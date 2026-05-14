from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import csv
from io import StringIO
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'biomedica_tec_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    sessions = db.relationship('SessionRecord', backref='owner', lazy=True)

class SessionRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.String(100))
    doctor_name = db.Column(db.String(100))
    rms_avg = db.Column(db.Float)
    arv_avg = db.Column(db.Float)
    date_created = db.Column(db.DateTime, default=datetime.now)

# --- CREACIÓN AUTOMÁTICA DE TABLAS ---
with app.app_context():
    db.create_all()

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- RUTAS DE AUTENTICACIÓN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('home'))
        flash('Credenciales incorrectas')
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        exists = User.query.filter_by(username=request.form['username']).first()
        if not exists:
            hashed_pw = generate_password_hash(request.form['password'])
            new_user = User(username=request.form['username'], password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        flash('El usuario ya existe')
    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- RUTAS DEL SISTEMA ---
@app.route('/')
@login_required
def home():
    return render_template('index.html', name=current_user.username)

@app.route('/sesiones')
@login_required
def sesiones_pasadas():
    historial = SessionRecord.query.filter_by(user_id=current_user.id).order_by(SessionRecord.date_created.desc()).all()
    return render_template('sesiones.html', sesiones=historial)

@app.route('/api/guardar-sesion', methods=['POST'])
@login_required
def guardar_sesion():
    data = request.json
    # Ajuste de hora para México (UTC-6)
    mexico_time = datetime.now() - timedelta(hours=6)
    
    nueva_sesion = SessionRecord(
        user_id=current_user.id,
        patient_id=data.get('patient_id', 'Anónimo'),
        doctor_name=data.get('doctor_name', 'Sin asignar'),
        rms_avg=data.get('rms', 0),
        arv_avg=data.get('arv', 0),
        date_created=mexico_time
    )
    db.session.add(nueva_sesion)
    db.session.commit()
    return jsonify({"success": True})

# --- NUEVAS FUNCIONES: BORRAR Y DESCARGAR ---

@app.route('/borrar-sesion/<int:id>', methods=['POST'])
@login_required
def borrar_sesion(id):
    sesion = SessionRecord.query.get_or_404(id)
    if sesion.user_id == current_user.id:
        db.session.delete(sesion)
        db.session.commit()
    return redirect(url_for('sesiones_pasadas'))

@app.route('/descargar-csv')
@login_required
def descargar_csv():
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Fecha', 'ID Paciente', 'Medico', 'RMS Promedio (mV)', 'ARV Promedio (mV)'])
    
    historial = SessionRecord.query.filter_by(user_id=current_user.id).order_by(SessionRecord.date_created.desc()).all()
    
    for s in historial:
        cw.writerow([
            s.date_created.strftime('%d/%m/%Y %H:%M'),
            s.patient_id,
            s.doctor_name,
            f"{s.rms_avg:.4f}",
            f"{s.arv_avg:.4f}"
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=historial_emg.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == '__main__':
    app.run(debug=True)

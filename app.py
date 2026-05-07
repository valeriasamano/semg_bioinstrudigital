from flask import Flask, render_template, request, jsonify, send_file
import csv
import os
from datetime import datetime

app = Flask(__name__)
CSV_FILE = 'datos_pacientes.csv'

# Si el archivo CSV no existe, lo crea con sus columnas correspondientes
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Fecha_Hora', 'Dispositivo_ID', 'Valor_Sensor'])

# 1. Esta ruta recibe los datos que el Arduino envía por WiFi
@app.route('/update_data', methods=['POST'])
def update_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No se recibieron datos"}), 400
            
        valor = data.get('valor')
        dispositivo = data.get('dispositivo_id', 'DESCONOCIDO')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Guardar la lectura en el archivo CSV
        with open(CSV_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, dispositivo, valor])
        
        return jsonify({"status": "success", "message": "Datos guardados exitosamente"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 2. Esta ruta permite al médico descargar el CSV presionando un botón
@app.route('/descargar_csv')
def descargar_csv():
    try:
        return send_file(CSV_FILE, as_attachment=True)
    except Exception as e:
        return "El archivo de datos aún no se ha generado.", 404

# 3. Esta ruta muestra la página web visual (el frontend)
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from ultralytics import YOLO
import os
from werkzeug.utils import secure_filename
import requests
import base64

app = Flask(__name__, template_folder="template")
app.config['UPLOAD_FOLDER'] = 'C:/newproject/repo/virtual/finalproject/flask/uploads/'
DATABASE = 'Pathole.db'

# Function to get the database connection
def get_db():
    return sqlite3.connect(DATABASE)

# Function to create the hazard table
def create_tables():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS hazards
                         (id INTEGER PRIMARY KEY, latitude REAL, longitude REAL, prediction TEXT)''')
        db.commit()

# Function to detect hazards using YOLOv8 model
class_names = ['Drain Hole', 'Pothole', 'Sewer Cover', 'Unpaved Road', 'Wet Surface']

def detect_hazards(image_path):
    yolo = YOLO('best1.pt')
    results_list = yolo(image_path)
    all_predictions = []
    for results in results_list:
        predictions = []
        for box in results.boxes:
            class_index = int(box.cls.item())
            class_name = class_names[class_index] if 0 <= class_index < len(class_names) else "Unknown"
            predictions.append(class_name)
        all_predictions.append(predictions)
    return all_predictions

# Function to get latitude and longitude from IP address
def get_latitude_longitude():
    ip_request = requests.get('https://get.geojs.io/v1/ip.json')
    ip_address = ip_request.json()['ip']
    url = f'https://get.geojs.io/v1/ip/geo/{ip_address}.json'
    geo_request = requests.get(url)
    geo_data = geo_request.json()
    return geo_data['latitude'], geo_data['longitude']

# Function to save hazard data to the database
def save_hazard_data(latitude, longitude, prediction):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO hazards (latitude, longitude, prediction) VALUES (?, ?, ?)",
                   (latitude, longitude, str(prediction)))
    db.commit()

# Function to fetch hazard data from the database
def fetch_hazard_data():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM hazards")
    return cursor.fetchall()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename != '':
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image_file.filename))
                image_file.save(image_path)

                latitude, longitude = get_latitude_longitude()
                prediction = detect_hazards(image_path)
                save_hazard_data(latitude, longitude, prediction)

                live_location = f"Latitude: {latitude}, Longitude: {longitude}"
                return redirect(url_for('index', live_location=live_location))
        elif 'captured_image' in request.form:
            captured_image_data = request.form['captured_image']
            if captured_image_data:
                image_data = base64.b64decode(captured_image_data.split(',')[1])
                image_filename = 'captured_image.png'
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                with open(image_path, 'wb') as f:
                    f.write(image_data)

                latitude, longitude = get_latitude_longitude()
                prediction = detect_hazards(image_path)
                save_hazard_data(latitude, longitude, prediction)

                live_location = f"Latitude: {latitude}, Longitude: {longitude}"
                return redirect(url_for('index', live_location=live_location))

    hazard_data = fetch_hazard_data()
    live_location = request.args.get('live_location', None)
    return render_template('indexn.html', hazard_data=hazard_data, live_location=live_location)

if __name__ == '__main__':
    create_tables()
    app.run(debug=True, port=5000)
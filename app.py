from flask import Flask, render_template, jsonify, request
from flask_pymongo import PyMongo
from datetime import datetime
import requests
from ping3 import ping
import threading
import time
import os
from apscheduler.schedulers.background import BackgroundScheduler
import csv
import io

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/app_monitor"
mongo = PyMongo(app)

def check_status(target, check_type):
    try:
        if check_type == 'ping':
            response = ping(target)
            return bool(response)
        elif check_type == 'http':
            response = requests.get(target, timeout=5)
            return response.status_code == 200
        return False
    except:
        return False

def update_status():
    while True:
        systems = mongo.db.systems.find()
        for system in systems:
            status = False
            if system.get('check_type') in ['ping', 'http']:
                status = check_status(system['target'], system['check_type'])
            
            mongo.db.systems.update_one(
                {'_id': system['_id']},
                {'$set': {
                    'status': status,
                    'last_check': datetime.now()
                }}
            )
        time.sleep(60)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/systems', methods=['GET'])
def get_systems():
    systems = list(mongo.db.systems.find())
    for system in systems:
        system['_id'] = str(system['_id'])
        system['last_check'] = system['last_check'].isoformat() if 'last_check' in system else None
    return jsonify(systems)

@app.route('/api/systems', methods=['POST'])
def add_system():
    data = request.json
    data['created_at'] = datetime.now()
    data['last_check'] = datetime.now()
    data['status'] = False
    mongo.db.systems.insert_one(data)
    return jsonify({"message": "System added successfully"})

@app.route('/api/systems/<system_id>', methods=['PUT'])
def update_system(system_id):
    data = request.json
    from bson.objectid import ObjectId
    mongo.db.systems.update_one(
        {'_id': ObjectId(system_id)},
        {'$set': data}
    )
    return jsonify({"message": "System updated successfully"})

@app.route('/api/systems/<system_id>', methods=['DELETE'])
def delete_system(system_id):
    from bson.objectid import ObjectId
    mongo.db.systems.delete_one({'_id': ObjectId(system_id)})
    return jsonify({"message": "System deleted successfully"})

@app.route('/api/systems/import', methods=['POST'])
def import_systems():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.csv'):
        return jsonify({"error": "Invalid file format. Please upload a CSV file"}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_data = csv.DictReader(stream)
        
        systems_added = 0
        for row in csv_data:
            row['created_at'] = datetime.now()
            row['last_check'] = datetime.now()
            row['status'] = False
            mongo.db.systems.insert_one(row)
            systems_added += 1
            
        return jsonify({"message": f"Successfully imported {systems_added} systems"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    status_thread = threading.Thread(target=update_status)
    status_thread.daemon = True
    status_thread.start()
    app.run(debug=True)

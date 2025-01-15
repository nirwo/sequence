from flask import Flask, render_template, request, jsonify, Response
from flask_pymongo import PyMongo
from datetime import datetime
import threading
import time
import requests
from ping3 import ping
import os
import csv
import io
import json
from bson import ObjectId, json_util

app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/app_monitor")
mongo = PyMongo(app)

def parse_json(data):
    return json.loads(json_util.dumps(data))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/systems', methods=['GET'])
def get_systems():
    try:
        systems = list(mongo.db.systems.find())
        return Response(
            json_util.dumps({'systems': systems}),
            mimetype='application/json'
        )
    except Exception as e:
        print(f"Error fetching systems: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/systems', methods=['POST'])
def add_system():
    try:
        system = request.json
        system['created_at'] = datetime.now()
        system['last_check'] = datetime.now()
        system['status'] = False
        
        # Handle cluster nodes
        if 'cluster_nodes' in system and isinstance(system['cluster_nodes'], str):
            system['cluster_nodes'] = [node.strip() for node in system['cluster_nodes'].split(',') if node.strip()]
            # Set target as the first node if it's empty
            if not system.get('target') and system['cluster_nodes']:
                system['target'] = system['cluster_nodes'][0]
        
        # Ensure target is set for single node systems
        if not system.get('target') and not system.get('cluster_nodes'):
            return jsonify({"error": "Target URL/IP is required"}), 400
            
        result = mongo.db.systems.insert_one(system)
        return jsonify({
            "message": "System added successfully",
            "id": str(result.inserted_id)
        })
    except Exception as e:
        print(f"Error adding system: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/systems/<system_id>', methods=['PUT'])
def update_system(system_id):
    try:
        system = request.json
        
        # Handle cluster nodes
        if 'cluster_nodes' in system and isinstance(system['cluster_nodes'], str):
            system['cluster_nodes'] = [node.strip() for node in system['cluster_nodes'].split(',') if node.strip()]
            # Set target as the first node if it's empty
            if not system.get('target') and system['cluster_nodes']:
                system['target'] = system['cluster_nodes'][0]
        
        # Ensure target is set for single node systems
        if not system.get('target') and not system.get('cluster_nodes'):
            return jsonify({"error": "Target URL/IP is required"}), 400
            
        # Update the system
        result = mongo.db.systems.update_one(
            {'_id': ObjectId(system_id)},
            {'$set': system}
        )
        
        if result.modified_count == 0:
            return jsonify({"error": "System not found"}), 404
            
        return jsonify({"message": "System updated successfully"})
    except Exception as e:
        print(f"Error updating system: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/systems/<system_id>', methods=['DELETE'])
def delete_system(system_id):
    try:
        result = mongo.db.systems.delete_one({'_id': ObjectId(system_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "System not found"}), 404
        return jsonify({"message": "System deleted successfully"})
    except Exception as e:
        print(f"Error deleting system: {str(e)}")
        return jsonify({"error": str(e)}), 500

def check_status(target, check_type):
    try:
        if check_type == 'ping':
            response = ping(target)
            return response is not None and response is not False
        elif check_type == 'http':
            response = requests.get(target, timeout=5)
            return response.status_code == 200
        return False
    except:
        return False

def update_status():
    while True:
        try:
            systems = mongo.db.systems.find()
            for system in systems:
                status = check_status(system['target'], system['check_type'])
                mongo.db.systems.update_one(
                    {'_id': system['_id']},
                    {
                        '$set': {
                            'status': status,
                            'last_check': datetime.now()
                        }
                    }
                )
        except Exception as e:
            print(f"Error in status update: {str(e)}")
        time.sleep(60)

@app.route('/api/systems/import', methods=['POST'])
def import_systems():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.csv'):
        return jsonify({"error": "Invalid file format. Please upload a CSV file"}), 400

    try:
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        systems_added = 0
        errors = []
        
        for row in csv_reader:
            try:
                system = {
                    'name': row.get('System Name', '').strip(),
                    'app_name': row.get('Application Name', '').strip(),
                    'check_type': row.get('Check Type', 'http').strip().lower(),
                    'target': row.get('Target URL/IP', '').strip(),
                    'db_name': row.get('Database Name', '').strip(),
                    'db_type': row.get('Database Type', '').strip(),
                    'mount_points': row.get('Mount Points', '').strip(),
                    'owner': row.get('Owner', '').strip(),
                    'shutdown_sequence': row.get('Shutdown Sequence', '').strip(),
                    'created_at': datetime.now(),
                    'last_check': datetime.now(),
                    'status': False
                }

                # Validate required fields
                if not system['name'] or not system['app_name']:
                    errors.append(f"Row {systems_added + 1}: System Name and Application Name are required")
                    continue

                # Handle check type
                if system['check_type'] not in ['http', 'ping']:
                    system['check_type'] = 'http'

                # Handle cluster nodes
                cluster_nodes = row.get('Cluster Nodes', '').strip()
                if cluster_nodes:
                    system['cluster_nodes'] = [node.strip() for node in cluster_nodes.split(',') if node.strip()]
                    if not system['target'] and system['cluster_nodes']:
                        system['target'] = system['cluster_nodes'][0]

                # Handle mount points
                if system['mount_points']:
                    system['mount_points'] = system['mount_points'].replace(';', ',')

                # Validate target
                if not system['target'] and not system.get('cluster_nodes'):
                    errors.append(f"Row {systems_added + 1}: Target URL/IP is required for non-cluster systems")
                    continue

                mongo.db.systems.insert_one(system)
                systems_added += 1

            except Exception as e:
                errors.append(f"Row {systems_added + 1}: {str(e)}")

        response = {
            "message": f"Successfully imported {systems_added} systems",
            "systems_added": systems_added
        }
        
        if errors:
            response["warnings"] = errors

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Error processing CSV file: {str(e)}"}), 400

@app.route('/api/csv/preview', methods=['POST'])
def preview_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.csv'):
        return jsonify({"error": "Invalid file format. Please upload a CSV file"}), 400

    try:
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.reader(stream)
        
        # Get headers and first few rows
        headers = next(csv_reader)
        preview_rows = []
        for _ in range(3):  # Preview first 3 rows
            try:
                preview_rows.append(next(csv_reader))
            except StopIteration:
                break
        
        # Get available fields from MongoDB schema
        available_fields = [
            {"id": "name", "label": "System Name"},
            {"id": "app_name", "label": "Application Name"},
            {"id": "check_type", "label": "Check Type"},
            {"id": "target", "label": "Target URL/IP"},
            {"id": "db_name", "label": "Database Name"},
            {"id": "db_type", "label": "Database Type"},
            {"id": "mount_points", "label": "Mount Points"},
            {"id": "owner", "label": "Owner"},
            {"id": "shutdown_sequence", "label": "Shutdown Sequence"},
            {"id": "cluster_nodes", "label": "Cluster Nodes"}
        ]
        
        return jsonify({
            "headers": headers,
            "preview_rows": preview_rows,
            "available_fields": available_fields
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/csv/import', methods=['POST'])
def import_csv_mapped():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        mapping = request.form.get('mapping')
        if not mapping:
            return jsonify({"error": "No field mapping provided"}), 400
        
        mapping = json.loads(mapping)
        
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        systems_added = 0
        for row in csv_reader:
            system = {
                "created_at": datetime.now(),
                "last_check": datetime.now(),
                "status": False
            }
            
            # Apply mapping
            for field, csv_header in mapping.items():
                if csv_header and csv_header in row:
                    value = row[csv_header].strip()
                    if field == "cluster_nodes" and value:
                        # Split cluster nodes by comma
                        system[field] = [node.strip() for node in value.split(',')]
                    elif field == "mount_points" and value:
                        # Split mount points by semicolon
                        system[field] = value.replace(';', ',')
                    else:
                        system[field] = value
            
            if system.get('name') and system.get('app_name'):  # Required fields
                mongo.db.systems.insert_one(system)
                systems_added += 1
        
        return jsonify({
            "message": f"Successfully imported {systems_added} systems",
            "systems_added": systems_added
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    status_thread = threading.Thread(target=update_status)
    status_thread.daemon = True
    status_thread.start()
    
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    app.run(host=host, port=port, debug=True)

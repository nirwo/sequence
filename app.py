from flask import Flask, render_template, request, jsonify, Response, send_from_directory
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
import subprocess
import platform
from requests.exceptions import RequestException

app = Flask(__name__, static_url_path='/static', static_folder='static')
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
        
        # Set default values
        system['created_at'] = datetime.now()
        system['last_check'] = datetime.now()  # Set initial last_check
        system['status'] = False
        
        # Handle empty or missing fields
        if not system.get('name'):
            return jsonify({"error": "Server Name is required"}), 400

        # Set default values for optional fields
        system['app_name'] = system.get('app_name') or 'N/A'
        system['db_name'] = system.get('db_name') or None
        system['db_type'] = system.get('db_type') or None
        system['owner'] = system.get('owner') or 'N/A'
        
        # Remove mount_points for now
        if 'mount_points' in system:
            del system['mount_points']

        # Handle shutdown sequence as string
        if not system.get('shutdown_sequence'):
            system['shutdown_sequence'] = None
        elif isinstance(system['shutdown_sequence'], list):
            system['shutdown_sequence'] = ';'.join(system['shutdown_sequence']) if system['shutdown_sequence'] else None
        else:
            system['shutdown_sequence'] = system['shutdown_sequence'].strip() or None
        
        # Handle cluster nodes
        if not system.get('cluster_nodes'):
            system['cluster_nodes'] = None
        elif isinstance(system['cluster_nodes'], str):
            nodes = [node.strip() for node in system['cluster_nodes'].split(';') if node.strip()]
            system['cluster_nodes'] = nodes if nodes else None
        elif isinstance(system['cluster_nodes'], list):
            system['cluster_nodes'] = [node for node in system['cluster_nodes'] if node.strip()]
            if not system['cluster_nodes']:
                system['cluster_nodes'] = None
        
        # Handle target for cluster systems
        if not system.get('target') and system.get('cluster_nodes'):
            system['target'] = system['cluster_nodes'][0]
        
        # Validate target
        if not system.get('target') and not system.get('cluster_nodes'):
            return jsonify({"error": "Target URL/IP is required for non-cluster systems"}), 400
            
        # Set default check type if not provided
        system['check_type'] = system.get('check_type', 'ping').lower()
        if system['check_type'] not in ['http', 'ping']:
            system['check_type'] = 'ping'
        
        mongo.db.systems.insert_one(system)
        return jsonify({"message": "System added successfully"})
    except Exception as e:
        print(f"Error adding system: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/systems/<system_id>', methods=['PUT'])
def update_system(system_id):
    try:
        if not ObjectId.is_valid(system_id):
            return jsonify({"error": "Invalid system ID format"}), 400

        system = request.json
        
        # Handle empty or missing fields
        if not system.get('name'):
            return jsonify({"error": "Server Name is required"}), 400
            
        # Handle cluster nodes
        if 'cluster_nodes' in system:
            if isinstance(system['cluster_nodes'], str):
                system['cluster_nodes'] = [node.strip() for node in system['cluster_nodes'].split(',') if node.strip()]
            elif not isinstance(system['cluster_nodes'], list):
                system['cluster_nodes'] = []
        
        # Handle target for cluster systems
        if not system.get('target') and system.get('cluster_nodes'):
            system['target'] = system['cluster_nodes'][0]
        
        # Validate target
        if not system.get('target') and not system.get('cluster_nodes'):
            return jsonify({"error": "Target URL/IP is required for non-cluster systems"}), 400
            
        # Set default check type if not provided
        if not system.get('check_type'):
            system['check_type'] = 'ping'
            
        # Clean empty strings to None
        for key in system:
            if isinstance(system[key], str) and not system[key].strip():
                system[key] = None
        
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
        # Validate ObjectId format
        if not ObjectId.is_valid(system_id):
            return jsonify({"error": "Invalid system ID format"}), 400

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
                    'name': row.get('Server Name', '').strip(),
                    'app_name': row.get('Application Name', '').strip(),
                    'check_type': row.get('Check Type', 'http').strip().lower(),
                    'target': row.get('Target URL/IP', '').strip(),
                    'db_name': row.get('Database Name', '').strip() or None,
                    'db_type': row.get('Database Type', '').strip() or None,
                    'owner': row.get('Owner', '').strip() or None,
                    'created_at': datetime.now(),
                    'last_check': datetime.now(),
                    'status': False
                }

                # Handle shutdown sequence as string
                shutdown_sequence = row.get('Shutdown Sequence', '').strip()
                system['shutdown_sequence'] = shutdown_sequence if shutdown_sequence else None

                # Handle cluster nodes
                cluster_nodes = row.get('Cluster Nodes', '').strip()
                if cluster_nodes:
                    system['cluster_nodes'] = [node.strip() for node in cluster_nodes.split(';') if node.strip()]
                    if not system['cluster_nodes']:
                        system['cluster_nodes'] = None
                    elif not system['target']:
                        system['target'] = system['cluster_nodes'][0]
                else:
                    system['cluster_nodes'] = None

                # Validate required fields
                if not system['name']:
                    errors.append(f"Row {systems_added + 1}: Server Name is required")
                    continue

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
        
        # Get headers and preview rows
        headers = next(csv_reader)  # First row as headers
        preview_rows = []
        for _ in range(5):  # Preview first 5 rows
            try:
                preview_rows.append(next(csv_reader))
            except StopIteration:
                break
        
        return jsonify({
            "headers": headers,
            "preview_rows": preview_rows
        })
    except Exception as e:
        return jsonify({"error": f"Error processing CSV file: {str(e)}"}), 400

@app.route('/api/csv/import', methods=['POST'])
def import_mapped_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.csv'):
        return jsonify({"error": "Invalid file format. Please upload a CSV file"}), 400

    try:
        # Get field mapping
        mapping = json.loads(request.form.get('mapping', '{}'))
        if not mapping:
            return jsonify({"error": "No field mapping provided"}), 400

        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        systems_added = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start from 2 since row 1 is header
            try:
                # Map fields according to provided mapping
                system = {
                    'created_at': datetime.now(),
                    'last_check': datetime.now(),
                    'status': False
                }

                # Map fields from CSV
                for field, csv_header in mapping.items():
                    if csv_header in row:
                        value = row[csv_header].strip() if row[csv_header] else None
                        if value:  # Only set if value is not empty
                            if field == 'cluster_nodes':
                                system[field] = [node.strip() for node in value.split(',') if node.strip()]
                            elif field == 'mount_points':
                                system[field] = [point.strip() for point in value.split(',') if point.strip()]
                            elif field == 'shutdown_sequence':
                                system[field] = [step.strip() for step in value.split(',') if step.strip()]
                            else:
                                system[field] = value

                # Validate required fields
                if not system.get('name'):
                    errors.append(f"Row {row_num}: Server Name is required")
                    continue

                # Set default check type if not provided
                if not system.get('check_type'):
                    system['check_type'] = 'ping'
                else:
                    system['check_type'] = system['check_type'].lower()

                # Handle target for cluster systems
                if not system.get('target') and system.get('cluster_nodes'):
                    system['target'] = system['cluster_nodes'][0]

                # Validate target
                if not system.get('target') and not system.get('cluster_nodes'):
                    errors.append(f"Row {row_num}: Target URL/IP is required for non-cluster systems")
                    continue

                # Insert the system
                mongo.db.systems.insert_one(system)
                systems_added += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        response = {
            "message": f"Successfully imported {systems_added} systems",
            "systems_added": systems_added
        }
        
        if errors:
            response["warnings"] = errors

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Error processing CSV file: {str(e)}"}), 400

@app.route('/api/csv/template', methods=['GET'])
def download_csv_template():
    try:
        # Create a StringIO object to write CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        headers = [
            'Server Name',
            'Application Name',
            'Check Type',
            'Target URL/IP',
            'Database Name',
            'Database Type',
            'Owner',
            'Shutdown Sequence',
            'Cluster Nodes'
        ]
        writer.writerow(headers)
        
        # Write example row
        example_row = [
            'Example System',
            'Example App',
            'http',
            'http://example.com',
            'example_db',
            'postgres',
            'John Doe',
            'service nginx stop;service app stop',
            'node1.example.com;node2.example.com'
        ]
        writer.writerow(example_row)
        
        # Create the response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=systems_template.csv',
                'Content-Type': 'text/csv'
            }
        )
    except Exception as e:
        return jsonify({"error": f"Error generating template: {str(e)}"}), 500

@app.route('/api/download/example-csv')
def download_example_csv():
    try:
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        headers = [
            'Server Name',
            'Application Name',
            'Check Type',
            'Target URL/IP',
            'Database Name',
            'Database Type',
            'Owner',
            'Shutdown Sequence',
            'Cluster Nodes'
        ]
        writer.writerow(headers)
        
        # Write example rows
        example_rows = [
            # Standalone web server
            [
                'webserver01',
                'Company Website',
                'http',
                'http://example.com',
                '',
                '',
                'John Doe',
                'service nginx stop;service php-fpm stop',
                ''
            ],
            # Database server
            [
                'dbserver01',
                'PostgreSQL DB',
                'ping',
                '192.168.1.100',
                'main_db',
                'postgres',
                'Jane Smith',
                'pg_ctl stop -D /var/lib/postgresql/data',
                ''
            ],
            # Load balancer cluster
            [
                'app-cluster',
                'Load Balancer',
                'http',
                '192.168.1.200',
                'app_db',
                'mysql',
                'Mike Johnson',
                'service haproxy stop;service mysql stop',
                'node1.example.com;node2.example.com'
            ]
        ]
        for row in example_rows:
            writer.writerow(row)
        
        # Create the response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=example_systems.csv',
                'Content-Type': 'text/csv'
            }
        )
    except Exception as e:
        return jsonify({"error": f"Error generating example CSV: {str(e)}"}), 500

def test_http(url):
    try:
        # Add http:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = f'http://{url}'
        
        # Try with verify=False to handle self-signed certificates
        try:
            response = requests.get(url, timeout=10, verify=False)
        except:
            # If failed with verify=False, try with verify=True
            response = requests.get(url, timeout=10)
        
        # Consider any 2xx status code as success
        return 200 <= response.status_code < 300
    except RequestException as e:
        print(f"HTTP test failed for {url}: {str(e)}")
        # If http:// failed, try https://
        if url.startswith('http://'):
            try:
                https_url = f"https://{url[7:]}"
                print(f"Retrying with HTTPS: {https_url}")
                response = requests.get(https_url, timeout=10, verify=False)
                return 200 <= response.status_code < 300
            except RequestException as e2:
                print(f"HTTPS retry failed: {str(e2)}")
        return False
    except Exception as e:
        print(f"Unexpected error in HTTP test for {url}: {str(e)}")
        return False

def test_ping(host):
    try:
        # Remove protocol if present
        host = host.replace('http://', '').replace('https://', '')
        # Remove path and query parameters
        host = host.split('/')[0]
        
        # Ping command parameters
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', host]
        
        return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    except:
        return False

@app.route('/api/systems/check/<system_id>')
def check_system(system_id):
    try:
        system = mongo.db.systems.find_one({'_id': ObjectId(system_id)})
        if not system:
            return jsonify({'error': 'System not found'}), 404

        status = False
        target = system.get('target')
        error_message = None
        
        if target:
            if system.get('check_type') == 'http':
                try:
                    status = test_http(target)
                    if not status:
                        error_message = "HTTP check failed - server not responding or invalid status code"
                except Exception as e:
                    error_message = f"HTTP check error: {str(e)}"
            else:  # default to ping
                try:
                    status = test_ping(target)
                    if not status:
                        error_message = "Ping failed - host not responding"
                except Exception as e:
                    error_message = f"Ping error: {str(e)}"

        # Update system status and last check time
        update_data = {
            'status': status,
            'last_check': datetime.now()
        }
        if error_message:
            update_data['last_error'] = error_message
        
        mongo.db.systems.update_one(
            {'_id': ObjectId(system_id)},
            {'$set': update_data}
        )

        return jsonify({
            'status': status,
            'last_check': datetime.now().isoformat(),
            'error': error_message
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/systems/check_all')
def check_all_systems():
    try:
        systems = list(mongo.db.systems.find())
        results = []
        
        for system in systems:
            status = False
            target = system.get('target')
            error_message = None
            
            if target:
                if system.get('check_type') == 'http':
                    try:
                        status = test_http(target)
                        if not status:
                            error_message = "HTTP check failed - server not responding or invalid status code"
                    except Exception as e:
                        error_message = f"HTTP check error: {str(e)}"
                else:  # default to ping
                    try:
                        status = test_ping(target)
                        if not status:
                            error_message = "Ping failed - host not responding"
                    except Exception as e:
                        error_message = f"Ping error: {str(e)}"
            
            # Update system status and last check time
            update_data = {
                'status': status,
                'last_check': datetime.now()
            }
            if error_message:
                update_data['last_error'] = error_message
            
            mongo.db.systems.update_one(
                {'_id': system['_id']},
                {'$set': update_data}
            )
            
            results.append({
                'id': str(system['_id']),
                'name': system.get('name'),
                'status': status,
                'error': error_message
            })
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    status_thread = threading.Thread(target=update_status)
    status_thread.daemon = True
    status_thread.start()
    
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    app.run(host=host, port=port, debug=True)

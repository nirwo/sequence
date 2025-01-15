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
from io import TextIOWrapper
import json
from bson import ObjectId, json_util
import subprocess
import platform
from requests.exceptions import RequestException
import socket
from pymongo.errors import DuplicateKeyError

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
        for system in systems:
            # Convert ObjectId to string for JSON serialization
            system['_id'] = str(system['_id'])
            
            # Ensure all required fields have default values
            system.setdefault('status', False)
            system.setdefault('db_status', None)
            system.setdefault('http_status', None)
            system.setdefault('http_error', None)
            system.setdefault('ping_status', None)
            system.setdefault('ping_error', None)
            system.setdefault('last_error', None)
            system.setdefault('sequence_status', 'not_started')
            
            # Convert datetime objects to ISO format strings
            if 'created_at' in system:
                system['created_at'] = system['created_at'].isoformat()
            if 'last_check' in system:
                system['last_check'] = system['last_check'].isoformat() if system['last_check'] else None

            # Handle cluster nodes
            if 'cluster_nodes' in system and system['cluster_nodes']:
                for node in system['cluster_nodes']:
                    if isinstance(node, dict):
                        if 'last_check' in node:
                            node['last_check'] = node['last_check'].isoformat() if node['last_check'] else None
                        node.setdefault('status', False)
                        node.setdefault('http_status', None)
                        node.setdefault('http_error', None)
                        node.setdefault('ping_status', None)
                        node.setdefault('ping_error', None)
                    else:
                        # Convert string node to dict format
                        system['cluster_nodes'] = [{'host': n, 'status': False} for n in system['cluster_nodes']]
                        break

        return jsonify(systems)
    except Exception as e:
        print(f"Error fetching systems: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/systems', methods=['POST'])
def add_system():
    try:
        system = request.json
        
        # Set default values
        system['created_at'] = datetime.now()
        system['last_check'] = datetime.now()
        system['status'] = False
        
        # Handle empty or missing fields
        if not system.get('name'):
            return jsonify({"error": "Server Name is required"}), 400

        # Set default values for optional fields
        system['app_name'] = system.get('app_name') or 'N/A'
        system['db_name'] = system.get('db_name') or 'N/A'
        system['db_type'] = system.get('db_type') or 'N/A'
        system['owner'] = system.get('owner') or 'N/A'
        system['shutdown_sequence'] = system.get('shutdown_sequence') or 'N/A'
        
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
        return jsonify({'error': 'No file provided', 'success': False})
    
    file = request.files['file']
    if not file or not file.filename.endswith('.csv'):
        return jsonify({'error': 'Invalid file format. Please upload a CSV file', 'success': False})
    
    try:
        # Read CSV file with different encodings
        encodings = ['utf-8', 'iso-8859-1', 'cp1252']
        csv_data = None
        
        for encoding in encodings:
            try:
                # Reset file pointer
                file.seek(0)
                # Try reading with current encoding
                csv_data = list(csv.DictReader(TextIOWrapper(file, encoding=encoding)))
                break
            except UnicodeDecodeError:
                continue
        
        if not csv_data:
            return jsonify({'error': 'Could not read CSV file with supported encodings', 'success': False})
        
        # Auto-map fields
        field_mappings = auto_map_csv_fields(csv_data[0].keys())
        
        if not field_mappings:
            return jsonify({'error': 'Could not map CSV fields to database fields', 'success': False})
        
        # Process each row
        success_count = 0
        error_messages = []
        
        for row in csv_data:
            try:
                # Map fields using the auto-mapped fields
                system_data = {field_mappings[key]: value.strip() if value else value 
                             for key, value in row.items() 
                             if key in field_mappings and value}
                
                # Validate required fields
                if not system_data.get('name'):
                    error_messages.append(f"Skipped row: Missing required field 'name'")
                    continue
                
                # Set default values and convert string lists to actual lists
                system_data = set_default_values(system_data)
                
                # Insert into database
                systems_collection = mongo.db.systems
                try:
                    systems_collection.insert_one(system_data)
                    success_count += 1
                except DuplicateKeyError:
                    error_messages.append(f"System '{system_data.get('name', 'Unknown')}' already exists")
                    continue
                
            except Exception as e:
                error_messages.append(f"Error processing row: {str(e)}")
        
        # Prepare response message
        message = f"Successfully imported {success_count} systems."
        if error_messages:
            message += f" Errors: {'; '.join(error_messages)}"
        
        return jsonify({
            'success': True,
            'message': message,
            'imported_count': success_count,
            'errors': error_messages
        })
        
    except Exception as e:
        return jsonify({'error': f'Error importing systems: {str(e)}', 'success': False})

@app.route('/api/systems/export')
def export_systems():
    try:
        systems = list(mongo.db.systems.find({}, {'_id': 0}))
        
        # Prepare CSV content
        output = io.StringIO()
        fieldnames = ['name', 'app_name', 'target', 'db_name', 'db_type', 'db_port', 
                     'owner', 'shutdown_sequence', 'check_type', 'cluster_nodes']
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for system in systems:
            # Convert cluster nodes to string format
            if system.get('cluster_nodes'):
                system['cluster_nodes'] = ';'.join(node['host'] for node in system['cluster_nodes'])
            else:
                system['cluster_nodes'] = ''
                
            # Remove extra fields not needed in CSV
            csv_system = {field: system.get(field, 'N/A') for field in fieldnames}
            writer.writerow(csv_system)
        
        # Create response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=systems_export.csv'}
        )
    except Exception as e:
        return jsonify({'error': f'Error exporting systems: {str(e)}'}), 500

@app.route('/static/example_systems.csv')
def download_example():
    return send_from_directory('static', 'example_systems.csv',
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name='example_systems.csv')

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
        # Create a StringIO object to write CSV data with UTF-8 BOM
        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM
        writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        
        # Write headers
        headers = [
            'Server Name',
            'Application Name',
            'Check Type',
            'Target URL/IP',
            'Database Name',
            'Database Type',
            'Database Port',
            'Owner',
            'Mount Points',
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
            '5432',
            'John Doe',
            '/mnt/data,/mnt/logs',
            'service nginx stop;service app stop',
            'node1.example.com;node2.example.com'
        ]
        writer.writerow(example_row)
        
        # Create the response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': 'attachment; filename=systems_template.csv',
                'Content-Type': 'text/csv; charset=utf-8'
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

@app.route('/api/systems/test/<system_id>', methods=['POST'])
def test_system(system_id):
    try:
        system = mongo.db.systems.find_one({'_id': ObjectId(system_id)})
        if not system:
            return jsonify({'error': 'System not found'}), 404

        results = {
            'system_id': str(system['_id']),
            'name': system['name'],
            'status': False,
            'messages': [],
            'nodes': []
        }

        # Test main system if target is provided
        if system.get('target'):
            if system['check_type'] in ['http', 'both']:
                http_status = test_http(system['target'])
                results['messages'].append({
                    'type': 'http',
                    'status': http_status['success'],
                    'message': http_status['message']
                })
                system['http_status'] = http_status['success']
                system['http_error'] = http_status['message'] if not http_status['success'] else ""

            if system['check_type'] in ['ping', 'both']:
                ping_status = test_ping(system['target'])
                results['messages'].append({
                    'type': 'ping',
                    'status': ping_status['success'],
                    'message': ping_status['message']
                })
                system['ping_status'] = ping_status['success']
                system['ping_error'] = ping_status['message'] if not ping_status['success'] else ""

            # Test database if configured
            if system.get('db_type') != 'N/A' and system.get('db_port'):
                db_status = test_db_connection(system['target'], system['db_port'])
                results['messages'].append({
                    'type': 'database',
                    'status': db_status['success'],
                    'message': db_status['message']
                })
                system['db_status'] = db_status['success']

        # Test cluster nodes if present
        if system.get('cluster_nodes'):
            for node in system['cluster_nodes']:
                node_result = {
                    'host': node['host'],
                    'status': False,
                    'messages': []
                }

                # Test HTTP if applicable
                if system['check_type'] in ['http', 'both']:
                    http_status = test_http(node['host'])
                    node_result['messages'].append({
                        'type': 'http',
                        'status': http_status['success'],
                        'message': http_status['message']
                    })
                    node['http_status'] = http_status['success']
                    node['http_error'] = http_status['message'] if not http_status['success'] else ""

                # Test Ping if applicable
                if system['check_type'] in ['ping', 'both']:
                    ping_status = test_ping(node['host'])
                    node_result['messages'].append({
                        'type': 'ping',
                        'status': ping_status['success'],
                        'message': ping_status['message']
                    })
                    node['ping_status'] = ping_status['success']
                    node['ping_error'] = ping_status['message'] if not ping_status['success'] else ""

                # Update node status
                node_result['status'] = any(msg['status'] for msg in node_result['messages'])
                node['status'] = node_result['status']
                node['last_check'] = datetime.now()
                results['nodes'].append(node_result)

        # Update overall system status
        main_system_status = False
        if system.get('target'):
            if system['check_type'] == 'both':
                main_system_status = system['http_status'] and system['ping_status']
            elif system['check_type'] == 'http':
                main_system_status = system['http_status']
            else:
                main_system_status = system['ping_status']
        
        # For cluster systems, consider node statuses
        if system.get('cluster_nodes'):
            cluster_status = any(node['status'] for node in system['cluster_nodes'])
            main_system_status = main_system_status or cluster_status

        system['status'] = main_system_status
        system['last_check'] = datetime.now()

        # Update system in database
        mongo.db.systems.update_one(
            {'_id': ObjectId(system_id)},
            {'$set': system}
        )

        results['status'] = main_system_status
        return jsonify(results)

    except Exception as e:
        print(f"Error testing system: {str(e)}")
        return jsonify({'error': f'Error testing system: {str(e)}'}), 500

@app.route('/api/systems/sequence/<system_id>', methods=['POST'])
def update_sequence_status(system_id):
    try:
        status = request.json.get('status')
        if status not in ['not_started', 'in_progress', 'completed']:
            return jsonify({'error': 'Invalid status'}), 400
            
        result = mongo.db.systems.update_one(
            {'_id': ObjectId(system_id)},
            {'$set': {'sequence_status': status}}
        )
        
        if result.modified_count == 0:
            return jsonify({'error': 'System not found'}), 404
            
        return jsonify({'message': 'Status updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/systems/summary')
def get_systems_summary():
    try:
        # Get all systems
        systems = list(mongo.db.systems.find())
        
        # Initialize counters
        total_systems = len(systems)
        online_systems = sum(1 for system in systems if system.get('status', False))
        offline_systems = total_systems - online_systems
        
        # Count database statuses
        db_total = sum(1 for system in systems if system.get('db_name'))
        db_online = sum(1 for system in systems if system.get('db_status', False))
        db_offline = db_total - db_online
        
        # Count sequence statuses
        sequence_counts = {
            'not_started': 0,
            'in_progress': 0,
            'completed': 0
        }
        for system in systems:
            status = system.get('sequence_status', 'not_started')
            sequence_counts[status] = sequence_counts.get(status, 0) + 1
        
        # Get recent errors
        recent_errors = []
        for system in systems:
            if system.get('last_error'):
                recent_errors.append({
                    'system_name': system.get('name', 'Unknown'),
                    'error': system.get('last_error'),
                    'timestamp': system.get('last_check', datetime.now()).isoformat() if system.get('last_check') else None
                })
        
        # Sort errors by timestamp (most recent first)
        recent_errors.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '', reverse=True)
        recent_errors = recent_errors[:5]  # Keep only 5 most recent errors
        
        return jsonify({
            'total_systems': total_systems,
            'online_systems': online_systems,
            'offline_systems': offline_systems,
            'db_total': db_total,
            'db_online': db_online,
            'db_offline': db_offline,
            'sequence_status': sequence_counts,
            'recent_errors': recent_errors
        })
    except Exception as e:
        print(f"Error getting systems summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/systems/check_all')
def check_all_systems():
    try:
        systems = list(mongo.db.systems.find())
        results = []
        
        for system in systems:
            try:
                result = test_system(system)
                system_id = str(system['_id'])
                
                # Update system status and last check time
                update_data = {
                    'status': result['status'],
                    'last_check': datetime.now(),
                    'db_status': result['db_status'],
                    'http_status': result['http_status'],
                    'http_error': result['http_error'],
                    'ping_status': result['ping_status'],
                    'ping_error': result['ping_error'],
                    'last_error': '; '.join(result['errors']) if result['errors'] else None
                }
                
                # Update cluster nodes if present
                if result.get('cluster_nodes'):
                    update_data['cluster_nodes'] = result['cluster_nodes']
                
                mongo.db.systems.update_one(
                    {'_id': ObjectId(system_id)},
                    {'$set': update_data}
                )
                
                results.append({
                    'system_id': system_id,
                    'name': system.get('name', 'Unknown'),
                    'status': result['status'],
                    'errors': result['errors']
                })
            except Exception as e:
                print(f"Error checking system {system.get('name', 'Unknown')}: {str(e)}")
                results.append({
                    'system_id': str(system['_id']),
                    'name': system.get('name', 'Unknown'),
                    'status': False,
                    'errors': [str(e)]
                })
        
        return jsonify({'results': results})
    except Exception as e:
        print(f"Error checking all systems: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
        return {'success': 200 <= response.status_code < 300, 'message': response.text}
    except RequestException as e:
        print(f"HTTP test failed for {url}: {str(e)}")
        # If http:// failed, try https://
        if url.startswith('http://'):
            try:
                https_url = f"https://{url[7:]}"
                print(f"Retrying with HTTPS: {https_url}")
                response = requests.get(https_url, timeout=10, verify=False)
                return {'success': 200 <= response.status_code < 300, 'message': response.text}
            except RequestException as e2:
                print(f"HTTPS retry failed: {str(e2)}")
        return {'success': False, 'message': str(e)}
    except Exception as e:
        print(f"Unexpected error in HTTP test for {url}: {str(e)}")
        return {'success': False, 'message': str(e)}

def test_ping(host):
    try:
        # Remove protocol if present
        host = host.replace('http://', '').replace('https://', '')
        # Remove path and query parameters
        host = host.split('/')[0]
        # Remove port if present
        host = host.split(':')[0]
        
        print(f"Attempting to ping host: {host}")
        
        # Ping command parameters
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', host]  # Using just 'ping' as it's in PATH
        
        # Use subprocess.Popen to get output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        success = process.returncode == 0
        print(f"Ping output for {host}:")
        print(stdout)
        if stderr:
            print(f"Ping error for {host}:")
            print(stderr)
            
        if not success:
            # Check if we can get more specific error from output
            if "unknown host" in (stdout + stderr).lower():
                return {'success': False, 'message': f"Unknown host: {host}"}
            elif "network is unreachable" in (stdout + stderr).lower():
                return {'success': False, 'message': f"Network is unreachable for host: {host}"}
            elif "permission denied" in (stdout + stderr).lower():
                return {'success': False, 'message': f"Permission denied when pinging {host}. Try running with sudo."}
            else:
                return {'success': False, 'message': f"Host {host} is not responding. {stderr if stderr else stdout}"}
            
        return {'success': success, 'message': stdout if success else f"Host {host} is not responding. {stderr if stderr else ''}"}
    except Exception as e:
        error_msg = f"Error pinging {host}: {str(e)}"
        print(error_msg)
        return {'success': False, 'message': error_msg}

def test_db_connection(host, port):
    try:
        # Try nmap first for detailed port info
        command = ['/usr/bin/nmap', '-p', str(port), '-Pn', host]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        if "open" in stdout.lower():
            return {'success': True, 'message': "Port is open"}
            
        # Fallback to telnet
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return {'success': True, 'message': "Port is open"}
        else:
            return {'success': False, 'message': f"Port {port} is closed on {host}"}
    except Exception as e:
        return {'success': False, 'message': f"Error checking port {port} on {host}: {str(e)}"}

def auto_map_csv_fields(csv_headers):
    """Auto map CSV headers to database fields."""
    field_mappings = {}
    db_fields = [
        'name', 'app_name', 'target', 'db_name', 'db_type', 'db_port',
        'owner', 'shutdown_sequence', 'check_type', 'cluster_nodes', 'mount_points'
    ]
    
    for header in csv_headers:
        # Convert header to lowercase and remove spaces for matching
        normalized_header = header.lower().replace(' ', '_')
        if normalized_header in db_fields:
            field_mappings[header] = normalized_header
    
    return field_mappings

def set_default_values(system_data):
    """Set default values for missing fields."""
    defaults = {
        'db_name': 'N/A',
        'db_type': 'N/A',
        'db_port': None,
        'owner': 'System Admin',
        'shutdown_sequence': [],
        'mount_points': [],
        'cluster_nodes': [],
        'created_at': datetime.utcnow(),
        'last_check': datetime.utcnow(),
        'status': False,
        'sequence_status': 'not_started',
        'http_status': False,
        'http_error': '',
        'ping_status': False,
        'ping_error': '',
        'db_status': False,
        'last_error': ''
    }
    
    for key, value in defaults.items():
        if key not in system_data or not system_data[key]:
            system_data[key] = value
    
    # Convert string lists to actual lists
    for field in ['shutdown_sequence', 'mount_points', 'cluster_nodes']:
        if isinstance(system_data[field], str):
            # Split by semicolon or comma
            items = system_data[field].split(';') if ';' in system_data[field] else system_data[field].split(',')
            # Clean up items
            system_data[field] = [item.strip() for item in items if item.strip()]
    
    return system_data

if __name__ == '__main__':
    status_thread = threading.Thread(target=update_status)
    status_thread.daemon = True
    status_thread.start()
    
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    app.run(host=host, port=port, debug=True)

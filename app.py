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
import socket

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
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({"success": False, "error": "File must be a CSV"}), 400

        # Get import options
        options = json.loads(request.form.get('options', '{}'))
        skip_duplicates = options.get('skip_duplicates', True)
        update_existing = options.get('update_existing', False)
        auto_map_fields = options.get('auto_map_fields', True)

        try:
            # Read CSV file with UTF-8 encoding, handle BOM if present
            content = file.read()
            try:
                csv_content = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                csv_content = content.decode('latin-1')  # Fallback encoding
        except Exception as e:
            return jsonify({"success": False, "error": f"Error reading CSV file: {str(e)}"}), 400

        try:
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            if not csv_reader.fieldnames:
                return jsonify({"success": False, "error": "CSV file has no headers"}), 400
        except Exception as e:
            return jsonify({"success": False, "error": f"Error parsing CSV: {str(e)}"}), 400

        # Get field mapping
        mapping = json.loads(request.form.get('mapping', '{}'))
        
        # Auto-map fields if enabled
        if auto_map_fields and not mapping:
            mapping = auto_map_csv_fields(csv_reader.fieldnames)
            if not mapping:
                return jsonify({"success": False, "error": "Could not automatically map fields"}), 400

        # Initialize counters and error tracking
        results = {
            "total": 0,
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "warnings": [],
            "errors": []
        }

        # Process each row
        for row_num, row in enumerate(csv_reader, start=1):
            try:
                results["total"] += 1
                
                # Create system dict with mapped fields
                system = {}
                for field, header in mapping.items():
                    if header in row:
                        value = row[header].strip()
                        if value:  # Only add non-empty values
                            system[field] = value

                # Validate required fields
                if not system.get('name'):
                    results["failed"] += 1
                    results["errors"].append(f"Row {row_num}: System Name is required")
                    continue

                # Check for existing system
                existing_system = mongo.db.systems.find_one({"name": system['name']})
                if existing_system:
                    if update_existing:
                        try:
                            # Preserve existing ID and created_at
                            system['_id'] = existing_system['_id']
                            system['created_at'] = existing_system['created_at']
                            
                            # Set default values
                            set_system_defaults(system)
                            
                            # Update the existing system
                            mongo.db.systems.replace_one({'_id': existing_system['_id']}, system)
                            results["updated"] += 1
                            results["warnings"].append(f"Row {row_num}: Updated existing system '{system['name']}'")
                        except Exception as e:
                            results["failed"] += 1
                            results["errors"].append(f"Row {row_num}: Error updating system '{system['name']}': {str(e)}")
                    elif skip_duplicates:
                        results["skipped"] += 1
                        results["warnings"].append(f"Row {row_num}: Skipped duplicate system '{system['name']}'")
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"Row {row_num}: System '{system['name']}' already exists")
                    continue

                # Set default values for new system
                set_system_defaults(system)

                # Insert the new system
                try:
                    mongo.db.systems.insert_one(system)
                    results["added"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Row {row_num}: Error adding system '{system['name']}': {str(e)}")

            except Exception as e:
                results["failed"] += 1
                error_msg = f"Row {row_num}: {str(e)}"
                results["errors"].append(error_msg)
                print(f"Error processing row: {error_msg}")

        # Prepare response message
        message = f"Import completed: {results['added']} added, {results['updated']} updated, "
        message += f"{results['skipped']} skipped, {results['failed']} failed"
        
        response = {
            "success": True,
            "message": message,
            "results": results
        }

        return jsonify(response)

    except Exception as e:
        print(f"Error importing systems: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error importing systems: {str(e)}"
        }), 500

def set_system_defaults(system):
    """Set default values for a system document."""
    # Set timestamps
    system.setdefault('created_at', datetime.now())
    system.setdefault('last_check', datetime.now())
    
    # Set status fields
    system.setdefault('status', False)
    system.setdefault('sequence_status', "not_started")
    system.setdefault('http_status', False)
    system.setdefault('http_error', "")
    system.setdefault('ping_status', False)
    system.setdefault('ping_error', "")
    system.setdefault('db_status', False)
    system.setdefault('last_error', "")

    # Process check_type
    if 'check_type' in system:
        system['check_type'] = system['check_type'].lower()
        if system['check_type'] not in ['http', 'ping', 'both']:
            system['check_type'] = 'ping'
    else:
        system['check_type'] = 'ping'

    # Process mount points
    if 'mount_points' in system and isinstance(system['mount_points'], str):
        mount_points = [p.strip() for p in system['mount_points'].split(',')]
        system['mount_points'] = [p for p in mount_points if p]
    else:
        system['mount_points'] = []

    # Process shutdown sequence
    if 'shutdown_sequence' in system and isinstance(system['shutdown_sequence'], str):
        sequence = [s.strip() for s in system['shutdown_sequence'].split(';')]
        system['shutdown_sequence'] = [s for s in sequence if s]
    else:
        system['shutdown_sequence'] = []

    # Process cluster nodes
    if 'cluster_nodes' in system and isinstance(system['cluster_nodes'], str):
        nodes = [n.strip() for n in system['cluster_nodes'].split(';')]
        nodes = [n for n in nodes if n]
        if nodes:
            system['cluster_nodes'] = [
                {
                    'host': node,
                    'status': False,
                    'last_check': datetime.now(),
                    'http_status': False,
                    'http_error': "",
                    'ping_status': False,
                    'ping_error': ""
                }
                for node in nodes
            ]
    else:
        system['cluster_nodes'] = []

    # Process database port
    if 'db_port' in system:
        try:
            system['db_port'] = int(system['db_port'])
        except (ValueError, TypeError):
            system['db_port'] = None

    # Set default values for optional fields
    defaults = {
        'app_name': 'N/A',
        'target': system.get('target', 'N/A'),
        'db_name': 'N/A',
        'db_type': 'N/A',
        'owner': 'N/A'
    }
    for field, default in defaults.items():
        system.setdefault(field, default)

    return system

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

@app.route('/api/systems/check/<system_id>')
def check_system(system_id):
    try:
        system = mongo.db.systems.find_one({'_id': ObjectId(system_id)})
        if not system:
            return jsonify({'error': 'System not found'}), 404

        results = test_system(system)
        
        # Update system status and last check time
        update_data = {
            'status': results['status'],
            'last_check': datetime.now(),
            'db_status': results['db_status'],
            'http_status': results['http_status'],
            'http_error': results['http_error'],
            'ping_status': results['ping_status'],
            'ping_error': results['ping_error'],
            'last_error': '; '.join(results['errors']) if results['errors'] else None
        }
        
        # Update cluster nodes if present
        if results.get('cluster_nodes'):
            update_data['cluster_nodes'] = results['cluster_nodes']
        
        mongo.db.systems.update_one(
            {'_id': ObjectId(system_id)},
            {'$set': update_data}
        )

        return jsonify(results)
    except Exception as e:
        print(f"Error checking system: {str(e)}")
        return jsonify({'error': str(e)}), 500

def test_system(system):
    results = {
        'status': False,
        'errors': [],
        'db_status': None,
        'http_status': None,
        'http_error': None,
        'ping_status': None,
        'ping_error': None
    }
    
    # Test main target
    if system.get('target'):
        if system.get('check_type') in ['http', 'both']:
            try:
                http_status = test_http(system['target'])
                results['http_status'] = http_status
                if not http_status:
                    error_msg = f"HTTP check failed for {system['target']}"
                    results['http_error'] = error_msg
                    results['errors'].append(error_msg)
            except Exception as e:
                error_msg = f"HTTP error for {system['target']}: {str(e)}"
                results['http_error'] = error_msg
                results['errors'].append(error_msg)
                
        if system.get('check_type') in ['ping', 'both']:
            try:
                ping_status, message = test_ping(system['target'])
                results['ping_status'] = ping_status
                if not ping_status:
                    results['ping_error'] = message
                    results['errors'].append(message)
            except Exception as e:
                error_msg = f"Ping error for {system['target']}: {str(e)}"
                results['ping_error'] = error_msg
                results['errors'].append(error_msg)
    
    # Test cluster nodes
    if system.get('cluster_nodes'):
        updated_nodes = []
        nodes = system['cluster_nodes']
        if isinstance(nodes, list):
            for node in nodes:
                node_host = node['host'] if isinstance(node, dict) else node
                node_result = {
                    'host': node_host,
                    'status': False,
                    'last_check': datetime.now(),
                    'http_status': None,
                    'http_error': None,
                    'ping_status': None,
                    'ping_error': None
                }
                
                # Test ping
                try:
                    ping_status, message = test_ping(node_host)
                    node_result['ping_status'] = ping_status
                    node_result['status'] = ping_status
                    if not ping_status:
                        node_result['ping_error'] = message
                        results['errors'].append(f"Node {node_host}: {message}")
                except Exception as e:
                    error_msg = f"Error checking node {node_host}: {str(e)}"
                    node_result['ping_error'] = error_msg
                    results['errors'].append(error_msg)
                    
                # Test HTTP if main system is HTTP
                if system.get('check_type') in ['http', 'both']:
                    try:
                        http_status = test_http(node_host)
                        node_result['http_status'] = http_status
                        if not http_status:
                            error_msg = f"HTTP check failed for node {node_host}"
                            node_result['http_error'] = error_msg
                            results['errors'].append(error_msg)
                    except Exception as e:
                        error_msg = f"HTTP error for node {node_host}: {str(e)}"
                        node_result['http_error'] = error_msg
                        results['errors'].append(error_msg)
                
                updated_nodes.append(node_result)
            results['cluster_nodes'] = updated_nodes
    
    # Test database connection if db_port is specified
    if system.get('db_port'):
        try:
            db_host = system.get('target')  # Use main target for DB
            db_status, db_message = test_db_connection(db_host, system['db_port'])
            results['db_status'] = db_status
            if not db_status:
                results['errors'].append(db_message)
        except Exception as e:
            results['errors'].append(f"Database connection error: {str(e)}")
            results['db_status'] = False
    
    # Update overall status - system is online if any test passes
    results['status'] = (
        (results['http_status'] is True) or 
        (results['ping_status'] is True) or 
        (results.get('cluster_nodes') and any(node['status'] for node in results['cluster_nodes']))
    )
    
    return results

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
                return False, f"Unknown host: {host}"
            elif "network is unreachable" in (stdout + stderr).lower():
                return False, f"Network is unreachable for host: {host}"
            elif "permission denied" in (stdout + stderr).lower():
                return False, f"Permission denied when pinging {host}. Try running with sudo."
            else:
                return False, f"Host {host} is not responding. {stderr if stderr else stdout}"
            
        return success, stdout if success else f"Host {host} is not responding. {stderr if stderr else ''}"
    except Exception as e:
        error_msg = f"Error pinging {host}: {str(e)}"
        print(error_msg)
        return False, error_msg

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
            return True, "Port is open"
            
        # Fallback to telnet
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return True, "Port is open"
        else:
            return False, f"Port {port} is closed on {host}"
    except Exception as e:
        return False, f"Error checking port {port} on {host}: {str(e)}"

if __name__ == '__main__':
    status_thread = threading.Thread(target=update_status)
    status_thread.daemon = True
    status_thread.start()
    
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    app.run(host=host, port=port, debug=True)

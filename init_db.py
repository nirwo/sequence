#!/usr/bin/env python3
from pymongo import MongoClient
from datetime import datetime
import argparse
import sys

def init_database(mongo_uri, drop_existing=False):
    try:
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client.get_database()
        print(f"Connected to MongoDB at {mongo_uri}")

        # Drop existing collections if requested
        if drop_existing:
            db.systems.drop()
            print("Dropped existing systems collection")

        # Create systems collection if it doesn't exist
        if "systems" not in db.list_collection_names():
            db.create_collection("systems")
            print("Created systems collection")

        # Create indexes
        db.systems.create_index("name", unique=True)
        print("Created index on name field")

        # Insert initial test data if collection is empty
        if db.systems.count_documents({}) == 0:
            initial_systems = [
                {
                    "name": "Test System 1",
                    "app_name": "Test App 1",
                    "target": "localhost",
                    "check_type": "ping",
                    "db_name": "N/A",
                    "db_type": "N/A",
                    "db_port": None,
                    "owner": "System Admin",
                    "mount_points": [],
                    "shutdown_sequence": [],
                    "cluster_nodes": [],
                    "created_at": datetime.utcnow(),
                    "last_check": datetime.utcnow(),
                    "status": False,
                    "sequence_status": "not_started",
                    "http_status": False,
                    "http_error": "",
                    "ping_status": False,
                    "ping_error": "",
                    "db_status": False,
                    "last_error": ""
                },
                {
                    "name": "Example Web Server",
                    "app_name": "WebApp",
                    "target": "https://example.com",
                    "check_type": "http",
                    "db_name": "N/A",
                    "db_type": "N/A",
                    "db_port": None,
                    "owner": "System Admin",
                    "mount_points": ["/var/www/html"],
                    "shutdown_sequence": ["stop service webapp", "wait 10s"],
                    "cluster_nodes": [],
                    "created_at": datetime.utcnow(),
                    "last_check": datetime.utcnow(),
                    "status": False,
                    "sequence_status": "not_started",
                    "http_status": False,
                    "http_error": "",
                    "ping_status": False,
                    "ping_error": "",
                    "db_status": False,
                    "last_error": ""
                }
            ]
            
            result = db.systems.insert_many(initial_systems)
            print(f"Inserted {len(result.inserted_ids)} initial systems")
        
        print("\nDatabase initialization completed successfully!")
        return True

    except Exception as e:
        print(f"Error initializing database: {str(e)}", file=sys.stderr)
        return False

    finally:
        client.close()

def main():
    parser = argparse.ArgumentParser(description='Initialize MongoDB database for App Monitor')
    parser.add_argument('--uri', required=True, help='MongoDB URI (e.g., mongodb://user:pass@host:port/dbname)')
    parser.add_argument('--drop', action='store_true', help='Drop existing collections before initialization')
    
    args = parser.parse_args()
    
    success = init_database(args.uri, args.drop)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

db = db.getSiblingDB('app_monitor');

// Create collections with schema validation
db.createCollection('systems', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['name', 'app_name', 'owner', 'created_at'],
            properties: {
                name: {
                    bsonType: 'string',
                    description: 'System name - required'
                },
                app_name: {
                    bsonType: 'string',
                    description: 'Application name - required'
                },
                check_type: {
                    enum: ['ping', 'http'],
                    description: 'Type of check to perform'
                },
                target: {
                    bsonType: 'string',
                    description: 'Target IP or URL'
                },
                db_name: {
                    bsonType: 'string',
                    description: 'Database name if applicable'
                },
                db_type: {
                    bsonType: 'string',
                    description: 'Database type if applicable'
                },
                mount_points: {
                    bsonType: 'string',
                    description: 'NFS/CIFS mount points'
                },
                owner: {
                    bsonType: 'string',
                    description: 'Application owner - required'
                },
                shutdown_sequence: {
                    bsonType: 'string',
                    description: 'Shutdown sequence instructions'
                },
                cluster_nodes: {
                    bsonType: 'array',
                    description: 'List of cluster nodes',
                    items: {
                        bsonType: 'string'
                    }
                },
                status: {
                    bsonType: 'bool',
                    description: 'Current system status'
                },
                created_at: {
                    bsonType: 'date',
                    description: 'Creation timestamp - required'
                },
                last_check: {
                    bsonType: 'date',
                    description: 'Last check timestamp'
                }
            }
        }
    }
});

// Create indexes
db.systems.createIndex({ "name": 1 }, { unique: true });
db.systems.createIndex({ "app_name": 1 });
db.systems.createIndex({ "owner": 1 });
db.systems.createIndex({ "status": 1 });
db.systems.createIndex({ "created_at": 1 });

// Insert some sample data if the collection is empty
if (db.systems.countDocuments() === 0) {
    db.systems.insertMany([
        {
            name: "Sample App Server",
            app_name: "Sample Application",
            check_type: "http",
            target: "http://app-server:8080",
            owner: "System Admin",
            status: false,
            created_at: new Date(),
            last_check: new Date(),
            shutdown_sequence: "1. Stop application service\n2. Verify no active connections",
            mount_points: "/mnt/data,/mnt/logs"
        },
        {
            name: "Database Cluster",
            app_name: "Core Database",
            check_type: "ping",
            target: "db-server",
            db_name: "production_db",
            db_type: "PostgreSQL",
            owner: "DBA Team",
            status: false,
            created_at: new Date(),
            last_check: new Date(),
            shutdown_sequence: "1. Stop application servers\n2. Wait for connections to drain\n3. Shutdown database",
            cluster_nodes: ["db-node-1.internal", "db-node-2.internal", "db-node-3.internal"]
        }
    ]);
}

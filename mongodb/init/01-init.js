// Create the database and collection
db = db.getSiblingDB('app_monitor');

// Drop existing collections to start fresh
db.systems.drop();

// Create the systems collection with validation
db.createCollection('systems', {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["name", "created_at"],
            properties: {
                name: {
                    bsonType: "string",
                    description: "Server name - required"
                },
                app_name: {
                    bsonType: ["string", "null"],
                    description: "Application name - optional"
                },
                check_type: {
                    bsonType: "string",
                    enum: ["http", "ping", "both"],
                    description: "Type of health check - defaults to ping"
                },
                target: {
                    bsonType: ["string", "null"],
                    description: "Target URL or IP address"
                },
                db_name: {
                    bsonType: ["string", "null"],
                    description: "Database name - optional"
                },
                db_type: {
                    bsonType: ["string", "null"],
                    description: "Database type - optional"
                },
                db_port: {
                    bsonType: ["int", "null"],
                    description: "Database port - optional"
                },
                owner: {
                    bsonType: ["string", "null"],
                    description: "System owner - optional"
                },
                shutdown_sequence: {
                    bsonType: ["string", "null"],
                    description: "Shutdown sequence steps - optional"
                },
                sequence_status: {
                    bsonType: ["string", "null"],
                    enum: ["not_started", "in_progress", "completed", null],
                    description: "Status of shutdown/startup sequence"
                },
                cluster_nodes: {
                    bsonType: ["array", "null"],
                    items: {
                        bsonType: "object",
                        required: ["host"],
                        properties: {
                            host: {
                                bsonType: "string",
                                description: "Node hostname or IP"
                            },
                            status: {
                                bsonType: "bool",
                                description: "Node status"
                            },
                            last_check: {
                                bsonType: ["date", "null"],
                                description: "Last node check timestamp"
                            }
                        }
                    },
                    description: "List of cluster nodes"
                },
                created_at: {
                    bsonType: "date",
                    description: "Creation timestamp - required"
                },
                last_check: {
                    bsonType: ["date", "null"],
                    description: "Last health check timestamp"
                },
                status: {
                    bsonType: "bool",
                    description: "Current system status"
                },
                db_status: {
                    bsonType: ["bool", "null"],
                    description: "Database connection status"
                },
                last_error: {
                    bsonType: ["string", "null"],
                    description: "Last error message"
                }
            }
        }
    },
    validationLevel: "moderate",
    validationAction: "warn"
});

// Create indexes
db.systems.createIndex({ "name": 1 }, { unique: true });
db.systems.createIndex({ "app_name": 1 });
db.systems.createIndex({ "status": 1 });
db.systems.createIndex({ "sequence_status": 1 });
db.systems.createIndex({ "created_at": 1 });
db.systems.createIndex({ "last_check": 1 });

// Insert sample data
db.systems.insertMany([
    {
        name: "webserver01",
        app_name: "Company Website",
        check_type: "http",
        target: "http://webserver01:8080",
        mount_points: ["/mnt/logs"],
        owner: "John Doe",
        shutdown_sequence: ["service nginx stop", "service app stop"],
        created_at: new Date(),
        last_check: null,
        status: false
    },
    {
        name: "dbserver01",
        check_type: "ping",
        target: "192.168.1.100",
        db_name: "main_db",
        db_type: "postgres",
        mount_points: ["/mnt/data", "/mnt/backup"],
        owner: "Jane Smith",
        shutdown_sequence: ["service postgresql stop"],
        created_at: new Date(),
        last_check: null,
        status: false
    },
    {
        name: "app-cluster",
        app_name: "Load Balancer",
        check_type: "http",
        target: "http://app-lb:8080",
        db_name: "app_db",
        db_type: "mysql",
        mount_points: ["/mnt/app/data"],
        owner: "Mike Johnson",
        shutdown_sequence: ["service haproxy stop", "service app stop"],
        cluster_nodes: ["app01.example.com", "app02.example.com", "app03.example.com"],
        created_at: new Date(),
        last_check: null,
        status: false
    }
]);

// Verify the setup
print("Checking database setup...");
print("Number of systems:", db.systems.count());
print("Indexes:");
db.systems.getIndexes().forEach(index => printjson(index));
print("MongoDB initialization completed successfully!");

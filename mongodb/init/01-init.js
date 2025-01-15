// Create the database and collection
db = db.getSiblingDB('app_monitor');

// Drop existing collections to start fresh
db.systems.drop();

// Create collection with schema validation
db.createCollection('systems', {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["name", "target"],
            properties: {
                name: {
                    bsonType: "string",
                    description: "System name - required"
                },
                app_name: {
                    bsonType: "string",
                    description: "Application name"
                },
                check_type: {
                    enum: ["http", "ping", "both"],
                    description: "Type of check to perform"
                },
                target: {
                    bsonType: "string",
                    description: "Target host/URL - required"
                },
                db_name: {
                    bsonType: "string",
                    description: "Database name"
                },
                db_type: {
                    bsonType: "string",
                    description: "Database type"
                },
                db_port: {
                    bsonType: "int",
                    description: "Database port"
                },
                mount_points: {
                    bsonType: "array",
                    items: {
                        bsonType: "string"
                    },
                    description: "Mount points to check"
                },
                owner: {
                    bsonType: "string",
                    description: "System owner"
                },
                shutdown_sequence: {
                    bsonType: "array",
                    items: {
                        bsonType: "string"
                    },
                    description: "Shutdown sequence commands"
                },
                cluster_nodes: {
                    bsonType: "array",
                    items: {
                        oneOf: [
                            {
                                bsonType: "string",
                                description: "Simple node host"
                            },
                            {
                                bsonType: "object",
                                required: ["host"],
                                properties: {
                                    host: {
                                        bsonType: "string",
                                        description: "Node hostname"
                                    },
                                    status: {
                                        bsonType: "bool",
                                        description: "Node status"
                                    },
                                    http_status: {
                                        bsonType: "bool",
                                        description: "HTTP check status"
                                    },
                                    http_error: {
                                        bsonType: "string",
                                        description: "HTTP check error"
                                    },
                                    ping_status: {
                                        bsonType: "bool",
                                        description: "Ping check status"
                                    },
                                    ping_error: {
                                        bsonType: "string",
                                        description: "Ping check error"
                                    },
                                    last_check: {
                                        bsonType: "date",
                                        description: "Last check timestamp"
                                    }
                                }
                            }
                        ]
                    },
                    description: "Cluster node information"
                },
                created_at: {
                    bsonType: "date",
                    description: "Creation timestamp"
                },
                last_check: {
                    bsonType: ["date", "null"],
                    description: "Last check timestamp"
                },
                status: {
                    bsonType: "bool",
                    description: "Overall system status"
                },
                sequence_status: {
                    enum: ["not_started", "in_progress", "completed"],
                    description: "Sequence status"
                },
                http_status: {
                    bsonType: ["bool", "null"],
                    description: "HTTP check status"
                },
                http_error: {
                    bsonType: ["string", "null"],
                    description: "HTTP check error"
                },
                ping_status: {
                    bsonType: ["bool", "null"],
                    description: "Ping check status"
                },
                ping_error: {
                    bsonType: ["string", "null"],
                    description: "Ping check error"
                },
                db_status: {
                    bsonType: ["bool", "null"],
                    description: "Database check status"
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
        status: false,
        sequence_status: "not_started",
        http_status: null,
        http_error: null,
        ping_status: null,
        ping_error: null,
        db_status: null,
        last_error: null
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
        status: false,
        sequence_status: "not_started",
        http_status: null,
        http_error: null,
        ping_status: null,
        ping_error: null,
        db_status: null,
        last_error: null
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
        cluster_nodes: [
            {
                host: "app01.example.com",
                status: false,
                http_status: null,
                http_error: null,
                ping_status: null,
                ping_error: null,
                last_check: null
            },
            {
                host: "app02.example.com",
                status: false,
                http_status: null,
                http_error: null,
                ping_status: null,
                ping_error: null,
                last_check: null
            },
            {
                host: "app03.example.com",
                status: false,
                http_status: null,
                http_error: null,
                ping_status: null,
                ping_error: null,
                last_check: null
            }
        ],
        created_at: new Date(),
        last_check: null,
        status: false,
        sequence_status: "not_started",
        http_status: null,
        http_error: null,
        ping_status: null,
        ping_error: null,
        db_status: null,
        last_error: null
    }
]);

// Verify the setup
print("Checking database setup...");
print("Number of systems:", db.systems.count());
print("Indexes:");
db.systems.getIndexes().forEach(index => printjson(index));
print("MongoDB initialization completed successfully!");

db = db.getSiblingDB('app_monitor');

// Create collections if they don't exist
db.createCollection('systems');

// Create indexes
db.systems.createIndex({ "name": 1 }, { unique: true });

// Insert some initial test data
const initialSystems = [
    {
        name: "Test System 1",
        app_name: "Test App 1",
        target: "localhost",
        check_type: "ping",
        db_name: "N/A",
        db_type: "N/A",
        db_port: null,
        owner: "System Admin",
        mount_points: [],
        shutdown_sequence: [],
        cluster_nodes: [],
        created_at: new Date(),
        last_check: new Date(),
        status: false,
        sequence_status: "not_started",
        http_status: false,
        http_error: "",
        ping_status: false,
        ping_error: "",
        db_status: false,
        last_error: ""
    }
];

// Insert initial data only if collection is empty
if (db.systems.countDocuments() === 0) {
    db.systems.insertMany(initialSystems);
}

// Create user if it doesn't exist
db.createUser({
    user: "app_user",
    pwd: "app_password",
    roles: [
        {
            role: "readWrite",
            db: "app_monitor"
        }
    ]
});

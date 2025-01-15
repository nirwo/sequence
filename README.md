# Application Monitoring System

A web-based application monitoring system that helps track the status of applications, databases, and servers. The system provides real-time monitoring with a 60-second refresh interval and supports various monitoring methods including ping and HTTP checks.

## Features

- Real-time monitoring of applications and servers
- Support for both ping and HTTP endpoint monitoring
- Cluster awareness for distributed applications
- Database dependency tracking
- Shutdown sequence management
- NFS/CIFS mount point tracking
- Modern, responsive web interface
- 60-second automatic refresh interval

## Prerequisites

- Python 3.8+
- MongoDB
- pip (Python package manager)

## Installation

1. Clone the repository
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Make sure MongoDB is installed and running on your system
   ```bash
   sudo systemctl start mongod
   ```

## Docker Installation

The easiest way to run the application is using Docker Compose:

1. Make sure you have Docker and Docker Compose installed
2. Clone the repository
3. Run the application stack:
   ```bash
   docker-compose up -d
   ```
4. The application will be available at:
   ```
   http://<your-host-ip>:5000
   ```
   
   To find your host IP address:
   ```bash
   # On Linux
   ip addr show
   # or
   hostname -I
   ```

### Docker Environment Variables

- `MONGO_URI`: MongoDB connection string (default: mongodb://admin:adminpassword@mongodb:27017/app_monitor?authSource=admin)

### Accessing MongoDB

The MongoDB instance is accessible at:
- Host: localhost
- Port: 27017
- Username: admin
- Password: adminpassword
- Database: app_monitor

### MongoDB Initialization

The MongoDB instance is initialized with:
- Schema validation for the systems collection
- Required indexes for optimal performance
- Sample data (only added if the collection is empty)

The initialization script is located in `mongodb/init/01-init.js` and will run automatically when the MongoDB container is first created. The script:
1. Creates the `systems` collection with schema validation
2. Sets up appropriate indexes
3. Adds sample data if the collection is empty

This initialization only happens when the MongoDB volume is first created. To force reinitialization:
```bash
docker-compose down -v  # Warning: This will delete all data
docker-compose up -d
```

### Stopping the Application

To stop the application:
```bash
docker-compose down
```

To stop the application and remove all data:
```bash
docker-compose down -v
```

## Running the Application

1. Start the application:
   ```bash
   python app.py
   ```
2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

## Adding a New System

1. Click the "Add System" button in the navigation bar
2. Fill in the required information:
   - System Name
   - Application Name
   - Check Type (ping/http)
   - Target (IP/URL)
   - Database Name (if applicable)
   - Mount Points
   - Application Owner
   - Shutdown Sequence
   - Cluster Nodes (if applicable)

## CSV Import

The application supports two methods of CSV import:

1. Quick Import: Uses the example CSV format
2. Mapped Import: Allows you to map any CSV format to the application's fields

### Example CSV Format

Download the example CSV template (`example_import.csv`) which contains the following fields:
- System Name
- Application Name
- Check Type (ping/http)
- Target URL/IP
- Database Name
- Database Type
- Mount Points (semicolon-separated)
- Owner
- Shutdown Sequence
- Cluster Nodes (comma-separated)

### Custom CSV Import

For custom CSV files:
1. Click "Import" → "Map & Import CSV"
2. Select your CSV file
3. Preview the data
4. Map your CSV columns to the application fields
5. Click Import

The mapping interface will attempt to automatically match fields with similar names, but you can adjust the mapping as needed. Fields can be skipped by selecting "-- Skip Field --" in the mapping dropdown.

## Monitoring Features

- Status indicators (green for up, red for down)
- Last check timestamp
- Real-time updates every 60 seconds
- Edit and delete functionality for each system
- Detailed view of system properties

## Security Notes

- Ensure MongoDB is properly secured in production
- Consider implementing authentication for the web interface
- Review and validate shutdown sequences before implementation

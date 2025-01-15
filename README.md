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

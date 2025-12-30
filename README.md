# Si-Ware Production Line Monitoring System

A modular, object-oriented Python desktop application for real-time sensor monitoring in production line environments.

## Project Structure

The project is organized into modular packages:

```
RT-ProductionLine-Sensors-Dashboard/
├── main.py                      # Main entry point
├── requirements.txt             # Python dependencies
│
├── core/                        # Core data models and logic
│   ├── __init__.py
│   └── sensor_data.py          # SensorReading, SensorStatus, SensorConfig, AlarmEvent
│
├── sensors/                     # Sensor communication modules
│   ├── __init__.py
│   ├── sensor_manager.py       # Unified sensor manager
│   ├── sensor_serial.py        # Serial communication
│   ├── sensor_tcp.py           # TCP communication
│   └── sensor_modbus.py        # Modbus communication
│
├── gui/                         # GUI components
│   ├── __init__.py
│   ├── main_gui.py             # Main PyQt5 GUI window
│   ├── metric_card.py          # Metric card widget
│   └── circular_progress.py    # Circular progress widget
│
├── services/                    # Services
│   ├── __init__.py
│   ├── alarm_notifications.py  # Notification system
│   └── remote_console.py       # WebSocket remote console
│
├── simulators/                  # Sensor simulators
│   ├── README.md               # Simulator documentation
│   ├── sensor_serial.py        # Unified serial sensor simulator (PTY)
│   ├── start_tcp_system.py     # TCP sensor system launcher
│   ├── run_tcp_sensor_clients.py # TCP sensor clients
│   ├── tcp_sensor_server.py    # TCP sensor server
│   ├── sensor_modbus.py        # Unified Modbus sensor simulator
│   ├── tcp_sensor_server.py    # TCP sensor server
│   ├── start_tcp_system.py     # Start TCP sensor system
│   └── run_tcp_sensor_clients.py # Run TCP sensor clients
│
├── config/                      # Configuration
│   └── config.json
│
├── api/                         # API documentation
│   ├── API_DOCUMENTATION.md     # Detailed API documentation
│   └── openapi.yaml            # OpenAPI 3.0 specification
│
├── web/                         # Web client
│   └── remote_console_client.html
│
├── scripts/                     # Utility scripts
│   ├── run_api_docs.sh         # Start API documentation server
│   ├── serve_api_docs.py       # API documentation server
│   ├── verify_project.py       # Project verification script
│   ├── test_desktop_notifications.py # Test desktop notifications
│   ├── test_modbus.py          # Test Modbus communication
│   ├── test_websocket.py       # Test WebSocket connection
│   ├── test_webhook.py         # Test webhook functionality
│   ├── test_webhook_server.py  # Test webhook server
│   ├── check_modbus_server.py  # Check Modbus server
│   ├── check_tcp_servers.py    # Check TCP servers
│   ├── read_sensor_serial.py   # Read serial sensor data
│   ├── read_modbus_frame.py    # Read Modbus frame
│   ├── generate_flowchart.py   # Generate system flowchart
│   └── convert_md_to_pdf.py    # Convert markdown to PDF
│
├── tests/                       # Unit tests
│   ├── __init__.py
│   └── test_sensor_data.py     # Sensor data tests
│
├── README.md                    # This file
├── COMPREHENSIVE_DOCUMENTATION.md # Complete system documentation
├── COMPREHENSIVE_DOCUMENTATION.pdf # PDF version
├── SYSTEM_FLOWCHART.md          # System flowchart documentation
├── SYSTEM_ARCHITECTURE.png      # System architecture diagram
├── DATA_FLOW.png                # Data flow diagram
└── STARTUP_SEQUENCE.png         # Startup sequence diagram
```

See `COMPREHENSIVE_DOCUMENTATION.md` for complete documentation.

## Features

### Core Features

- ✅ Real-time monitoring of 5+ sensors
- ✅ Multiple protocols: 2 Serial, 2 TCP, 1 Modbus
- ✅ Worker threads for all communication
- ✅ Thread-safe communication (queues/signals)
- ✅ Real-time GUI updates (2+ Hz)
- ✅ Alarm system with LOW/HIGH limits
- ✅ Visual dashboard with plots

### Bonus Features

- ✅ Remote Maintenance Console (WebSocket)
- ✅ Alarm Notification System (Webhook, Desktop Notifications)
  - **Desktop notifications work automatically on Linux Ubuntu and Windows**
  - No configuration needed - enabled by default

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Start Simulators

```bash
# Start all simulators
./scripts/run_all_sensors.sh

# Or start individual simulators
python3 simulators/sensor_serial.py --sensor-id 1 --sensor-type temperature  # Temperature (Serial/PTY)
python3 simulators/sensor_serial.py --sensor-id 2 --sensor-type pressure  # Pressure (Serial/PTY)
python3 simulators/start_tcp_system.py --server-ports 5000 --sensor flow:3:localhost:5000 --sensor vibration:4:localhost:5000  # TCP Sensors
python3 simulators/sensor_modbus.py --sensor-id 5 --sensor-type voltage  # Voltage (Modbus/TCP)
```

**Note:** For Serial sensors (1 & 2), note the PTY path printed when they start and update `config/config.json`.

### 2. Start Application

```bash
python3 main.py
```

Or use the convenience script:

```bash
./scripts/run_app.sh
```

The GUI application will start and automatically:

- Start the Remote Console WebSocket server (port 8765)
- Start the HTTP server for web interface (port 8080)

### 3. Access Remote Console (Optional)

The remote console starts automatically with the main application. Open:

```
http://localhost:8080/remote_console_client.html
```

Default credentials: `admin` / `admin123`

## Configuration

Edit `config/config.json` to configure:

- Sensors and their protocols
- Alarm limits
- Notification settings
- Remote console settings

## Documentation

Complete documentation is available in the root directory:

- `COMPREHENSIVE_DOCUMENTATION.md` - Complete system documentation (single file)
- `COMPREHENSIVE_DOCUMENTATION.pdf` - PDF version
- `README.md` - This quick overview file

### API Documentation

Interactive API documentation with Swagger UI:

```bash
python3 scripts/serve_api_docs.py
```

Then open: `http://localhost:8081/`

Or view the documentation files:

- `api/API_DOCUMENTATION.md` - Detailed markdown API documentation
- `api/openapi.yaml` - OpenAPI 3.0 specification

## Testing

```bash
# Run unit tests
python3 -m pytest tests/

# Verify project
python3 scripts/verify_project.py

# Test desktop notifications
python3 scripts/test_desktop_notifications.py
```

## Architecture

- **Modular Design**: Organized into logical packages
- **OOP**: Object-oriented design throughout
- **Thread-Safe**: Worker threads with queues and signals
- **Separation of Concerns**: GUI, communication, services separated

See `COMPREHENSIVE_DOCUMENTATION.md` for complete details on architecture, threading, and all features.

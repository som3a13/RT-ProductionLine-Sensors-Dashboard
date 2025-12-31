# Production Line Remote Maintenance Console

A comprehensive real-time monitoring and maintenance system for industrial production lines. Monitor multiple sensors across different communication protocols, manage alarms, and access remote maintenance features through both desktop and web interfaces.

## 🚀 Key Features

### Core Monitoring
- ✅ **Real-Time Sensor Monitoring**: Live data from multiple sensors with 2+ Hz refresh rate
- ✅ **Multi-Protocol Support**: Serial (PTY), TCP/IP, and Modbus/TCP communication
- ✅ **Real-Time Rolling Plots**: Per-sensor plots showing last 15 seconds of data with fixed y-axis based on sensor limits
- ✅ **Color-Coded Status**: Visual status indicators (Green: OK, Yellow: Low/High Alarm, Red: Faulty)
- ✅ **Global System Health**: Overall system health indicator showing Normal/Warning/Critical status

### Alarm Management
- ✅ **Intelligent Alarm Detection**: Automatic detection of LOW/HIGH limits and faulty sensors (-999)
- ✅ **Alarm Log with Limits**: Complete alarm history including low/high limits at time of alarm
- ✅ **State Transition Notifications**: Notifications sent only on state transitions (prevents spam)
- ✅ **Dashboard Alarm Table**: Quick view of recent alarms directly on dashboard
- ✅ **Multiple Notification Methods**: Desktop notifications (Linux/Windows) and webhook support

### Maintenance Console
- ✅ **Password-Protected Maintenance Tab**: Secure access with username/password authentication from `config.json`
- ✅ **Comprehensive Alarm Log**: Full alarm history with timestamps, values, types, and limits
- ✅ **System Tools**: Remote commands (self-test, snapshot, system diagnostics)
- ✅ **Live Log Viewer**: Real-time system logs including:
  - User login/logout events
  - Alarm clearing events
  - Sensor connection attempts
  - System diagnostics
- ✅ **Web-Based Remote Console**: Access from any browser with authentication

### User Interface
- ✅ **Modern Light Theme**: Clean, professional interface
- ✅ **Resizable Window**: Flexible window sizing for different screen sizes
- ✅ **Scrollable Components**: Sensor table and plots section are scrollable for variable number of sensors
- ✅ **Custom Application Icon**: Professional branding with custom icon and favicon
- ✅ **Responsive Layout**: Optimized layout with sensor table on left, plots on right

## 📋 Project Structure

```
RT-ProductionLine-Sensors-Dashboard/
├── main.py                      # Main entry point
├── requirements.txt             # Python dependencies
├── fav.png                      # Application icon and favicon
│
├── core/                        # Core data models and logic
│   ├── __init__.py
│   └── sensor_data.py          # SensorReading, SensorStatus, SensorConfig, AlarmEvent
│
├── sensors/                     # Sensor communication modules
│   ├── __init__.py
│   ├── sensor_manager.py       # Unified sensor manager
│   ├── sensor_serial_comm.py  # Serial communication
│   ├── sensor_tcp_comm.py      # TCP communication
│   └── sensor_modbus_comm.py  # Modbus communication
│
├── gui/                         # GUI components
│   ├── __init__.py
│   ├── main_gui.py             # Main PyQt5 GUI window
│   ├── components/              # Reusable GUI components
│   │   ├── splitter.py         # Non-resizable splitter
│   │   └── helpers.py          # Helper classes
│   ├── stylesheet/             # Styling
│   │   └── styles.qss          # Light theme stylesheet
│   └── tabs/                    # Tab components (future modularization)
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
│   └── sensor_modbus.py        # Unified Modbus sensor simulator
│
├── config/                      # Configuration
│   └── config.json             # Main configuration file
│
├── web/                         # Web client
│   └── remote_console_client.html # Remote console web interface
│
├── scripts/                     # Utility scripts
│   ├── verify_project.py       # Project verification
│   ├── test_desktop_notifications.py # Test desktop notifications
│   ├── test_modbus.py          # Test Modbus communication
│   ├── test_websocket.py       # Test WebSocket connection
│   ├── test_webhook.py         # Test webhook functionality
│   ├── test_webhook_server.py  # Test webhook server
│   ├── read_sensor_serial.py   # Read serial sensor data
│   ├── read_modbus_frame.py    # Read Modbus frames
│   ├── check_modbus_server.py  # Check Modbus server
│   ├── check_tcp_servers.py    # Check TCP servers
│   ├── serve_api_docs.py       # Serve API documentation
│   ├── run_api_docs.sh         # Run API docs script
│   ├── generate_flowchart.py   # Generate system flowchart
│   └── convert_md_to_pdf.py    # Convert markdown to PDF
│
├── tests/                       # Unit tests
│   ├── __init__.py
│   ├── README.md               # Test documentation
│   ├── test_sensor_data.py     # Sensor data tests (32 tests)
│   └── test_results.png        # Test execution screenshot
│
├── api/                         # API documentation
│   ├── API_DOCUMENTATION.md    # Detailed API documentation
│   └── openapi.yaml            # OpenAPI 3.0 specification
│
├── README.md                    # This file
├── Project_Documentation.md     # Complete system documentation
├── Project_Documentation.pdf    # PDF version
├── SYSTEM_FLOWCHART.md          # System flowchart documentation
├── SYSTEM_ARCHITECTURE.png      # System architecture diagram
├── DATA_FLOW.png                # Data flow diagram
├── STARTUP_SEQUENCE.png         # Startup sequence diagram
└── Si-Ware_System_-_PE_Assesment_v3.pdf # Assessment document
```

## 🛠️ Setup Steps

### Prerequisites
- Python 3.8 or higher
- Linux (Ubuntu recommended) or Windows
- Internet connection (for installing packages)

### Step 1: Clone/Download Project

```bash
cd /path/to/RT-ProductionLine-Sensors-Dashboard
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Required Packages:**
- `PyQt5==5.15.10` - GUI framework
- `pyqtgraph==0.13.3` - Real-time plotting
- `numpy==1.24.3` - Numerical operations
- `pyserial==3.5` - Serial communication
- `pymodbus==3.5.4` - Modbus communication
- `websockets==12.0` - WebSocket server
- `aiohttp==3.9.1` - Async HTTP
- `requests==2.31.0` - HTTP requests

### Step 3: Verify Installation

```bash
python3 scripts/verify_project.py
```

This script verifies:
- All required files exist
- Python imports work correctly
- Configuration is valid
- Dependencies are installed

### Step 4: Configure Sensors

Edit `config/config.json` to configure your sensors:

1. **Add Sensor Definitions**: Add sensor entries to the `sensors` array
2. **Set Alarm Limits**: Configure `low_limit` and `high_limit` for each sensor
3. **Configure Protocols**: Set `protocol` and `protocol_config` for each sensor
4. **Set Remote Console Users**: Configure users in `remote_console.users`

See [Configuration](#-configuration) section for detailed examples.

## 🚀 Running Instructions

### Step 1: Start Sensor Simulators

Start sensor simulators based on your configuration. You can run multiple simulators concurrently:

#### Serial Sensors (PTY)

```bash
# Single sensor
python3 simulators/sensor_serial.py --config "temperature:1:115200:8N1"

# Multiple sensors in one command
python3 simulators/sensor_serial.py \
  --config "temperature:1:115200:8N1" \
  --config "pressure:2:115200:8N1" \
  --config "flow:3:115200:8N1"

# Or run in separate terminals
python3 simulators/sensor_serial.py --config "temperature:1:115200:8N1"
python3 simulators/sensor_serial.py --config "pressure:2:115200:8N1"
```

**Important:** Note the PTY path printed when serial simulators start (e.g., `PTY device: /dev/pts/9`) and update `config/config.json` with the correct paths.

#### TCP Sensors

```bash
# Start TCP system (servers and clients)
python3 simulators/start_tcp_system.py \
  --server-ports 5000 5001 \
  --sensor flow:3:localhost:5000:10:100:L/min \
  --sensor vibration:4:localhost:5000:0:5:mm/s \
  --sensor flow:6:localhost:5001:10:100:L/min
```

#### Modbus Sensors

```bash
# Single Modbus sensor
python3 simulators/sensor_modbus.py --config "voltage:5:localhost:1502:1:0"

# Multiple Modbus sensors
python3 simulators/sensor_modbus.py --config "voltage:5:localhost:1502:1:0"
python3 simulators/sensor_modbus.py --config "temperature:7:localhost:1503:2:0"
```

### Step 2: Update Configuration

After starting simulators, update `config/config.json`:

1. **Serial Sensors**: Update `protocol_config.port` with the PTY path from simulator output
2. **TCP Sensors**: Verify `protocol_config.host` and `protocol_config.port` match your TCP servers
3. **Modbus Sensors**: Verify `protocol_config.host`, `protocol_config.port`, `protocol_config.unit_id`, and `protocol_config.register`

### Step 3: Start Main Application

```bash
python3 main.py
```

The GUI application will:
- Load sensor configurations from `config/config.json`
- Start the Remote Console WebSocket server (port 8765)
- Start the HTTP server for web interface (port 8080)
- Display the main window with Dashboard tab

### Step 4: Connect to Sensors

1. Click the **"Connect"** button in the Dashboard tab
2. The system will connect to all configured sensors
3. Real-time data will start appearing in the sensor table and plots
4. Check the global system health indicator for overall status

### Step 5: Access Features

#### Desktop Application
- **Dashboard Tab**: Real-time sensor monitoring with plots and status table
- **Maintenance Console Tab**: Password-protected access to:
  - Alarm Log (with low/high limits)
  - System Tools (self-test, snapshot)
  - Live Log Viewer (real-time system logs)

#### Web Interface
1. Open your browser: `http://localhost:8080/remote_console_client.html`
2. Login with credentials from `config.json`:
   - **Admin**: `admin` / `admin123` (full access)
   - **Operator**: `operator` / `operator123` (read-only)
   - **Viewer**: `viewer` / `viewer123` (read-only)
3. Access real-time sensor data, alarms, and system commands

## ⚙️ Configuration

Edit `config/config.json` to configure:

### Sensors
```json
{
  "sensors": [
    {
      "name": "Temperature Sensor 1",
      "id": 1,
      "low_limit": 20.0,
      "high_limit": 80.0,
      "unit": "°C",
      "protocol": "serial",
      "protocol_config": {
        "port": "/dev/pts/2",
        "baudrate": 115200,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1
      }
    }
  ]
}
```

### Alarm Settings
```json
{
  "alarm_settings": {
    "enable_notifications": true,
    "enable_desktop_notifications": true,
    "webhook_url": "http://localhost:3000/webhook"
  }
}
```

### Remote Console Users
```json
{
  "remote_console": {
    "enabled": true,
    "host": "localhost",
    "port": 8765,
    "http_port": 8080,
    "users": {
      "admin": {
        "password": "admin123",
        "permissions": ["read", "write", "commands"]
      }
    }
  }
}
```

## 📊 Features Overview

### Dashboard Features

1. **Sensor Status Table** (Left Panel)
   - Real-time sensor readings
   - Color-coded rows (Green: OK, Yellow: Alarm, Red: Faulty)
   - Columns: ID, Sensor Name, Latest Value, Unit, Timestamp, Status
   - Scrollable for variable number of sensors

2. **Real-Time Plots** (Right Panel)
   - Individual plot per sensor
   - Rolling 15-second window
   - Fixed y-axis based on sensor limits
   - Scrollable for multiple sensors

3. **Global System Health Indicator**
   - Overall system status (Normal/Warning/Critical)
   - Located beside Connect/Disconnect button
   - Color-coded status display

4. **Dashboard Alarm Table**
   - Quick view of last 10 alarms
   - Shows time, sensor name, value, alarm type, and limits

### Maintenance Console Features

1. **Authentication**
   - Username/password from `config.json`
   - Content hidden until authenticated
   - Secure access to sensitive features

2. **Alarm Log Tab**
   - Complete alarm history
   - Columns: Time, Sensor Name, Value, Alarm Type, Low Limit, High Limit, Unit
   - Export to CSV functionality
   - Clear log functionality

3. **System Tools Tab**
   - Run Self-Test: System diagnostics
   - Get Snapshot: Detailed system state
   - Results displayed in formatted text

4. **Live Log Viewer Tab**
   - Real-time system logs
   - Color-coded log levels (INFO, WARNING, ERROR, ALARM, FAULT)
   - Logs include:
     - User login/logout events
     - Alarm clearing events
     - Sensor connection attempts
     - System diagnostics
   - No forced auto-scrolling (manual scroll control)

### Notification System

- **State Transition Notifications**: Notifications sent only when sensor status changes (not continuously)
- **Desktop Notifications**: Automatic on Linux (via `notify-send`) and Windows (via `win10toast`)
- **Webhook Notifications**: HTTP POST to configurable URL
- **Alarm Types**: LOW, HIGH, FAULT (for -999 values)

## 🔧 Usage Guide

### Daily Operations

1. **Start Simulators**: Run sensor simulators in separate terminals
2. **Start Application**: Launch `python3 main.py`
3. **Connect Sensors**: Click "Connect" button in dashboard
4. **Monitor Dashboard**: View real-time sensor data and plots
5. **Check Alarms**: View dashboard alarm table or maintenance console alarm log
6. **Access Maintenance**: Login to Maintenance Console tab for detailed logs and tools

### Remote Access

1. **Open Web Interface**: Navigate to `http://localhost:8080/remote_console_client.html`
2. **Login**: Use credentials from `config.json`
3. **View Data**: Access real-time sensor data, alarms, and logs
4. **Run Commands**: Execute system diagnostics and get snapshots

## 📡 Protocol Descriptions

### Serial Communication (PTY)

**Protocol:** Serial over Pseudo-Terminal (PTY)

**Configuration:**
- Baudrate: 115200 (configurable, default: 115200)
- Data bits: 8
- Parity: None (N)
- Stop bits: 1
- Frame format: JSON terminated by newline (`\n`)

**Frame Format:**
```json
{
  "sensor_id": 1,
  "sensor_name": "Temperature Sensor 1",
  "value": 45.5,
  "timestamp": "2025-01-15T12:00:00",
  "status": "OK",
  "unit": "°C"
}
```

**How It Works:**
1. Simulator creates a PTY pair (master/slave)
2. Simulator writes JSON frames to master file descriptor
3. Application connects to slave device (e.g., `/dev/pts/9`)
4. Application reads JSON frames terminated by newline
5. Frames are parsed and converted to `SensorReading` objects

**Example Frame (Single Line):**
```
{"sensor_id":1,"sensor_name":"Temperature Sensor 1","value":45.5,"timestamp":"2025-01-15T12:00:00","status":"OK","unit":"°C"}\n
```

**Worker Thread Model:**
- One worker thread per unique serial port
- Multiple sensors on the same port share one worker thread
- Example: 3 sensors on 3 different ports = 3 worker threads
- Example: 5 sensors on 2 ports (3 on port A, 2 on port B) = 2 worker threads

---

### TCP/IP Communication

**Protocol:** TCP/IP Socket

**Configuration:**
- Host: localhost (configurable)
- Port: 5000, 5001, etc. (configurable)
- Frame format: JSON terminated by newline (`\n`)

**Frame Format:**
Same as Serial (JSON):
```json
{
  "sensor_id": 3,
  "sensor_name": "Flow Rate Sensor 1",
  "value": 75.2,
  "timestamp": "2025-01-15T12:00:00",
  "status": "OK",
  "unit": "L/min"
}
```

**How It Works:**
1. TCP server is created on specified port (e.g., 5000)
2. Multiple sensor clients connect to the same server
3. Application connects as TCP client to the server
4. Server relays JSON frames from all connected sensor clients
5. Application reads frames terminated by newline and parses them

**Architecture:**
- **TCP Server**: Central server that accepts multiple sensor client connections
- **TCP Clients**: Individual sensor simulators that connect to the server
- **Application**: Connects to server and receives data from all sensors

**Example Frame (Single Line):**
```
{"sensor_id":3,"sensor_name":"Flow Rate Sensor 1","value":75.2,"timestamp":"2025-01-15T12:00:00","status":"OK","unit":"L/min"}\n
```

**Worker Thread Model:**
- One worker thread per unique TCP server (host:port combination)
- Multiple sensors connecting to the same server share one worker thread
- Example: 4 sensors on 2 different servers = 2 worker threads
- Example: 6 sensors on 3 servers (2 per server) = 3 worker threads

---

### Modbus/TCP Communication

**Protocol:** Modbus/TCP (Function Code 3 - Read Holding Registers)

**Configuration:**
- Host: localhost (configurable)
- Port: 1502 (default Modbus port, configurable)
- Unit ID: 1 (configurable)
- Register: 0 (configurable, starting register address)
- Function Code: 3 (Read Holding Registers)

**Frame Format (Modbus/TCP):**

**Request Frame (Application → Sensor):**
```
MBAP Header (7 bytes):
  - Transaction ID (2 bytes): 0x0001
  - Protocol ID (2 bytes): 0x0000 (Modbus)
  - Length (2 bytes): 0x0006
  - Unit ID (1 byte): 0x01

PDU (Protocol Data Unit, 5 bytes):
  - Function Code (1 byte): 0x03 (Read Holding Registers)
  - Starting Address (2 bytes): 0x0000
  - Quantity (2 bytes): 0x0001 (read 1 register)
```

**Response Frame (Sensor → Application):**
```
MBAP Header (7 bytes):
  - Transaction ID (2 bytes): 0x0001
  - Protocol ID (2 bytes): 0x0000 (Modbus)
  - Length (2 bytes): 0x0005
  - Unit ID (1 byte): 0x01

PDU (Protocol Data Unit):
  - Function Code (1 byte): 0x03
  - Byte Count (1 byte): 0x02
  - Register Value (2 bytes): 0x01C7 (455 decimal = 45.5)
```

**Value Encoding:**
- Values stored as 16-bit integers (0-65535)
- Scaled by 10 for decimal precision
- Example: 455 = 45.5, 2205 = 220.5
- Negative values use two's complement
- Example: -999.0 = 65536 - 9990 = 55546 (0xD8FA)

**How It Works:**
1. Modbus/TCP server is created on specified port (e.g., 1502)
2. Application connects as Modbus client
3. Application sends Function Code 3 requests (Read Holding Registers)
4. Server responds with register values (16-bit integers)
5. Application converts integer values to float by dividing by 10
6. Example: Register value 455 → Float value 45.5

**Worker Thread Model:**
- One worker thread per unique Modbus server (host:port combination)
- Multiple sensors on the same server share one worker thread
- Example: 2 sensors on 2 different servers = 2 worker threads
- Example: 3 sensors on 1 server = 1 worker thread

---

### Protocol Comparison

| Protocol | Frame Format | Termination | Encoding | Worker Threads |
|----------|--------------|-------------|----------|----------------|
| **Serial (PTY)** | JSON | Newline (`\n`) | Text | One per unique port |
| **TCP/IP** | JSON | Newline (`\n`) | Text | One per unique host:port |
| **Modbus/TCP** | Binary (MBAP + PDU) | TCP packet | 16-bit integer × 10 | One per unique host:port |

### Common Features

All protocols support:
- Multiple sensors per communication endpoint
- Real-time data streaming
- Automatic reconnection on failure
- Thread-safe communication
- Configurable alarm limits
- Status indication (OK, LOW_ALARM, HIGH_ALARM, FAULTY)

## 📚 API Documentation

### WebSocket API

The system provides a WebSocket-based API for remote access to sensor data, alarms, and system control.

**Base URL:** `ws://localhost:8765`

**Authentication:**
All connections require authentication before accessing commands:
```json
{
  "type": "auth",
  "username": "admin",
  "password": "admin123"
}
```

**Available Commands:**

1. **`get_status`** - Get system status summary
   ```json
   {
     "type": "command",
     "command": "get_status"
   }
   ```

2. **`get_sensors`** - Get all sensor readings
   ```json
   {
     "type": "command",
     "command": "get_sensors"
   }
   ```

3. **`get_alarms`** - Get alarm log entries (includes low_limit and high_limit)
   ```json
   {
     "type": "command",
     "command": "get_alarms",
     "limit": 100
   }
   ```

4. **`clear_alarms`** - Clear alarm log (requires `write` permission)
   ```json
   {
     "type": "command",
     "command": "clear_alarms"
   }
   ```

5. **`get_logs`** - Get system log entries
   ```json
   {
     "type": "command",
     "command": "get_logs",
     "limit": 50
   }
   ```

6. **`run_self_test`** - Run system diagnostics (requires `commands` permission)
   ```json
   {
     "type": "command",
     "command": "run_self_test"
   }
   ```

7. **`get_snapshot`** - Get detailed system snapshot
   ```json
   {
     "type": "command",
     "command": "get_snapshot"
   }
   ```

8. **`set_limit`** - Set alarm limits for a sensor (requires `write` permission)
   ```json
   {
     "type": "command",
     "command": "set_limit",
     "sensor_id": 1,
     "low_limit": 20.0,
     "high_limit": 80.0
   }
   ```

**User Permissions:**
- **read**: View sensor data and alarms
- **write**: Clear alarms, modify settings
- **commands**: Execute system commands (self-test, snapshot)

**Response Format:**
All responses are JSON messages with a `type` field indicating the response type:
- `status` - System status response
- `sensors` - Sensor data response
- `alarms` - Alarm log response
- `logs` - System logs response
- `self_test` - Self-test results
- `snapshot` - System snapshot
- `success` - Command success
- `error` - Error response

### Detailed API Documentation

For complete API documentation, see:
- **`api/API_DOCUMENTATION.md`** - Detailed markdown API documentation with examples
- **`api/openapi.yaml`** - OpenAPI 3.0 specification

### Interactive API Documentation

View interactive API documentation with Swagger UI:

```bash
python3 scripts/serve_api_docs.py
```

Then open: `http://localhost:8081/`

This provides:
- Visual API explorer
- Test endpoints directly from browser
- Request/response examples
- Schema definitions

## 🧪 Testing

```bash
# Run unit tests
python3 -m pytest tests/

# Verify project
python3 scripts/verify_project.py

# Test desktop notifications
python3 scripts/test_desktop_notifications.py

# Test WebSocket connection
python3 scripts/test_websocket.py
```

## 🏗️ Architecture

- **Modular Design**: Organized into logical packages
- **OOP**: Object-oriented design throughout
- **Thread-Safe**: Worker threads with queues and signals
- **Separation of Concerns**: GUI, communication, services separated
- **Port-Based Workers**: One worker thread per unique communication endpoint (not per sensor)

## 🔐 Security

- **Password Protection**: Maintenance console requires authentication
- **User Permissions**: Role-based access control (read, write, commands)
- **Secure WebSocket**: Authentication required for all remote console commands

## 🎨 User Interface

- **Light Theme**: Modern, clean interface
- **Resizable Window**: Flexible sizing
- **Custom Icon**: Professional branding
- **Color-Coded Status**: Intuitive visual feedback
- **Scrollable Components**: Support for variable number of sensors

## 📝 Recent Updates

- ✅ Real-time rolling plots (15-second window)
- ✅ Global system health indicator
- ✅ Color-coded sensor status
- ✅ Maintenance Console with authentication
- ✅ Alarm log with low/high limits
- ✅ Live log viewer with system events
- ✅ State transition notifications (prevents spam)
- ✅ Dashboard alarm table
- ✅ Application icon and favicon
- ✅ Light theme
- ✅ Multiple sensor simulator support

## 🆘 Troubleshooting

### Common Issues

1. **"ModuleNotFoundError"**: Run from project root or set `PYTHONPATH=.`
2. **"Serial port not found"**: Ensure simulators are running and PTY paths in `config.json` are correct
3. **"WebSocket connection failed"**: Check firewall settings and ensure port 8765 is available
4. **"No sensor data"**: Click "Connect" button and verify simulators are running

### Debug

- Check connection status: System Tools → Get Snapshot
- View live logs: Maintenance Console → Live Log Viewer
- Test individual components: Use scripts in `scripts/` directory

## 📄 License

This project is part of the Si-Ware Production Line Monitoring System.

## 👥 Support

For detailed information, refer to:
- `Project_Documentation.md` - Complete system documentation
- `Project_Documentation.pdf` - PDF version
- `tests/README.md` - Unit tests documentation
- `simulators/README.md` - Sensor simulators documentation
- `api/API_DOCUMENTATION.md` - API reference
- `SYSTEM_FLOWCHART.md` - System flowchart documentation
- Source code comments for implementation details

---

*Last Updated: January 2025*

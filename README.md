# Production Line Remote Maintenance Console

A comprehensive real-time monitoring and maintenance system for industrial production lines. Monitor multiple sensors across different communication protocols, manage alarms, and access remote maintenance features through both desktop and web interfaces.

## Key Features

- **Real-Time Sensor Monitoring**: Live data from multiple sensors with 2+ Hz refresh rate
- **Multi-Protocol Support**: Serial (PTY), TCP/IP, and Modbus/TCP communication
- **Real-Time Rolling Plots**: Per-sensor plots showing last 15 seconds of data
- **Color-Coded Status**: Visual status indicators (Green: OK, Yellow: Alarm, Red: Faulty)
- **Global System Health**: Overall system health indicator
- **Alarm Management**: Automatic detection with complete alarm history and notifications
- **Maintenance Console**: Password-protected access with alarm log, system tools, and live logs
- **Web-Based Remote Console**: Browser access with authentication
- **Desktop & Webhook Notifications**: Platform-specific notifications and HTTP webhooks

## Quick Start

### Prerequisites

- **Python 3.8 or higher** (use `python3` command)
- **pip3** for installing dependencies
- **Linux** (Ubuntu recommended) or **Windows**
- Internet connection (for installing packages)

### Step 1: Install Dependencies

```bash
# Make sure you're in the project directory
cd /path/to/RT-ProductionLine-Sensors-Dashboard

# Install all required packages using pip3
pip3 install -r requirements.txt
```

**Note:** Use `python3` and `pip3` commands (not `python` or `pip`) to ensure you're using Python 3.

### Step 2: Configure Sensors

**Important:** Before starting simulators, ensure your `config/config.json` matches the sensor IDs, ports, and protocols you'll use in the simulator commands below.

Your `config/config.json` should have sensors configured like this (matching the simulators you'll start):

```json
{
  "sensors": [
    {
      "name": "Flow Rate Sensor 1",
      "id": 3,
      "low_limit": 10.0,
      "high_limit": 100.0,
      "unit": "L/min",
      "protocol": "tcp",
      "protocol_config": {
        "host": "localhost",
        "port": 5000
      }
    },
    {
      "name": "Flow Rate Sensor 2",
      "id": 6,
      "low_limit": 10.0,
      "high_limit": 100.0,
      "unit": "L/min",
      "protocol": "tcp",
      "protocol_config": {
        "host": "localhost",
        "port": 5001
      }
    },
    {
      "name": "Vibration Sensor 1",
      "id": 4,
      "low_limit": 0.0,
      "high_limit": 5.0,
      "unit": "mm/s",
      "protocol": "tcp",
      "protocol_config": {
        "host": "localhost",
        "port": 5000
      }
    },
    {
      "name": "Voltage Sensor 1",
      "id": 5,
      "low_limit": 200.0,
      "high_limit": 240.0,
      "unit": "V",
      "protocol": "modbus",
      "protocol_config": {
        "host": "localhost",
        "port": 1502,
        "unit_id": 1,
        "register": 0
      }
    },
    {
      "name": "Pressure Sensor 2",
      "id": 7,
      "low_limit": 50.0,
      "high_limit": 150.0,
      "unit": "PSI",
      "protocol": "modbus",
      "protocol_config": {
        "host": "localhost",
        "port": 1502,
        "unit_id": 2,
        "register": 0
      }
    }
  ]
}
```

**Critical:** The sensor IDs, ports, and protocols in `config.json` **must match** the simulators you start below!

### Step 3: Start Sensor Simulators

**Option A: Automated Headless Startup (Recommended - Works on Both Linux and Windows)**

Use the headless startup script that automatically starts all simulators and updates `config.json`:

**Linux:**

```bash
./scripts/start_system_linux.sh
```

**Windows:**

```cmd
scripts\start_system_windows.bat
```

**Or use the Python script directly (Cross-platform):**

```bash
# Linux
python3 ./scripts/start_system.py \
    --serial "temperature:1:115200:8N1" \
    --com-port COM20 \
    --serial "pressure:2:115200:8N1" \
    --com-port COM22 \
    --modbus "voltage:5:localhost:1502:1:0" \
    --modbus "pressure:7:localhost:1502:2:0" \
    --tcp-server-ports 5000 5001 \
    --tcp-sensor "flow:3:localhost:5000" \
    --tcp-sensor "vibration:4:localhost:5000" \
    --tcp-sensor "flow:6:localhost:5001" \
    --webhook \
    --main-app

# Windows (adjust COM ports based on your available ports)
python scripts\start_system.py ^
    --serial "temperature:1:115200:8N1" ^
    --com-port COM20 ^
    --serial "pressure:2:115200:8N1" ^
    --com-port COM22 ^
    --modbus "voltage:5:localhost:1502:1:0" ^
    --modbus "pressure:7:localhost:1502:2:0" ^
    --tcp-server-ports 5000 5001 ^
    --tcp-sensor "flow:3:localhost:5000" ^
    --tcp-sensor "vibration:4:localhost:5000" ^
    --tcp-sensor "flow:6:localhost:5001" ^
    --webhook ^
    --main-app
```

**What the headless startup scripts do:**

- Start all simulators in the background
- **Linux**: Automatically capture PTY paths from serial simulators
- **Windows**: Automatically handle COM port pairs (simulator uses COM20, config gets COM21)
- Update `config.json` with correct ports and paths
- Start the webhook server (if `--webhook` is specified)
- Start the main application (if `--main-app` is specified)
- Handle Ctrl+C to stop all processes gracefully

**Windows COM Port Notes:**

- For virtual COM ports, install com0com first using `install_com0com_simple.bat`
- Adjust COM port numbers (COM20, COM22) in the commands based on your available ports
- The script automatically handles COM port pairing (simulator port → paired port in config)

**Option B: Manual Startup (Separate Terminals)**

Open **separate terminal windows** for each command. Run them in this order:

#### Terminal 1: Modbus Sensors

```bash
python3 ./simulators/sensor_modbus.py --config "voltage:5:localhost:1502:1:0" --config "pressure:7:localhost:1502:2:0"
```

#### Terminal 2: TCP Sensors

```bash
python3 ./simulators/start_tcp_system.py --server-ports 5000 5001 --sensor flow:3:localhost:5000 --sensor vibration:4:localhost:5000 --sensor flow:6:localhost:5001
```

**Note:** For serial sensors (Linux), you would also run:

```bash
python3 ./simulators/sensor_serial.py --config "temperature:1:115200:8N1" --config "pressure:2:115200:8N1"
```

Then update `config.json` with the PTY paths shown in the output (e.g., `/dev/pts/2`).

**Windows users:** For serial sensors, you need to:

1. **Install com0com first** (for virtual COM ports):
   - Double-click `install_com0com_simple.bat` in the project root
   - The script will request Administrator privileges and install com0com automatically
   - After installation, use `setupc.exe` to create COM port pairs (e.g., COM10 <-> COM11)
2. **Then run the simulator** with `--com-port`:

```bash
python3 ./simulators/sensor_serial.py --config "temperature:1:115200:8N1" --com-port COM10
```

- Use the COM port in `config.json` (e.g., `"port": "COM11"` if simulator uses COM10)

### Step 4: Start Webhook Server (Optional)

If you want to test webhook notifications, start the webhook server in **Terminal 3**:

```bash
python3 ./scripts/test_webhook_server.py
```

This starts a test webhook server on `http://localhost:3000/webhook` (as configured in `config.json`).

### Step 5: Start Main Application

In **Terminal 4** (or your main terminal), start the GUI application:

```bash
python3 main.py
```

### Step 6: Connect to Sensors

1. The GUI application will open
2. Click the **"Connect"** button in the Dashboard tab
3. Real-time sensor data will start appearing
4. Monitor the dashboard for sensor readings, plots, and alarms

### Quick Start Summary

**Easiest Method (Headless Startup):**

1. Install dependencies: `pip3 install -r requirements.txt`
2. **Linux**: Run `./scripts/start_system_linux.sh`
3. **Windows**: Run `scripts\start_system_windows.bat`
4. Click "Connect" button in GUI when it opens or it will auto connect

**Manual Method:**

1. Install dependencies: `pip3 install -r requirements.txt`
2. Configure `config/config.json` to match your simulators
3. Start sensor simulators in separate terminals
4. Start main application: `python3 main.py`
5. Click "Connect" button in GUI

**Note:**

- **Linux**: Use `python3` command
- **Windows**: Use `python` command (or `python3` if available)
- Make sure Python 3.8+ is installed

---

## Project Structure

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
│   │   ├── __init__.py
│   │   ├── splitter.py         # Non-resizable splitter
│   │   └── helpers.py          # Helper classes
│   ├── stylesheet/             # Styling
│   │   └── styles.qss          # Light theme stylesheet
│   └── tabs/                    # Tab components (future modularization)
│       └── __init__.py
│
├── services/                    # Services
│   ├── __init__.py
│   ├── alarm_notifications.py  # Notification system
│   └── remote_console.py         # WebSocket remote console
│
├── simulators/                  # Sensor simulators
│   ├── README.md               # Simulator documentation
│   ├── QUICK_START.md          # Quick start guide
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
│   ├── start_system.py         # Cross-platform system startup script
│   ├── start_system_linux.sh   # Linux system startup script
│   ├── start_system_windows.bat # Windows system startup script
│   └── generate_flowchart.py   # Generate system flowchart
│
├── tests/                       # Unit tests
│   ├── __init__.py
│   ├── README.md               # Test documentation
│   ├── test_sensor_data.py     # Sensor data tests (32 tests)
│   └── test_results.png         # Test execution screenshot
│
├── docs/                        # Documentation
│   ├── Project_Documentation.md # Complete system documentation
│   ├── SYSTEM_FLOWCHART.md      # System flowchart documentation
│   ├── WINDOWS_COMPATIBILITY.md # Windows compatibility guide
│   ├── SYSTEM_ARCHITECTURE.png  # System architecture diagram
│   ├── DATA_FLOW.png            # Data flow diagram
│   ├── STARTUP_SEQUENCE.png     # Startup sequence diagram
│   ├── WEBHOOK_BACKGROUND_THREAD.png # Webhook thread flowchart
│   └── Si-Ware_System_-_PE_Assesment_v3.pdf # Assessment document
│
├── com0com/                     # Windows COM port virtualization
│   ├── com0com-3.0.0.0-i386-and-x64-signed.zip # com0com installer
│   ├── install_com0com_simple.bat # Simple installation script
│   └── install_com0com.ps1     # PowerShell installation script
│
├── README.md                    # This file
├── Project_Documentation.pdf    # PDF version of documentation
└── SYSTEM_ARCHITECTURE.png      # System architecture diagram (root copy)
```

## Detailed Setup

### Prerequisites

- Python 3.8 or higher (use `python3` command)
- **Linux** (Ubuntu recommended): Full support with PTY for serial sensors
- **Windows**: Full support with TCP sockets for serial sensors (automatic fallback)
- Internet connection (for installing packages)

### Step 1: Clone/Download Project

```bash
cd /path/to/RT-ProductionLine-Sensors-Dashboard
```

### Step 2: Install Dependencies

```bash
# Use pip3 to ensure Python 3 packages are installed
pip3 install -r requirements.txt
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

Edit `config/config.json` to configure your sensors. **Important:** The sensor IDs, ports, and protocols must match the simulators you start.

1. **Add Sensor Definitions**: Add sensor entries to the `sensors` array
2. **Set Alarm Limits**: Configure `low_limit` and `high_limit` for each sensor
3. **Configure Protocols**: Set `protocol` and `protocol_config` for each sensor
4. **Set Remote Console Users**: Configure users in `remote_console.users`

See [Configuration](#-configuration) section for detailed examples.

## Running Instructions

For a faster setup, see the [Quick Start](#quick-start) section above.

### Step 1: Start Sensor Simulators

Start sensor simulators based on your configuration. You can run multiple simulators concurrently. **Use `python3` for all commands:**

#### Serial Sensors

**Linux (PTY):**

```bash
# Single sensor
python3 simulators/sensor_serial.py --config "temperature:1:115200:8N1"

# Multiple sensors in one command
python3 simulators/sensor_serial.py \
  --config "temperature:1:115200:8N1" \
  --config "pressure:2:115200:8N1" \
  --config "flow:3:115200:8N1"
```

**Windows (COM Port - Required):**

**Before running serial sensors on Windows, install com0com:**

1. Double-click `install_com0com_simple.bat` in the project root
2. The script will request Administrator privileges and install com0com automatically
3. After installation, use `setupc.exe` to create COM port pairs (e.g., COM10 <-> COM11)

```cmd
# Single sensor with COM port (COM port is REQUIRED)
python simulators\sensor_serial.py --config "temperature:1:115200:8N1" --com-port COM10

# Multiple sensors (each needs its own COM port)
python simulators\sensor_serial.py --config "temperature:1:115200:8N1" --com-port COM10
python simulators\sensor_serial.py --config "pressure:2:115200:8N1" --com-port COM11

# If --com-port is not specified, the simulator will error and require it
```

**Important:**

- **Linux**: Note the PTY path printed when serial simulators start (e.g., `Device: /dev/pts/9`) and update `config/config.json` with the correct paths.
- **Windows (COM Port - Required)**:
  - **Install com0com first**: Use `install_com0com_simple.bat` to install virtual COM port driver
  - COM port is **required** on Windows. Use `--com-port COM10` to specify a COM port
  - Use the paired COM port in `config/config.json` (e.g., if simulator uses COM10, use COM11 in config.json)
  - For real COM ports, use the actual COM port name directly

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

### Step 2: Update Configuration (Manual Startup Only)

**Note:** If using the automated startup script (Option A), `config.json` is updated automatically.

If starting manually, after starting simulators, update `config/config.json`:

1. **Serial Sensors**: Update `protocol_config.port` with the PTY path from simulator output
2. **TCP Sensors**: Verify `protocol_config.host` and `protocol_config.port` match your TCP servers
3. **Modbus Sensors**: Verify `protocol_config.host`, `protocol_config.port`, `protocol_config.unit_id`, and `protocol_config.register`

### Step 3: Start Webhook Server (Optional)

If you want to test webhook notifications:

```bash
python3 ./scripts/test_webhook_server.py
```

This starts a test webhook server on `http://localhost:3000/webhook` (as configured in `config.json`).

### Step 4: Start Main Application

```bash
python3 main.py
```

The GUI application will:

- Load sensor configurations from `config/config.json`
- Start the Remote Console WebSocket server (port 8765)
- Start the HTTP server for web interface (port 8080)
- Display the main window with Dashboard tab

### Step 5: Connect to Sensors

1. Click the **"Connect"** button in the Dashboard tab
2. The system will connect to all configured sensors
3. Real-time data will start appearing in the sensor table and plots
4. Check the global system health indicator for overall status

### Step 6: Access Features

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

## Configuration

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

## Features Overview

### Dashboard

- **Sensor Status Table**: Real-time readings with color-coded status (Green: OK, Yellow: Alarm, Red: Faulty)
- **Real-Time Plots**: Per-sensor plots with 15-second rolling window
- **Global System Health**: Overall status indicator (Normal/Warning/Critical)
- **Alarm Table**: Quick view of last 10 alarms

### Maintenance Console

- **Authentication**: Password-protected access from `config.json`
- **Alarm Log**: Complete history with export to CSV
- **System Tools**: Self-test and system snapshot
- **Live Log Viewer**: Real-time system logs with color-coded levels

### Notifications

- All alarms trigger notifications immediately
- Desktop notifications (Linux/Windows)
- Webhook notifications (HTTP POST)
- Alarm types: LOW, HIGH, FAULT

## Usage Guide

### Daily Operations

1. Start sensor simulators
2. Launch application: `python3 main.py`
3. Click "Connect" button in dashboard
4. Monitor real-time sensor data and plots
5. Check alarms in dashboard or maintenance console

### Remote Access

1. Open web interface: `http://localhost:8080/remote_console_client.html`
2. Login with credentials from `config.json`
3. Access real-time sensor data, alarms, and logs
4. Execute system diagnostics and snapshots

## Protocol Descriptions

### Serial Communication

**Protocol:**

- **Linux**: Serial over Pseudo-Terminal (PTY) - creates `/dev/pts/X` devices
- **Windows**: COM ports (e.g., COM10, COM1) - COM port is required, use `--com-port COM10`
  - **For virtual COM ports**: Install com0com using `install_com0com_simple.bat` (double-click the file in project root)
  - **For real COM ports**: Use actual COM port names (COM1, COM2, etc.)

**Platform Detection:** The simulator automatically detects the platform and uses the appropriate method.

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

| Protocol               | Frame Format        | Termination      | Encoding             | Worker Threads           |
| ---------------------- | ------------------- | ---------------- | -------------------- | ------------------------ |
| **Serial (PTY)** | JSON                | Newline (`\n`) | Text                 | One per unique port      |
| **TCP/IP**       | JSON                | Newline (`\n`) | Text                 | One per unique host:port |
| **Modbus/TCP**   | Binary (MBAP + PDU) | TCP packet       | 16-bit integer × 10 | One per unique host:port |

### Common Features

All protocols support:

- Multiple sensors per communication endpoint
- Real-time data streaming
- Automatic reconnection on failure
- Thread-safe communication
- Configurable alarm limits
- Status indication (OK, LOW_ALARM, HIGH_ALARM, FAULTY)

## API Documentation

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

The complete API documentation is available in this README file and in `docs/Project_Documentation.md`. The API includes:

- WebSocket API for remote console access
- Authentication and command reference
- Request/response examples
- SensorManager API methods
- SensorConfig API methods

## Testing

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

## Architecture

- **Modular Design**: Organized into logical packages
- **OOP**: Object-oriented design throughout
- **Thread-Safe**: Worker threads with queues and signals
- **Separation of Concerns**: GUI, communication, services separated
- **Port-Based Workers**: One worker thread per unique communication endpoint (not per sensor)

### System Diagrams

The following diagrams provide visual representations of the system architecture, data flow, and startup sequence:

#### System Architecture

![System Architecture](docs/SYSTEM_ARCHITECTURE.png)

_Complete system architecture showing all components organized into logical layers: Sensor Simulators, Communication Layer, Management Layer, GUI Application, Remote Console, and Notification System._

#### Data Flow

![Data Flow](docs/DATA_FLOW.png)

_Data flow sequence showing how sensor data moves through the system from simulators to GUI and remote console, with numbered processing steps._

#### Startup Sequence

![Startup Sequence](docs/STARTUP_SEQUENCE.png)

_System startup flowchart showing the phased initialization process from user launch through component setup, server startup, to system running state._

## Security

- **Password Protection**: Maintenance console requires authentication
- **User Permissions**: Role-based access control (read, write, commands)
- **Secure WebSocket**: Authentication required for all remote console commands

## User Interface

- **Light Theme**: Modern, clean interface
- **Resizable Window**: Flexible sizing
- **Custom Icon**: Professional branding
- **Color-Coded Status**: Intuitive visual feedback
- **Scrollable Components**: Support for variable number of sensors

## Recent Updates

- Real-time rolling plots (15-second window)
- Global system health indicator
- Color-coded sensor status
- Maintenance Console with authentication
- Alarm log with low/high limits
- Live log viewer with system events
- Unlimited notifications for all alarms
- Dashboard alarm table
- Application icon and favicon
- Light theme
- Multiple sensor simulator support

## Troubleshooting

### Common Issues

1. **"ModuleNotFoundError"**: Run from project root or set `PYTHONPATH=.`
2. **"Serial port not found"**: Ensure simulators are running and PTY paths in `config.json` are correct
3. **"WebSocket connection failed"**: Check firewall settings and ensure port 8765 is available
4. **"No sensor data"**: Click "Connect" button and verify simulators are running

### Debug

- Check connection status: System Tools → Get Snapshot
- View live logs: Maintenance Console → Live Log Viewer
- Test individual components: Use scripts in `scripts/` directory

## License

This project is part of the Si-Ware Production Line Monitoring System Test.

## Support

For detailed information, refer to:

- `docs/Project_Documentation.md` - Complete system documentation
- `Project_Documentation.pdf` - PDF version
- `docs/SYSTEM_FLOWCHART.md` - System flowchart documentation
- `docs/WINDOWS_COMPATIBILITY.md` - Windows compatibility guide
- `tests/README.md` - Unit tests documentation
- `simulators/README.md` - Sensor simulators documentation
- Source code comments for implementation details
- Demo video LInk : https://drive.google.com/drive/folders/1JtgQllocJPmJjqbKN-MA3C9eeK7TkmEx?usp=sharing

---

## Credits

**Author:** Eng. Mohammed Ismail

_Last Updated: January 2026_

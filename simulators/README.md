# Sensor Simulators

Clean, individual simulator files for each sensor. Each sensor has its own file with its own working frame format.

## Structure

```
simulators/
├── sensor_serial.py        # Unified Serial Sensor Simulator (PTY) - Supports all sensor types
├── start_tcp_system.py      # TCP Sensor System Launcher (unified TCP sensors)
├── run_tcp_sensor_clients.py # TCP Sensor Clients (GenericTCPSensorClient)
├── tcp_sensor_server.py     # Unified TCP Server
└── sensor_modbus.py         # Unified Modbus Sensor Simulator - Supports all sensor types
```

## Quick Start

### Run Individual Sensors

```bash
# Serial sensors (PTY) - Unified simulator for all sensor types
python3 simulators/sensor_serial.py --sensor-id 1 --sensor-type temperature
python3 simulators/sensor_serial.py --sensor-id 2 --sensor-type pressure
python3 simulators/sensor_serial.py --sensor-id 1 --sensor-type temperature --low-limit 20.0 --high-limit 80.0

# TCP Sensors - Use unified system launcher
python3 simulators/start_tcp_system.py --server-ports 5000 --sensor flow:3:localhost:5000 --sensor vibration:4:localhost:5000

# Or start server and clients separately:
python3 simulators/tcp_sensor_server.py --host localhost --port 5000
# Then use run_tcp_sensor_clients.py or start_tcp_system.py for clients

# Modbus sensors - Unified simulator for all sensor types
python3 simulators/sensor_modbus.py --sensor-id 5 --sensor-type voltage
python3 simulators/sensor_modbus.py --sensor-id 6 --sensor-type temperature --host localhost --port 1503 --unit-id 2
```

### Run All Sensors

```bash
./scripts/run_all_sensors.sh
```

Or use individual scripts:
```bash
./scripts/run_sensor_1.sh
./scripts/run_sensor_2.sh
./scripts/run_tcp_server.sh  # Unified server for Sensor 3 & 4
./scripts/run_sensor_5.sh
```

## Sensor Details

### Serial Sensors (Unified: sensor_serial.py)
- **Protocol**: Serial via PTY
- **Default**: 115200 baud, 8N1
- **Frame Format**: JSON
- **PTY Device**: Created automatically (e.g., `/dev/pts/5`)
- **Supported Types**: temperature, pressure, flow, vibration, voltage
- **Configurable**: sensor_id, sensor_type, low_limit, high_limit, unit, baudrate, serial parameters

**Default Values by Type:**
- Temperature: 20.0-80.0°C
- Pressure: 50.0-150.0 PSI
- Flow: 10.0-100.0 L/min
- Vibration: 0.0-5.0 mm/s
- Voltage: 200.0-240.0 V

**Example Usage:**
```bash
# Temperature sensor
python3 simulators/sensor_serial.py --sensor-id 1 --sensor-type temperature

# Pressure sensor with custom limits
python3 simulators/sensor_serial.py --sensor-id 2 --sensor-type pressure --low-limit 40.0 --high-limit 160.0

# Flow sensor
python3 simulators/sensor_serial.py --sensor-id 3 --sensor-type flow
```

### TCP Sensors (Unified: start_tcp_system.py)

**TCP Server** (`tcp_sensor_server.py`):
- **Protocol**: TCP Socket Server
- **Default**: `localhost:5000`
- **Role**: Infrastructure server that accepts connections from sensor clients
- **Function**: Relays data from sensor clients to monitoring clients (main app)

**TCP Sensor System** (`start_tcp_system.py`):
- **Protocol**: TCP Socket Client
- **Unified launcher** for all TCP sensors
- **Supports**: flow, vibration, temperature, pressure, voltage
- **Configurable**: sensor_id, sensor_type, low_limit, high_limit, unit, server host/port

**Default Values by Type:**
- Flow: 10.0-100.0 L/min
- Vibration: 0.0-5.0 mm/s
- Temperature: 20.0-80.0°C
- Pressure: 50.0-150.0 PSI
- Voltage: 200.0-240.0 V

**Example Usage:**
```bash
# Start server and connect multiple sensors
python3 simulators/start_tcp_system.py \\
  --server-ports 5000 \\
  --sensor flow:3:localhost:5000 \\
  --sensor vibration:4:localhost:5000

# With custom limits
python3 simulators/start_tcp_system.py \\
  --server-ports 5000 \\
  --sensor flow:3:localhost:5000:10:100:L/min \\
  --sensor vibration:4:localhost:5000:0:5:mm/s
```

**Architecture**:
1. Start TCP Server (via start_tcp_system.py or separately)
2. Connect sensor clients (via start_tcp_system.py)
3. Main app connects to server and receives data from all sensors

### Modbus Sensors (Unified: sensor_modbus.py)
- **Protocol**: Modbus/TCP
- **Default**: `localhost:1502`, Unit ID: 1, Register: 0
- **Frame Format**: Modbus/TCP (Function Code 3)
- **Data Encoding**: Integer × 10 (e.g., 2205 for 220.5V)
- **Supported Types**: voltage, temperature, pressure, flow, vibration
- **Configurable**: sensor_id, sensor_type, low_limit, high_limit, unit, host, port, unit_id, register

**Default Values by Type:**
- Voltage: 200.0-240.0 V
- Temperature: 20.0-80.0°C
- Pressure: 50.0-150.0 PSI
- Flow: 10.0-100.0 L/min
- Vibration: 0.0-5.0 mm/s

**Example Usage:**
```bash
# Voltage sensor (default)
python3 simulators/sensor_modbus.py --sensor-id 5 --sensor-type voltage

# Temperature sensor with custom limits
python3 simulators/sensor_modbus.py --sensor-id 6 --sensor-type temperature --low-limit 15.0 --high-limit 90.0

# Using simplified config string
python3 simulators/sensor_modbus.py --config "voltage:5:localhost:1502:1:0"
python3 simulators/sensor_modbus.py --config "voltage:5:localhost:1502:1:0:200:240:V"
```

## Configuration

Each sensor simulator prints connection information when started. Update `config/config.json` with:

- **Serial sensors**: PTY device paths (e.g., `/dev/pts/5`)
- **TCP sensors**: Host and port (already configured)
- **Modbus sensor**: Host, port, unit ID, and register (already configured)

## Features

- ✅ **Individual files** - One file per sensor
- ✅ **Working frames** - Each sensor defines its own frame format
- ✅ **Configurable** - Command-line arguments for all parameters
- ✅ **Standalone** - Each sensor runs independently
- ✅ **Clean structure** - No unnecessary files






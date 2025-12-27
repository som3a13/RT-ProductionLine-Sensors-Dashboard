# Sensor Simulators

Clean, individual simulator files for each sensor. Each sensor has its own file with its own working frame format.

## Structure

```
simulators/
├── sensor_1.py          # Temperature Sensor (Serial/PTY)
├── sensor_2.py          # Pressure Sensor (Serial/PTY)
├── sensor_3.py          # Flow Rate Sensor (TCP) - Legacy, use tcp_sensor_server.py
├── sensor_4.py          # Vibration Sensor (TCP) - Legacy, use tcp_sensor_server.py
├── tcp_sensor_server.py # Unified TCP Server (Sensor 3 & 4)
└── sensor_5.py          # Voltage Sensor (Modbus/TCP)
```

## Quick Start

### Run Individual Sensors

```bash
# Serial sensors (PTY)
python3 simulators/sensor_1.py --baudrate 115200 --bytesize 8 --parity N --stopbits 1
python3 simulators/sensor_2.py --baudrate 115200 --bytesize 8 --parity N --stopbits 1

# Step 1: Start TCP Server (required first)
python3 simulators/tcp_sensor_server.py --host localhost --port 5000

# Step 2: Start Sensor Clients (can be started independently)
python3 simulators/sensor_3_client.py --server-host localhost --server-port 5000
python3 simulators/sensor_4_client.py --server-host localhost --server-port 5000

# Modbus sensor
python3 simulators/sensor_5.py --host localhost --port 1502 --unit-id 1 --register 0
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

### Sensor 1: Temperature (Serial/PTY)
- **Protocol**: Serial via PTY
- **Default**: 115200 baud, 8N1
- **Frame Format**: JSON
- **PTY Device**: Created automatically (e.g., `/dev/pts/5`)

### Sensor 2: Pressure (Serial/PTY)
- **Protocol**: Serial via PTY
- **Default**: 115200 baud, 8N1
- **Frame Format**: JSON
- **PTY Device**: Created automatically (e.g., `/dev/pts/6`)

### Modular TCP Architecture (Sensor 3 & 4)

**TCP Server** (`tcp_sensor_server.py`):
- **Protocol**: TCP Socket Server
- **Default**: `localhost:5000`
- **Role**: Infrastructure server that accepts connections from sensor clients
- **Function**: Relays data from sensor clients to monitoring clients (main app)

**Sensor 3 Client** (`sensor_3_client.py`):
- **Protocol**: TCP Socket Client
- **Connects to**: TCP Server on `localhost:5000`
- **Frame Format**: JSON
- **Sensor**: Flow Rate Sensor 1 (L/min)
- **Role**: Independent client that connects to server and sends data

**Sensor 4 Client** (`sensor_4_client.py`):
- **Protocol**: TCP Socket Client
- **Connects to**: TCP Server on `localhost:5000`
- **Frame Format**: JSON
- **Sensor**: Vibration Sensor 1 (mm/s)
- **Role**: Independent client that connects to server and sends data

**Architecture**:
1. Start TCP Server first (infrastructure)
2. Start Sensor 3 Client (connects independently)
3. Start Sensor 4 Client (connects independently)
4. Main app connects to server and receives data from both sensors

### Sensor 5: Voltage (Modbus/TCP)
- **Protocol**: Modbus/TCP
- **Default**: `localhost:1502`, Unit ID: 1, Register: 0
- **Frame Format**: Modbus/TCP (Function Code 3)
- **Data Encoding**: Integer × 10 (e.g., 2205 for 220.5V)

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






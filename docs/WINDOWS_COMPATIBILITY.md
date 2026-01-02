# Windows Compatibility Guide

This project is now fully compatible with both **Linux** and **Windows** operating systems.

## Platform-Specific Features

### Serial Sensor Simulators

#### Linux (PTY Mode)
- Uses pseudo-terminals (PTY) to create virtual serial ports
- Creates `/dev/pts/X` devices automatically
- Full serial parameter support (baudrate, parity, stop bits)

**Example:**
```bash
python3 simulators/sensor_serial.py --config "temperature:1:115200:8N1"
# Output: Device: /dev/pts/9
# Use in config.json: "port": "/dev/pts/9"
```

#### Windows (COM Port Mode - Required)
- Uses real COM ports (e.g., COM10, COM1, COM2)
- **COM port is REQUIRED** - must specify `--com-port COM10`
- Supports virtual COM ports (install com0com for virtual ports)
- Full serial parameter support (baudrate, parity, stop bits)

**Example:**
```cmd
python simulators\sensor_serial.py --config "temperature:1:115200:8N1" --com-port COM10
# Output: Port: COM10
# Use in config.json: "port": "COM10"

# If --com-port is not specified, the simulator will error and require it
```


### Desktop Notifications

#### Linux
- Uses `notify-send` command (if available)
- Falls back to PyQt5 system tray notifications

#### Windows
- Uses `win10toast` library (automatically installed)
- Falls back to PyQt5 system tray notifications

**Note:** `win10toast` is automatically installed on Windows via `requirements.txt`.

### File Paths

All file paths in the codebase use `os.path.join()` for cross-platform compatibility. Both forward slashes (Linux) and backslashes (Windows) are handled correctly.

### TCP and Modbus Communication

TCP and Modbus communication work identically on both platforms - no platform-specific changes needed.

## Installation on Windows

1. **Install Python 3.8+**
   - Download from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation

2. **Install Dependencies**
   ```cmd
   pip install -r requirements.txt
   ```
   This will automatically install `win10toast` on Windows.

3. **Run the Application**
   ```cmd
   python main.py
   ```

## Configuration Differences

### Serial Sensors Configuration

**Linux (`config.json`):**
```json
{
  "protocol": "serial",
  "communication": {
    "port": "/dev/pts/9",
    "baudrate": 115200
  }
}
```

**Windows (`config.json`):**
```json
{
  "protocol": "serial",
  "communication": {
    "port": "COM10",
    "baudrate": 115200
  }
}
```

### Real Serial Ports

If you're using **real serial ports** (not simulators):

**Linux:**
- Use device paths like `/dev/ttyUSB0`, `/dev/ttyACM0`, etc.

**Windows:**
- Use COM port names like `COM1`, `COM2`, `COM3`, `COM10`, etc.
- Specify the COM port with `--com-port COM10` when running the simulator
- The `sensor_serial_comm.py` automatically detects the format and uses the appropriate connection method

### Virtual COM Ports on Windows

To create virtual COM port pairs on Windows (similar to PTY on Linux):

1. **Install com0com** (free virtual serial port driver):
   - Download from: https://sourceforge.net/projects/com0com/
   - Install the driver
   - Use the `setupc.exe` tool to create COM port pairs (e.g., COM10 <-> COM11)

2. **Use the virtual COM ports:**
   ```cmd
   # Simulator uses COM10
   python simulators\sensor_serial.py --config "temperature:1:115200:8N1" --com-port COM10
   
   # Application connects to COM11 (the paired port)
   # In config.json: "port": "COM11"
   ```

3. **Alternative: Use real COM ports** if you have physical serial ports available.

## Testing on Windows

1. **Start a Serial Sensor Simulator:**
   ```cmd
   python simulators\sensor_serial.py --config "temperature:1:115200:8N1" --com-port COM10
   ```
   Note the COM port printed (e.g., `COM10`).

2. **Update `config/config.json`:**
   ```json
   {
     "sensors": [
       {
         "sensor_id": 1,
         "name": "Temperature Sensor",
         "protocol": "serial",
         "communication": {
           "port": "COM10",
           "baudrate": 115200
         }
       }
     ]
   }
   ```

3. **Run the Main Application:**
   ```cmd
   python main.py
   ```

## Known Limitations

1. **PTY on Windows**: Windows doesn't support PTY (pseudo-terminals), so COM ports must be used. Install com0com for virtual COM port pairs.

2. **COM Port Required**: On Windows, the `--com-port` argument is required when running the serial sensor simulator. Use real COM ports (COM1, COM10, etc.) or virtual COM ports created with com0com.

3. **Real Serial Ports**: Real serial ports work the same on both platforms - just use the appropriate port name (`COM1` on Windows, `/dev/ttyUSB0` on Linux).

## Troubleshooting

### Windows: "ModuleNotFoundError: No module named 'win10toast'"
**Solution:** Install dependencies:
```cmd
pip install -r requirements.txt
```

### Windows: Serial port not found
**Solution:** 
- Make sure you specify `--com-port COM10` when running the simulator
- For real ports: Use COM port names like `COM1`, `COM2`, `COM10`, etc.
- For virtual ports: Install com0com and create COM port pairs

## Summary

✅ **Fully Compatible**: The project works on both Linux and Windows  
✅ **Automatic Detection**: Platform-specific features are automatically detected  
✅ **Same API**: All protocols (Serial, TCP, Modbus) work identically on both platforms  
✅ **Easy Configuration**: Just use the appropriate port format for your platform


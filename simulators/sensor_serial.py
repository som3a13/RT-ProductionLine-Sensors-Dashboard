"""
Unified Serial Sensor Simulator (PTY-based on Linux, COM port on Windows)
Supports multiple sensor types: temperature, pressure, flow, vibration, voltage
- Linux: Uses PTY (pseudo-terminal) to create a fake serial port
- Windows: Uses COM ports or TCP socket for simulation
Configurable baudrate and serial parameters (8N1)

Author: Mohammed Ismail AbdElmageid
"""
import os
import sys
import time
import json
import random
import re
import threading
import platform
from datetime import datetime

# Platform-specific imports
IS_WINDOWS = platform.system() == "Windows"
if not IS_WINDOWS:
    import pty
    import termios
else:
    # Windows: Use COM port
    import serial


class TrendBasedGenerator:
    """Trend-based sensor value generator for realistic gradual changes"""
    
    def __init__(self, low_limit: float, high_limit: float, base_value: float = None):
        self.low_limit = low_limit
        self.high_limit = high_limit
        self.base_value = base_value if base_value is not None else (low_limit + high_limit) / 2
        self.current_value = self.base_value
        self.trend_direction = random.choice([-1, 1])
        self.trend_rate = random.uniform(0.01, 0.05)
        self.trend_change_probability = 0.02
        self.range = high_limit - low_limit
        self.step_size = self.range * self.trend_rate
        self.noise_level = self.range * 0.01
        self.faulty = False
        self.alarm_cooldown = 0
    
    def generate_value(self) -> float:
        """Generate next trend-based sensor value"""
        if self.faulty:
            if random.random() < 0.1:
                self.faulty = False
                self.current_value = self.base_value
            else:
                return -999.0
        
        if random.random() < 0.01:
            self.faulty = True
            return -999.0
        
        if self.alarm_cooldown > 0:
            self.alarm_cooldown -= 1
        
        if self.alarm_cooldown == 0 and random.random() < 0.05:
            self.alarm_cooldown = 20
            if random.random() < 0.5:
                self.current_value = self.low_limit - random.uniform(1, min(10, self.range * 0.1))
                return round(self.current_value, 2)
            else:
                self.current_value = self.high_limit + random.uniform(1, min(10, self.range * 0.1))
                return round(self.current_value, 2)
        
        if random.random() < self.trend_change_probability:
            self.trend_direction *= -1
            self.trend_rate = random.uniform(0.01, 0.05)
            self.step_size = self.range * self.trend_rate
        
        self.current_value += self.trend_direction * self.step_size
        noise = random.uniform(-self.noise_level, self.noise_level)
        self.current_value += noise
        
        if self.current_value < self.low_limit - self.range * 0.2:
            self.current_value = self.low_limit - self.range * 0.1
            self.trend_direction = 1
        elif self.current_value > self.high_limit + self.range * 0.2:
            self.current_value = self.high_limit + self.range * 0.1
            self.trend_direction = -1
        
        return round(self.current_value, 2)


def get_defaults_for_type(sensor_type: str):
    """Get default values for sensor type"""
    defaults = {
        'flow': {'low': 10.0, 'high': 100.0, 'unit': 'L/min', 'name': 'Flow Rate'},
        'vibration': {'low': 0.0, 'high': 5.0, 'unit': 'mm/s', 'name': 'Vibration'},
        'temperature': {'low': 20.0, 'high': 80.0, 'unit': '°C', 'name': 'Temperature'},
        'pressure': {'low': 50.0, 'high': 150.0, 'unit': 'PSI', 'name': 'Pressure'},
        'voltage': {'low': 200.0, 'high': 240.0, 'unit': 'V', 'name': 'Voltage'},
        'speed': {'low': 0.0, 'high': 600.0, 'unit': 'RPM', 'name': 'Speed'},
        'optical': {'low': 50.0, 'high': 60.0, 'unit': '%', 'name': 'Optical'},
    }
    
    sensor_type_lower = sensor_type.lower()
    for key, value in defaults.items():
        if key in sensor_type_lower or sensor_type_lower in key:
            return value
    
    # Default to temperature if type not found
    return defaults['temperature']


class SerialSensorSimulator:
    """
    Cross-platform simulator for serial sensors (Temperature, Pressure, etc.)
    - Linux: Uses PTY (pseudo-terminal)
    - Windows: Uses TCP socket or COM port
    """
    
    def __init__(self, sensor_id=1, sensor_type='temperature', 
                 low_limit=None, high_limit=None, unit=None,
                 baudrate=115200, bytesize=8, parity='N', stopbits=1,
                 com_port=None):
        """
        Initialize sensor simulator
        
        Args:
            sensor_id: Sensor ID (default: 1)
            sensor_type: Sensor type - 'temperature', 'pressure', 'flow', 'vibration', 'voltage' (default: 'temperature')
            low_limit: Low alarm limit (default: based on sensor_type)
            high_limit: High alarm limit (default: based on sensor_type)
            unit: Unit of measurement (default: based on sensor_type)
            baudrate: Serial baudrate (default: 115200)
            bytesize: Data bits (default: 8)
            parity: Parity ('N' for None, 'E' for Even, 'O' for Odd)
            stopbits: Stop bits (1 or 2)
            com_port: COM port name for Windows (e.g., 'COM10', 'COM1'). If None, uses TCP fallback.
        """
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.running = False
        self.master_fd = None
        self.slave_name = None
        self.com_port = com_port  # For Windows COM port mode
        self.serial_conn = None  # For Windows COM port mode
        
        # Get defaults for sensor type
        defaults = get_defaults_for_type(sensor_type)
        
        # Sensor configuration
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type.lower()
        self.sensor_name = f"{defaults['name']} Sensor {sensor_id}"
        self.low_limit = low_limit if low_limit is not None else defaults['low']
        self.high_limit = high_limit if high_limit is not None else defaults['high']
        self.unit = unit if unit is not None else defaults['unit']
        self.base_value = (self.low_limit + self.high_limit) / 2
        self.faulty = False
        
        # Trend-based value generator
        self.value_generator = TrendBasedGenerator(
            low_limit=self.low_limit,
            high_limit=self.high_limit,
            base_value=self.base_value
        )
        
        # Working frame configuration for this sensor
        self.frame_format = "JSON"  # This sensor uses JSON frame format
        
    def create_pty(self):
        """
        Create serial port interface (PTY on Linux, COM port on Windows)
        Returns the port/address that the application should connect to
        """
        if IS_WINDOWS:
            # Windows: COM port is required
            if not self.com_port:
                print("Error: COM port is required on Windows. Please specify --com-port COM10 (or COM1, COM2, etc.)")
                print("For virtual COM ports, install com0com to create COM port pairs.")
                return None
            return self._create_windows_com_port()
        else:
            # Linux: Use PTY (pseudo-terminal)
            return self._create_linux_pty()
    
    def _create_linux_pty(self):
        """Create PTY pair on Linux and configure serial parameters"""
        try:
            # Create PTY pair
            master_fd, slave_fd = pty.openpty()
            self.slave_name = os.ttyname(slave_fd)
            
            # Configure PTY with serial parameters
            try:
                # Get current terminal attributes
                attrs = termios.tcgetattr(master_fd)
                
                # Set baudrate
                if self.baudrate == 115200:
                    attrs[4] = termios.B115200
                    attrs[5] = termios.B115200
                elif self.baudrate == 9600:
                    attrs[4] = termios.B9600
                    attrs[5] = termios.B9600
                elif self.baudrate == 19200:
                    attrs[4] = termios.B19200
                    attrs[5] = termios.B19200
                elif self.baudrate == 38400:
                    attrs[4] = termios.B38400
                    attrs[5] = termios.B38400
                elif self.baudrate == 57600:
                    attrs[4] = termios.B57600
                    attrs[5] = termios.B57600
                else:
                    attrs[4] = termios.B115200
                    attrs[5] = termios.B115200
                
                # Set data bits, parity, stop bits
                attrs[2] &= ~termios.CSIZE
                if self.bytesize == 8:
                    attrs[2] |= termios.CS8
                elif self.bytesize == 7:
                    attrs[2] |= termios.CS7
                elif self.bytesize == 6:
                    attrs[2] |= termios.CS6
                elif self.bytesize == 5:
                    attrs[2] |= termios.CS5
                
                # Set parity
                attrs[2] &= ~(termios.PARENB | termios.PARODD)
                if self.parity == 'E':
                    attrs[2] |= termios.PARENB
                elif self.parity == 'O':
                    attrs[2] |= termios.PARENB | termios.PARODD
                
                # Set stop bits
                if self.stopbits == 2:
                    attrs[2] |= termios.CSTOPB
                else:
                    attrs[2] &= ~termios.CSTOPB
                
                # Apply attributes
                termios.tcsetattr(master_fd, termios.TCSANOW, attrs)
            except Exception as e:
                print(f"Warning: Could not set serial parameters: {e}")
            
            self.master_fd = master_fd
            os.close(slave_fd)
            
            print(f"✓ Created PTY for {self.sensor_name}")
            print(f"  Device: {self.slave_name}")
            print(f"  Sensor ID: {self.sensor_id}")
            print(f"  Sensor Type: {self.sensor_type}")
            print(f"  Limits: {self.low_limit} - {self.high_limit} {self.unit}")
            print(f"  Baudrate: {self.baudrate}")
            print(f"  Serial Parameters: {self.bytesize}{self.parity}{self.stopbits}")
            print(f"  Frame Format: {self.frame_format}")
            
            return self.slave_name
        except Exception as e:
            print(f"Failed to create PTY: {e}")
            return None
    
    def _create_windows_com_port(self):
        """Create/use COM port on Windows"""
        try:
            import serial
            
            # Normalize COM port name (COM10, COM1, etc.)
            com_name = self.com_port.upper()
            if not com_name.startswith('COM'):
                com_name = f'COM{com_name}'
            
            # Try to open the COM port
            try:
                self.serial_conn = serial.Serial(
                    port=com_name,
                    baudrate=self.baudrate,
                    bytesize=self.bytesize,
                    parity=self.parity,
                    stopbits=self.stopbits,
                    timeout=1.0,
                    write_timeout=1.0
                )
                
                self.slave_name = com_name
                
                print(f"✓ Using COM port for {self.sensor_name}")
                print(f"  Port: {com_name}")
                print(f"  Sensor ID: {self.sensor_id}")
                print(f"  Sensor Type: {self.sensor_type}")
                print(f"  Limits: {self.low_limit} - {self.high_limit} {self.unit}")
                print(f"  Baudrate: {self.baudrate}")
                print(f"  Serial Parameters: {self.bytesize}{self.parity}{self.stopbits}")
                print(f"  Frame Format: {self.frame_format}")
                print(f"  Note: Use '{com_name}' as the port in config.json")
                
                return self.slave_name
            except serial.SerialException as e:
                print(f"Error: Could not open COM port {com_name}: {e}")
                print(f"  Make sure the COM port exists and is not in use by another application.")
                print(f"  For virtual COM ports, install 'com0com' or similar virtual serial port driver.")
                return None
        except ImportError:
            print("Error: pyserial not installed. Install with: pip install pyserial")
            return None
        except Exception as e:
            print(f"Failed to create COM port: {e}")
            return None
    
    
    def generate_sensor_value(self) -> float:
        """Generate a realistic trend-based sensor value"""
        value = self.value_generator.generate_value()
        self.faulty = self.value_generator.faulty
        return value
    
    def create_working_frame(self, value: float) -> bytes:
        """
        Create working frame for serial sensor
        This sensor uses JSON frame format
        """
        is_faulty = self.faulty or value == -999.0
        
        frame_data = {
            "sensor_id": self.sensor_id,
            "sensor_name": self.sensor_name,
            "sensor_type": self.sensor_type,
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "status": "FAULTY" if is_faulty else "OK",
            "unit": self.unit
        }
        
        # JSON frame format: JSON message + newline
        frame = json.dumps(frame_data) + "\n"
        return frame.encode('utf-8')
    
    def run(self):
        """Main loop - sends sensor data (platform-specific)"""
        if IS_WINDOWS:
            if self.com_port and self.serial_conn:
                self._run_windows_com()
            else:
                print("Error: COM port not created. Call create_pty() first.")
                return
        else:
            if not self.master_fd:
                print("Error: PTY not created. Call create_pty() first.")
                return
            self._run_linux_pty()
    
    def _run_linux_pty(self):
        """Run on Linux using PTY"""
        self.running = True
        print(f"\n{self.sensor_name} simulator running...")
        print("Press Ctrl+C to stop.\n")
        
        try:
            while self.running:
                value = self.generate_sensor_value()
                frame = self.create_working_frame(value)
                
                # Write frame to PTY master side
                os.write(self.master_fd, frame)
                
                time.sleep(0.5)  # Update every 0.5 seconds
        except KeyboardInterrupt:
            print("\n\nStopping simulator...")
            self.stop()
        except Exception as e:
            print(f"Error: {e}")
            self.stop()
    
    def _run_windows_com(self):
        """Run on Windows using COM port"""
        import serial
        self.running = True
        print(f"\n{self.sensor_name} simulator running on {self.com_port}...")
        print("Press Ctrl+C to stop.\n")
        
        try:
            while self.running:
                if self.serial_conn and self.serial_conn.is_open:
                    value = self.generate_sensor_value()
                    frame = self.create_working_frame(value)
                    
                    try:
                        self.serial_conn.write(frame)
                    except serial.SerialTimeoutException:
                        # Serial write timeout - silently continue
                        pass
                    except serial.SerialException as e:
                        print(f"Serial error: {e}")
                        break
                else:
                    print("Error: COM port is not open")
                    break
                
                time.sleep(0.5)  # Update every 0.5 seconds
        except KeyboardInterrupt:
            print("\n\nStopping simulator...")
            self.stop()
        except Exception as e:
            print(f"Error: {e}")
            self.stop()
    
    
    def stop(self):
        """Stop the simulator"""
        self.running = False
        if not IS_WINDOWS and self.master_fd:
            try:
                os.close(self.master_fd)
            except:
                pass
        if IS_WINDOWS:
            if self.serial_conn and self.serial_conn.is_open:
                try:
                    self.serial_conn.close()
                except:
                    pass
        print(f"{self.sensor_name} simulator stopped.")


def parse_config_string(config_str: str):
    """
    Parse simplified configuration string format:
    type:id:baudrate:bytesizeparitystopbits[:low[:high[:unit]]]
    
    Examples:
      flow:3:115200:8N1                    # Uses defaults for limits and unit
      flow:3:115200:8N1:10:100             # Custom limits, default unit
      flow:3:115200:8N1:10:100:L/min        # All parameters specified
    
    Minimum required: type:id:baudrate:bytesizeparitystopbits
    """
    parts = config_str.split(':')
    if len(parts) < 4:
        raise ValueError(f"Invalid config format. Minimum required: type:id:baudrate:bytesizeparitystopbits\n"
                        f"Got {len(parts)} parts, expected at least 4\n"
                        f"Examples:\n"
                        f"  flow:3:115200:8N1\n"
                        f"  flow:3:115200:8N1:10:100\n"
                        f"  flow:3:115200:8N1:10:100:L/min")
    
    sensor_type = parts[0].strip()
    sensor_id = int(parts[1].strip())
    baudrate = int(parts[2].strip()) if parts[2].strip() else 115200
    
    # Parse serial parameters: bytesizeparitystopbits (e.g., 8N1)
    serial_params = parts[3].strip()
    # Extract bytesize (first digit)
    bytesize = int(serial_params[0]) if len(serial_params) > 0 and serial_params[0].isdigit() else 8
    
    # Extract parity (second character: N, E, or O)
    parity = serial_params[1] if len(serial_params) > 1 and serial_params[1] in 'NEO' else 'N'
    
    # Extract stopbits (last digit)
    stopbits = int(serial_params[2]) if len(serial_params) > 2 and serial_params[2].isdigit() else 1
    
    # Optional parameters (limits and unit)
    low_limit = float(parts[4].strip()) if len(parts) > 4 and parts[4].strip() else None
    high_limit = float(parts[5].strip()) if len(parts) > 5 and parts[5].strip() else None
    unit = parts[6].strip() if len(parts) > 6 and parts[6].strip() else None
    
    return {
        'sensor_type': sensor_type,
        'sensor_id': sensor_id,
        'baudrate': baudrate,
        'bytesize': bytesize,
        'parity': parity,
        'stopbits': stopbits,
        'low_limit': low_limit,
        'high_limit': high_limit,
        'unit': unit
    }


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Unified Serial Sensor Simulator (PTY on Linux, COM port on Windows)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Linux: Using simplified config string (limits and unit are optional):
  python3 sensor_serial.py --config "flow:3:115200:8N1"
  python3 sensor_serial.py --config "flow:3:115200:8N1:10:100"
  python3 sensor_serial.py --config "flow:3:115200:8N1:10:100:L/min"
  python3 sensor_serial.py --config "temperature:1:9600:8E1"
  
  # Linux: Running multiple sensors at once:
  python3 sensor_serial.py --config "flow:1:115200:8N1" --config "pressure:2:115200:8N1"
  python3 sensor_serial.py --config "temperature:1:115200:8N1" --config "flow:3:9600:8N1" --config "pressure:4:19200:8N1"
  
  # Linux: Using individual arguments (single sensor only):
  python3 sensor_serial.py --sensor-id 1 --sensor-type temperature
  python3 sensor_serial.py --sensor-id 2 --sensor-type pressure --low-limit 40.0 --high-limit 160.0
  
  # Windows: COM port is REQUIRED (e.g., COM10, COM1):
  python sensor_serial.py --config "temperature:1:115200:8N1" --com-port COM10
  python sensor_serial.py --sensor-id 1 --sensor-type temperature --com-port COM1
  
  # Windows: Multiple sensors with different COM ports:
  python sensor_serial.py --config "temperature:1:115200:8N1" --com-port COM20 --config "pressure:2:115200:8N1" --com-port COM22
  
  # Windows: For virtual COM ports, install com0com to create COM port pairs
        """
    )
    
    parser.add_argument('--config', type=str, default=None, action='append',
                        help='Simplified config string: type:id:baudrate:bytesizeparitystopbits[:low[:high[:unit]]]\n'
                             'Can be specified multiple times to run multiple sensors.\n'
                             'Examples:\n'
                             '  --config "flow:3:115200:8N1" --config "pressure:2:115200:8N1"\n'
                             '  flow:3:115200:8N1                    (uses defaults)\n'
                             '  flow:3:115200:8N1:10:100             (custom limits)\n'
                             '  flow:3:115200:8N1:10:100:L/min       (all parameters)')
    parser.add_argument('--sensor-id', type=int, default=1, help='Sensor ID (default: 1)')
    parser.add_argument('--sensor-type', type=str, default='temperature',
                        choices=['temperature', 'pressure', 'flow', 'vibration', 'voltage'],
                        help='Sensor type (default: temperature)')
    parser.add_argument('--low-limit', type=float, default=None,
                        help='Low alarm limit (default: based on sensor type)')
    parser.add_argument('--high-limit', type=float, default=None,
                        help='High alarm limit (default: based on sensor type)')
    parser.add_argument('--unit', type=str, default=None,
                        help='Unit of measurement (default: based on sensor type)')
    parser.add_argument('--baudrate', type=int, default=115200, help='Baudrate (default: 115200)')
    parser.add_argument('--bytesize', type=int, default=8, choices=[5, 6, 7, 8], help='Data bits (default: 8)')
    parser.add_argument('--parity', type=str, default='N', choices=['N', 'E', 'O'], help='Parity (default: N)')
    parser.add_argument('--stopbits', type=int, default=1, choices=[1, 2], help='Stop bits (default: 1)')
    parser.add_argument('--com-port', type=str, default=None, action='append',
                        help='COM port name for Windows (REQUIRED on Windows, e.g., COM10, COM1).\n'
                             'Can be specified multiple times to assign different ports to each config.\n'
                             'For virtual COM ports, install com0com or similar virtual serial port driver.\n'
                             'Example: --config "temp:1:115200:8N1" --com-port COM20 --config "press:2:115200:8N1" --com-port COM22')
    
    args = parser.parse_args()
    
    simulators = []
    
    # If config strings are provided, create simulators for each
    if args.config:
        print(f"Creating {len(args.config)} sensor simulator(s)...\n")
        
        # Handle COM ports: if multiple provided, match by index; if single, use for all
        com_ports = args.com_port if args.com_port else []
        if len(com_ports) == 1 and len(args.config) > 1:
            # Single COM port for all configs
            com_ports = com_ports * len(args.config)
        elif len(com_ports) > 1 and len(com_ports) != len(args.config):
            print(f"Warning: Number of COM ports ({len(com_ports)}) doesn't match number of configs ({len(args.config)})")
            print(f"Using first COM port for all simulators: {com_ports[0]}")
            com_ports = [com_ports[0]] * len(args.config)
        elif len(com_ports) == 0 and IS_WINDOWS:
            print("Error: COM port is required on Windows. Please specify --com-port for each config.")
            sys.exit(1)
        
        for idx, config_str in enumerate(args.config):
            try:
                config = parse_config_string(config_str)
                # Get the corresponding COM port for this config
                com_port = com_ports[idx] if idx < len(com_ports) else (com_ports[0] if com_ports else None)
                simulator = SerialSensorSimulator(
                    sensor_id=config['sensor_id'],
                    sensor_type=config['sensor_type'],
                    low_limit=config['low_limit'],
                    high_limit=config['high_limit'],
                    unit=config['unit'],
                    baudrate=config['baudrate'],
                    bytesize=config['bytesize'],
                    parity=config['parity'],
                    stopbits=config['stopbits'],
                    com_port=com_port
                )
                simulators.append(simulator)
            except ValueError as e:
                print(f"Error parsing config string '{config_str}': {e}")
                sys.exit(1)
    else:
        # Use individual arguments (single simulator)
        # Handle COM port: if list, use first; otherwise use as-is
        com_port = args.com_port[0] if isinstance(args.com_port, list) and args.com_port else args.com_port
        simulator = SerialSensorSimulator(
            sensor_id=args.sensor_id,
            sensor_type=args.sensor_type,
            low_limit=args.low_limit,
            high_limit=args.high_limit,
            unit=args.unit,
            baudrate=args.baudrate,
            bytesize=args.bytesize,
            parity=args.parity,
            stopbits=args.stopbits,
            com_port=com_port
        )
        simulators.append(simulator)
    
    # Create PTYs for all simulators
    slave_names = []
    for simulator in simulators:
        slave_name = simulator.create_pty()
        if slave_name:
            slave_names.append(slave_name)
            print(f"  Serial parameters: {simulator.bytesize}{simulator.parity}{simulator.stopbits} @ {simulator.baudrate} baud")
        else:
            print(f"Failed to create PTY for {simulator.sensor_name}")
            sys.exit(1)
    
    if slave_names:
        print(f"\n{'='*60}")
        print("Sensor simulators ready. Worker threads should connect to:")
        for i, slave_name in enumerate(slave_names, 1):
            # On Windows with com0com, worker should use the paired port (COM20 -> COM21, COM22 -> COM23, etc.)
            if IS_WINDOWS and slave_name and slave_name.upper().startswith("COM"):
                # Extract port number and add 1 for the paired port
                match = re.match(r'COM(\d+)', slave_name.upper())
                if match:
                    port_num = int(match.group(1))
                    worker_port = f"COM{port_num + 1}"
                    print(f"  {i}. {worker_port} (simulator is using {slave_name})")
                else:
                    worker_port = slave_name
                    print(f"  {i}. {worker_port}")
            else:
                worker_port = slave_name
                print(f"  {i}. {worker_port}")
        print(f"{'='*60}\n")
        print("All simulators running... Press Ctrl+C to stop all.\n")
    
    # Run all simulators in separate threads
    threads = []
    for simulator in simulators:
        thread = threading.Thread(target=simulator.run, daemon=True)
        thread.start()
        threads.append(thread)
    
    # Wait for all threads (or until Ctrl+C)
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\n\nStopping all simulators...")
        for simulator in simulators:
            simulator.stop()
        print("All simulators stopped.")


if __name__ == "__main__":
    main()


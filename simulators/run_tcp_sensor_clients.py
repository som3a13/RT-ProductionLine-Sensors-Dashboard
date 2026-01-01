#!/usr/bin/env python3
"""
Run Multiple TCP Sensor Clients
Connects multiple sensors to different TCP servers with command-line arguments

Author: Mohammed Ismail AbdElmageid
"""
import sys
import argparse
import threading
import signal
import time
from pathlib import Path

# Import sensor client classes (not needed for GenericTCPSensorClient, but kept for reference)
sys.path.insert(0, str(Path(__file__).parent))


class GenericTCPSensorClient:
    """Generic TCP sensor client that can be configured for any sensor"""
    
    def __init__(self, sensor_id: int, sensor_name: str, sensor_type: str,
                 low_limit: float, high_limit: float, unit: str,
                 server_host: str = "localhost", server_port: int = 5000):
        """Initialize generic sensor client"""
        import socket
        import threading
        import time
        import json
        import random
        from datetime import datetime
        
        self.sensor_id = sensor_id
        self.sensor_name = sensor_name
        self.sensor_type = sensor_type
        self.server_host = server_host
        self.server_port = server_port
        self.low_limit = low_limit
        self.high_limit = high_limit
        self.unit = unit
        self.running = False
        self.socket = None
        self.send_thread = None
        
        # Trend-based generator for realistic sensor value simulation
        class TrendBasedGenerator:
            def __init__(self, low_limit, high_limit, base_value=None):
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
            
            def generate_value(self):
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
        
        self.value_generator = TrendBasedGenerator(low_limit, high_limit)
        self.faulty = False
    
    def generate_sensor_value(self):
        """Generate a realistic trend-based sensor value"""
        value = self.value_generator.generate_value()
        self.faulty = self.value_generator.faulty
        return value
    
    def create_working_frame(self, value):
        """Create JSON frame for sensor data"""
        import json
        from datetime import datetime
        
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
        
        frame = json.dumps(frame_data) + "\n"
        return frame.encode('utf-8')
    
    def connect_to_server(self):
        """Connect to TCP server"""
        import socket
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.server_host, self.server_port))
            print(f"✓ {self.sensor_name} connected to {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"✗ {self.sensor_name} connection error: {e}")
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            return False
    
    def send_data_loop(self):
        """Main loop to send sensor data to server"""
        import time
        while self.running:
            try:
                if not self.socket:
                    if not self.connect_to_server():
                        time.sleep(2)
                        continue
                
                value = self.generate_sensor_value()
                frame = self.create_working_frame(value)
                
                try:
                    self.socket.send(frame)
                except Exception as e:
                    print(f"Error sending data from {self.sensor_name}: {e}")
                    if self.socket:
                        try:
                            self.socket.close()
                        except:
                            pass
                        self.socket = None
                    continue
                
                time.sleep(0.5)  # Update every 0.5 seconds
                
            except Exception as e:
                if self.running:
                    print(f"Error in send loop for {self.sensor_name}: {e}")
                break
    
    def start(self):
        """Start the sensor client"""
        self.running = True
        
        if not self.connect_to_server():
            print(f"Failed to connect {self.sensor_name}. Make sure TCP server is running on {self.server_host}:{self.server_port}")
            return False
        
        self.send_thread = threading.Thread(target=self.send_data_loop, daemon=True)
        self.send_thread.start()
        return True
    
    def stop(self):
        """Stop the sensor client"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        print(f"{self.sensor_name} stopped.")


def parse_sensor_spec(spec: str):
    """
    Parse sensor specification string
    Format: TYPE:ID:HOST:PORT:LOW:HIGH:UNIT
    Example: flow:3:localhost:5000:10:100:L/min
    """
    parts = spec.split(':')
    if len(parts) < 4:
        raise ValueError(f"Invalid sensor spec: {spec}. Need at least TYPE:ID:HOST:PORT")
    
    sensor_type = parts[0]
    sensor_id = int(parts[1])
    host = parts[2]
    port = int(parts[3])
    
    # Optional parameters
    low_limit = float(parts[4]) if len(parts) > 4 else None
    high_limit = float(parts[5]) if len(parts) > 5 else None
    unit = parts[6] if len(parts) > 6 else None
    
    return {
        'type': sensor_type,
        'id': sensor_id,
        'host': host,
        'port': port,
        'low_limit': low_limit,
        'high_limit': high_limit,
        'unit': unit
    }


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
    
    # Default fallback
    return {'low': 0.0, 'high': 100.0, 'unit': '', 'name': 'Sensor'}


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Run Multiple TCP Sensor Clients - Connect sensors to TCP servers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Connect single sensor
  python3 simulators/run_tcp_sensor_clients.py --sensor flow:3:localhost:5000
  
  # Connect multiple sensors to same server
  python3 simulators/run_tcp_sensor_clients.py \\
    --sensor flow:3:localhost:5000 \\
    --sensor vibration:4:localhost:5000
  
  # Connect sensors to different servers
  python3 simulators/run_tcp_sensor_clients.py \\
    --sensor flow:3:localhost:5000:10:100:L/min \\
    --sensor flow:6:localhost:5001:10:100:L/min
  
  # Connect with custom limits
  python3 simulators/run_tcp_sensor_clients.py \\
    --sensor temperature:1:localhost:5000:15:75:°C \\
    --sensor pressure:2:localhost:5001:40:160:PSI

Sensor Specification Format:
  TYPE:ID:HOST:PORT[:LOW:HIGH:UNIT]
  
  TYPE:    Sensor type (flow, vibration, temperature, pressure, voltage)
  ID:      Unique sensor ID (integer)
  HOST:    TCP server host
  PORT:    TCP server port
  LOW:     Lower alarm limit (optional, uses defaults if not specified)
  HIGH:    Upper alarm limit (optional, uses defaults if not specified)
  UNIT:    Unit of measurement (optional, uses defaults if not specified)
        """
    )
    
    parser.add_argument('--sensor', action='append', metavar='SPEC',
                       help='Sensor specification: TYPE:ID:HOST:PORT[:LOW:HIGH:UNIT]')
    parser.add_argument('--name-prefix', default='',
                       help='Prefix for sensor names (e.g., "Production Line 1 - ")')
    
    args = parser.parse_args()
    
    if not args.sensor:
        parser.print_help()
        print("\nError: At least one --sensor argument is required.")
        sys.exit(1)
    
    # Parse all sensor specifications
    sensors = []
    for spec in args.sensor:
        try:
            sensor_config = parse_sensor_spec(spec)
            defaults = get_defaults_for_type(sensor_config['type'])
            
            # Use provided values or defaults
            low_limit = sensor_config['low_limit'] if sensor_config['low_limit'] is not None else defaults['low']
            high_limit = sensor_config['high_limit'] if sensor_config['high_limit'] is not None else defaults['high']
            unit = sensor_config['unit'] if sensor_config['unit'] else defaults['unit']
            sensor_name = f"{args.name_prefix}{defaults['name']} Sensor {sensor_config['id']}"
            
            client = GenericTCPSensorClient(
                sensor_id=sensor_config['id'],
                sensor_name=sensor_name,
                sensor_type=sensor_config['type'],
                low_limit=low_limit,
                high_limit=high_limit,
                unit=unit,
                server_host=sensor_config['host'],
                server_port=sensor_config['port']
            )
            sensors.append(client)
        except Exception as e:
            print(f"Error parsing sensor spec '{spec}': {e}")
            sys.exit(1)
    
    # Display configuration
    print("=" * 70)
    print("TCP Sensor Clients Launcher")
    print("=" * 70)
    print(f"Number of sensors: {len(sensors)}")
    print("\nSensors:")
    for sensor in sensors:
        print(f"  - ID {sensor.sensor_id}: {sensor.sensor_name} ({sensor.sensor_type})")
        print(f"    Server: {sensor.server_host}:{sensor.server_port}")
        print(f"    Range: {sensor.low_limit} - {sensor.high_limit} {sensor.unit}")
    print("=" * 70)
    print("\nStarting sensors...\n")
    
    # Start all sensors
    started = []
    for sensor in sensors:
        if sensor.start():
            started.append(sensor)
            time.sleep(0.2)  # Small delay between starts
        else:
            print(f"Failed to start {sensor.sensor_name}")
    
    if not started:
        print("No sensors started successfully.")
        sys.exit(1)
    
    print(f"\n{len(started)} sensor(s) started. Press Ctrl+C to stop.\n")
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\nStopping all sensors...")
        for sensor in started:
            sensor.stop()
        print("All sensors stopped.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()


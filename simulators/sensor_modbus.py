"""
Unified Modbus/TCP Sensor Simulator
Supports multiple sensor types: temperature, pressure, flow, vibration, voltage
Uses Modbus/TCP server to provide sensor data via holding registers
Supports multiple sensors on the same port using different unit IDs

Author: Mohammed Ismail AbdElmageid
"""
import threading
import time
import random
import sys
from datetime import datetime
from collections import defaultdict


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
    
    # Default to voltage if type not found (Modbus is commonly used for voltage)
    return defaults['voltage']


# Global server manager to share Modbus servers across sensors on same host:port
_modbus_servers = {}  # (host, port) -> {'context': ModbusServerContext, 'stores': {unit_id: ModbusSlaveContext}, 'thread': Thread, 'running': bool}
_server_lock = threading.Lock()


class ModbusSensorSimulator:
    """Modbus/TCP-based simulator for sensors (Voltage, Temperature, etc.)"""
    
    def __init__(self, sensor_id=5, sensor_type='voltage',
                 low_limit=None, high_limit=None, unit=None,
                 host="localhost", port=1502, unit_id=1, register=0):
        """
        Initialize Modbus sensor simulator
        
        Args:
            sensor_id: Sensor ID (default: 5)
            sensor_type: Sensor type - 'temperature', 'pressure', 'flow', 'vibration', 'voltage' (default: 'voltage')
            low_limit: Low alarm limit (default: based on sensor_type)
            high_limit: High alarm limit (default: based on sensor_type)
            unit: Unit of measurement (default: based on sensor_type)
            host: Modbus server host (default: localhost)
            port: Modbus server port (default: 1502)
            unit_id: Modbus unit ID (default: 1)
            register: Starting register address (default: 0)
        """
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.register = register
        self.running = False
        self.modbus_context = None
        self.modbus_store = None
        self.worker_thread = None
        
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
        self.frame_format = "Modbus/TCP"  # This sensor uses Modbus/TCP frame format
        
    def generate_sensor_value(self) -> float:
        """Generate a realistic trend-based sensor value"""
        value = self.value_generator.generate_value()
        self.faulty = self.value_generator.faulty
        return value
    
    def update_modbus_register(self, value: float):
        """
        Update Modbus holding register with sensor value
        Values are stored as integer × 10 for decimal precision
        """
        if not self.modbus_store:
            return
        
        try:
            # Store as integer * 10 for decimal precision (e.g., 220.5 -> 2205)
            if value == -999.0:
                int_value = -9990
            else:
                int_value = int(round(value * 10))
            
            # Handle negative values (two's complement for 16-bit)
            if int_value < 0:
                int_value = int_value + 65536
            
            # Function code 3 = holding registers
            # Use the store associated with this sensor's unit_id
            self.modbus_store.setValues(3, self.register, [int_value])
        except Exception as e:
            print(f"Modbus update error for {self.sensor_name}: {e}")
    
    def modbus_worker(self):
        """Worker thread that updates Modbus register values"""
        while self.running:
            value = self.generate_sensor_value()
            self.update_modbus_register(value)
            time.sleep(0.5)  # Update every 0.5 seconds
    
    def start(self):
        """
        Start Modbus sensor (server is created in main() for grouped sensors)
        This method is kept for backward compatibility but is now called from main()
        """
        # Server setup is now done in main() to support multiple sensors on same port
        # This method is a placeholder for backward compatibility
        pass
    
    def stop(self):
        """Stop the simulator"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        
        # Remove from server tracking
        server_key = (self.host, self.port)
        with _server_lock:
            if server_key in _modbus_servers:
                server_info = _modbus_servers[server_key]
                if self in server_info['sensors']:
                    server_info['sensors'].remove(self)
                
                # If no more sensors, we could stop the server, but for simplicity
                # we'll leave it running (daemon threads will clean up on exit)
        
        print(f"{self.sensor_name} Modbus/TCP simulator stopped.")


def parse_config_string(config_str: str):
    """
    Parse simplified configuration string format:
    type:id:host:port:unit_id:register[:low[:high[:unit]]]
    
    Example: voltage:5:localhost:1502:1:0
    Example: voltage:5:localhost:1502:1:0:200:240:V
    """
    parts = config_str.split(':')
    if len(parts) < 6:
        raise ValueError(f"Invalid config format. Minimum required: type:id:host:port:unit_id:register\n"
                        f"Got {len(parts)} parts, expected at least 6\n"
                        f"Examples:\n"
                        f"  voltage:5:localhost:1502:1:0\n"
                        f"  voltage:5:localhost:1502:1:0:200:240\n"
                        f"  voltage:5:localhost:1502:1:0:200:240:V")
    
    sensor_type = parts[0].strip()
    sensor_id = int(parts[1].strip())
    host = parts[2].strip()
    port = int(parts[3].strip())
    unit_id = int(parts[4].strip())
    register = int(parts[5].strip())
    
    # Optional parameters (limits and unit)
    low_limit = float(parts[6].strip()) if len(parts) > 6 and parts[6].strip() else None
    high_limit = float(parts[7].strip()) if len(parts) > 7 and parts[7].strip() else None
    unit = parts[8].strip() if len(parts) > 8 and parts[8].strip() else None
    
    return {
        'sensor_type': sensor_type,
        'sensor_id': sensor_id,
        'host': host,
        'port': port,
        'unit_id': unit_id,
        'register': register,
        'low_limit': low_limit,
        'high_limit': high_limit,
        'unit': unit
    }


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Unified Modbus/TCP Sensor Simulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using simplified config string (limits and unit are optional):
  python sensor_modbus.py --config "voltage:5:localhost:1502:1:0"
  python sensor_modbus.py --config "voltage:5:localhost:1502:1:0:200:240"
  python sensor_modbus.py --config "voltage:5:localhost:1502:1:0:200:240:V"
  python sensor_modbus.py --config "temperature:6:localhost:1503:2:0:20:80:°C"
  
  # Running multiple sensors at once (different ports):
  python sensor_modbus.py --config "voltage:5:localhost:1502:1:0" --config "temperature:6:localhost:1503:1:0"
  
  # Running multiple sensors on the SAME port (different unit IDs):
  python sensor_modbus.py --config "voltage:5:localhost:1502:1:0" --config "temperature:6:localhost:1502:2:0"
  python sensor_modbus.py --config "voltage:5:localhost:1502:1:0" --config "pressure:7:localhost:1502:2:0" --config "flow:8:localhost:1502:3:0"
  
  # Using individual arguments (single sensor only):
  python sensor_modbus.py --sensor-id 5 --sensor-type voltage
  python sensor_modbus.py --sensor-id 6 --sensor-type temperature --low-limit 20.0 --high-limit 80.0
        """
    )
    
    parser.add_argument('--config', type=str, default=None, action='append',
                        help='Simplified config string: type:id:host:port:unit_id:register[:low[:high[:unit]]]\n'
                             'Can be specified multiple times to run multiple sensors.\n'
                             'Examples:\n'
                             '  --config "voltage:5:localhost:1502:1:0" --config "temperature:6:localhost:1503:1:0"\n'
                             '  voltage:5:localhost:1502:1:0                    (uses defaults)\n'
                             '  voltage:5:localhost:1502:1:0:200:240             (custom limits)\n'
                             '  voltage:5:localhost:1502:1:0:200:240:V          (all parameters)')
    parser.add_argument('--sensor-id', type=int, default=5, help='Sensor ID (default: 5)')
    parser.add_argument('--sensor-type', type=str, default='voltage',
                        choices=['temperature', 'pressure', 'flow', 'vibration', 'voltage'],
                        help='Sensor type (default: voltage)')
    parser.add_argument('--low-limit', type=float, default=None,
                        help='Low alarm limit (default: based on sensor type)')
    parser.add_argument('--high-limit', type=float, default=None,
                        help='High alarm limit (default: based on sensor type)')
    parser.add_argument('--unit', type=str, default=None,
                        help='Unit of measurement (default: based on sensor type)')
    parser.add_argument('--host', type=str, default='localhost', help='Modbus server host (default: localhost)')
    parser.add_argument('--port', type=int, default=1502, help='Modbus server port (default: 1502)')
    parser.add_argument('--unit-id', type=int, default=1, help='Modbus unit ID (default: 1)')
    parser.add_argument('--register', type=int, default=0, help='Register address (default: 0)')
    
    args = parser.parse_args()
    
    simulators = []
    
    # If config strings are provided, create simulators for each
    if args.config:
        print(f"Creating {len(args.config)} Modbus sensor simulator(s)...\n")
        for config_str in args.config:
            try:
                config = parse_config_string(config_str)
                simulator = ModbusSensorSimulator(
                    sensor_id=config['sensor_id'],
                    sensor_type=config['sensor_type'],
                    low_limit=config['low_limit'],
                    high_limit=config['high_limit'],
                    unit=config['unit'],
                    host=config['host'],
                    port=config['port'],
                    unit_id=config['unit_id'],
                    register=config['register']
                )
                simulators.append(simulator)
            except ValueError as e:
                print(f"Error parsing config string '{config_str}': {e}")
                sys.exit(1)
    else:
        # Use individual arguments (single simulator)
        simulator = ModbusSensorSimulator(
            sensor_id=args.sensor_id,
            sensor_type=args.sensor_type,
            low_limit=args.low_limit,
            high_limit=args.high_limit,
            unit=args.unit,
            host=args.host,
            port=args.port,
            unit_id=args.unit_id,
            register=args.register
        )
        simulators.append(simulator)
    
    # Group simulators by host:port to share servers
    servers_dict = defaultdict(list)  # (host, port) -> [simulators]
    for simulator in simulators:
        servers_dict[(simulator.host, simulator.port)].append(simulator)
    
    # Start servers (one per unique host:port)
    print(f"\n{'='*60}")
    print("Starting Modbus sensor simulators...")
    print(f"{'='*60}\n")
    
    for (host, port), server_simulators in servers_dict.items():
        try:
            # Create Modbus server with all unit_ids for this host:port
            try:
                from pymodbus.server import StartTcpServer
            except ImportError:
                from pymodbus.server.sync import StartTcpServer
            
            from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
            from pymodbus.datastore import ModbusSequentialDataBlock
            
            # Create stores for all unit_ids
            stores = {}
            for simulator in server_simulators:
                if simulator.unit_id not in stores:
                    initial_hr_values = [0] * 100
                    store = ModbusSlaveContext(
                        di=ModbusSequentialDataBlock(0, [0]*100),
                        co=ModbusSequentialDataBlock(0, [0]*100),
                        hr=ModbusSequentialDataBlock(0, initial_hr_values),
                        ir=ModbusSequentialDataBlock(0, [0]*100)
                    )
                    stores[simulator.unit_id] = store
                    
                    # Initialize register with default value
                    base_value = (simulator.low_limit + simulator.high_limit) / 2
                    int_value = int(round(base_value * 10))
                    if int_value < 0:
                        int_value = int_value + 65536
                    store.setValues(3, simulator.register, [int_value])
            
            # Create server context with all unit_ids
            context = ModbusServerContext(slaves=stores, single=False)
            
            # Store server info
            server_key = (host, port)
            with _server_lock:
                _modbus_servers[server_key] = {
                    'context': context,
                    'stores': stores,
                    'thread': None,
                    'running': False,
                    'sensors': server_simulators
                }
            
            # Start Modbus server in separate thread
            def start_server():
                try:
                    # Try async server first
                    from pymodbus.server.async_io import StartAsyncTcpServer
                    import asyncio
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(StartAsyncTcpServer(context=context, address=(host, port)))
                except ImportError:
                    # Fallback to sync server
                    StartTcpServer(context=context, address=(host, port))
                except Exception as e:
                    print(f"Modbus server error on {host}:{port}: {e}")
            
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()
            
            with _server_lock:
                _modbus_servers[server_key]['thread'] = server_thread
                _modbus_servers[server_key]['running'] = True
            
            # Assign context and store to each simulator
            for simulator in server_simulators:
                simulator.modbus_context = context
                simulator.modbus_store = stores[simulator.unit_id]
                simulator.running = True
                
                # Start worker thread for each sensor
                simulator.worker_thread = threading.Thread(target=simulator.modbus_worker, daemon=True)
                simulator.worker_thread.start()
            
            # Wait for server to start
            time.sleep(2.0)
            
            # Verify server is listening
            import socket
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(1)
                result = test_sock.connect_ex((host, port))
                test_sock.close()
                if result == 0:
                    print(f"✓ Modbus/TCP server started on {host}:{port}")
                    print(f"  Serving {len(server_simulators)} sensor(s) with unit IDs: {sorted(stores.keys())}")
                    for simulator in server_simulators:
                        print(f"  - {simulator.sensor_name} (Unit ID: {simulator.unit_id}, Register: {simulator.register})")
                        print(f"    Limits: {simulator.low_limit} - {simulator.high_limit} {simulator.unit}")
                    print()
                else:
                    print(f"⚠ Modbus server may not be ready on {host}:{port}")
            except:
                print(f"⚠ Could not verify Modbus server on {host}:{port}")
                
        except ImportError:
            print("Error: pymodbus not available. Install with: pip install pymodbus")
            sys.exit(1)
        except OSError as e:
            if "permission denied" in str(e).lower() or "address already in use" in str(e).lower():
                print(f"Modbus port {port} requires root or is in use.")
                print(f"Try using a different port (e.g., --port 1503)")
            else:
                print(f"Failed to start Modbus server on {host}:{port}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Failed to start Modbus server on {host}:{port}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    if simulators:
        print(f"{'='*60}")
        print("All Modbus sensor simulators ready. Worker threads should connect to:")
        for i, simulator in enumerate(simulators, 1):
            print(f"  {i}. {simulator.sensor_name}")
            print(f"     Host: {simulator.host}:{simulator.port}, Unit ID: {simulator.unit_id}, Register: {simulator.register}")
        print(f"{'='*60}\n")
        print("All simulators running... Press Ctrl+C to stop all.\n")
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping all simulators...")
        for simulator in simulators:
            simulator.stop()
        print("All simulators stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()



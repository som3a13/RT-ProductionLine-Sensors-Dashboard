"""
Sensor 5 Simulator - Voltage Sensor (Modbus/TCP)
Uses Modbus/TCP server to provide sensor data via holding registers
"""
import threading
import time
import random
import sys
from datetime import datetime


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


class Sensor5Simulator:
    """Modbus/TCP-based simulator for Sensor 5 (Voltage Sensor)"""
    
    def __init__(self, host="localhost", port=1502, unit_id=1, register=0):
        """
        Initialize Modbus sensor simulator
        
        Args:
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
        
        # Sensor configuration
        self.sensor_id = 5
        self.sensor_name = "Voltage Sensor 1"
        self.low_limit = 200.0
        self.high_limit = 240.0
        self.unit = "V"
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
            self.modbus_store.setValues(3, self.register, [int_value])
        except Exception as e:
            print(f"Modbus update error: {e}")
    
    def modbus_worker(self):
        """Worker thread that updates Modbus register values"""
        while self.running:
            value = self.generate_sensor_value()
            self.update_modbus_register(value)
            time.sleep(0.5)  # Update every 0.5 seconds
    
    def start(self):
        """Start Modbus/TCP server"""
        try:
            # Try to import pymodbus
            try:
                from pymodbus.server import StartTcpServer
            except ImportError:
                from pymodbus.server.sync import StartTcpServer
            
            from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
            from pymodbus.datastore import ModbusSequentialDataBlock
            
            # Create Modbus data store with initial values
            initial_hr_values = [0] * 100
            store = ModbusSlaveContext(
                di=ModbusSequentialDataBlock(0, [0]*100),
                co=ModbusSequentialDataBlock(0, [0]*100),
                hr=ModbusSequentialDataBlock(0, initial_hr_values),
                ir=ModbusSequentialDataBlock(0, [0]*100)
            )
            
            # Create server context
            context = ModbusServerContext(slaves={self.unit_id: store}, single=False)
            self.modbus_context = context
            self.modbus_store = store
            
            # Initialize register with default value
            base_value = (self.low_limit + self.high_limit) / 2
            int_value = int(round(base_value * 10))
            if int_value < 0:
                int_value = int_value + 65536
            store.setValues(3, self.register, [int_value])
            
            # Start worker thread to update values
            self.running = True
            self.worker_thread = threading.Thread(target=self.modbus_worker, daemon=True)
            self.worker_thread.start()
            
            # Start Modbus server in separate thread
            def start_server():
                try:
                    # Try async server first
                    from pymodbus.server.async_io import StartAsyncTcpServer
                    import asyncio
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(StartAsyncTcpServer(context=context, address=(self.host, self.port)))
                except ImportError:
                    # Fallback to sync server
                    StartTcpServer(context=context, address=(self.host, self.port))
                except Exception as e:
                    print(f"Modbus server error: {e}")
            
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()
            
            # Wait for server to start
            time.sleep(2.0)
            
            # Verify server is listening
            import socket
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(1)
                result = test_sock.connect_ex((self.host, self.port))
                test_sock.close()
                if result == 0:
                    print(f"✓ {self.sensor_name} Modbus/TCP simulator started")
                    print(f"  Host: {self.host}")
                    print(f"  Port: {self.port}")
                    print(f"  Unit ID: {self.unit_id}")
                    print(f"  Register: {self.register}")
                    print(f"  Frame Format: {self.frame_format}")
                    print(f"\nWorker thread should connect to: {self.host}:{self.port}")
                    print(f"  Unit ID: {self.unit_id}, Register: {self.register}")
                    print("Press Ctrl+C to stop.\n")
                else:
                    print(f"⚠ Modbus server may not be ready on {self.host}:{self.port}")
            except:
                print(f"⚠ Could not verify Modbus server on {self.host}:{self.port}")
                
        except ImportError:
            print("Error: pymodbus not available. Install with: pip install pymodbus")
            sys.exit(1)
        except OSError as e:
            if "permission denied" in str(e).lower() or "address already in use" in str(e).lower():
                print(f"Modbus port {self.port} requires root or is in use.")
                print(f"Try using a different port (e.g., --port 1502)")
            else:
                print(f"Failed to start Modbus server: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Failed to start Modbus simulator: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def stop(self):
        """Stop the simulator"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        print(f"{self.sensor_name} Modbus/TCP simulator stopped.")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sensor 5 (Voltage) Modbus/TCP Simulator')
    parser.add_argument('--host', type=str, default='localhost', help='Modbus server host (default: localhost)')
    parser.add_argument('--port', type=int, default=1502, help='Modbus server port (default: 1502)')
    parser.add_argument('--unit-id', type=int, default=1, help='Modbus unit ID (default: 1)')
    parser.add_argument('--register', type=int, default=0, help='Register address (default: 0)')
    
    args = parser.parse_args()
    
    simulator = Sensor5Simulator(
        host=args.host,
        port=args.port,
        unit_id=args.unit_id,
        register=args.register
    )
    
    try:
        simulator.start()
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping simulator...")
        simulator.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()


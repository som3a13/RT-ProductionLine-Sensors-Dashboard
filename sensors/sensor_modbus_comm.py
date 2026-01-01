"""
Modbus Communication Module - Handles Modbus/TCP communication with sensors
Uses worker thread for communication, thread-safe queue for data

Communication Architecture:
- ModbusSensorCommunicator: Main communication class (acts as Modbus CLIENT)
- Worker Thread: Polls Modbus holding registers in background
- Thread-Safe Queue: Stores sensor readings for main thread consumption
- Callbacks: Notify main thread of new readings (via signals)
- Frame Format: Binary Modbus/TCP (Function Code 3: Read Holding Registers)
- Protocol: One communicator per unique host:port combination
- Multiple sensors can share same port using different unit_ids
- Each sensor has its own unit_id and register address
- Value Encoding: 16-bit integer × 10 (e.g., 2205 = 220.5)
- Negative values: Two's complement (e.g., 55546 = -999.0)

Author: Mohammed Ismail AbdElmageid
"""
import threading
import queue
from datetime import datetime
from typing import Optional, Callable
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
from core.sensor_data import SensorReading, SensorStatus, SensorConfig


class ModbusSensorCommunicator:
    """
    Handles Modbus/TCP communication with sensors using worker thread
    
    Communication Flow:
    1. Connects to Modbus/TCP server (sensor simulator acts as server)
    2. Polls holding registers at configured interval (default: 500ms)
    3. Reads 16-bit integer values from registers
    4. Converts to float (divides by 10 for decimal precision)
    5. Creates SensorReading objects and queues them
    6. Callbacks notify main thread via signals
    
    Multi-Sensor Support:
    - Multiple sensors can share same host:port
    - Each sensor uses different unit_id to distinguish devices
    - Each sensor has its own register address
    - Unit IDs are stored per sensor in sensor_unit_id_map
    """
    
    def __init__(self, host: str, port: int = 502, unit_id: int = 1):
        self.host = host
        self.port = port
        self.unit_id = unit_id  # Default unit_id (for backward compatibility)
        self.client = None
        self.running = False
        self.worker_thread = None
        self.data_queue = queue.Queue()  # Thread-safe queue
        self.sensor_configs: dict = {}
        self.sensor_register_map: dict = {}  # sensor_id -> register_address
        self.sensor_unit_id_map: dict = {}  # sensor_id -> unit_id (for multiple sensors on same port)
        self.callbacks: list = []
        self.lock = threading.Lock()
        self.poll_interval = 0.5  # Poll every 500ms
        
    def add_sensor_config(self, sensor_id: int, config: SensorConfig, register_address: int, unit_id: int = None):
        """
        Add sensor configuration with Modbus register address and unit ID
        
        Args:
            sensor_id: Sensor ID
            config: Sensor configuration
            register_address: Modbus register address
            unit_id: Modbus unit ID (if None, uses default from __init__)
        """
        with self.lock:
            self.sensor_configs[sensor_id] = config
            self.sensor_register_map[sensor_id] = register_address
            # Store unit_id per sensor (allows multiple sensors on same port with different unit_ids)
            self.sensor_unit_id_map[sensor_id] = unit_id if unit_id is not None else self.unit_id
    
    def register_callback(self, callback: Callable):
        """Register callback for new sensor readings"""
        with self.lock:
            self.callbacks.append(callback)
    
    def connect(self) -> bool:
        """Connect to Modbus server"""
        try:
            print(f"Connecting to Modbus server at {self.host}:{self.port}...")
            self.client = ModbusTcpClient(host=self.host, port=self.port)
            
            # Try connecting with retries
            max_retries = 3
            for attempt in range(max_retries):
                connection_result = self.client.connect()
                if connection_result:
                    print(f"✓ Modbus connected successfully to {self.host}:{self.port}")
                    self.running = True
                    self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
                    self.worker_thread.start()
                    return True
                else:
                    if attempt < max_retries - 1:
                        print(f"Connection attempt {attempt + 1} failed, retrying...")
                        import time
                        time.sleep(1)
                    else:
                        print(f"✗ Modbus connection failed to {self.host}:{self.port} after {max_retries} attempts")
                        print(f"  Make sure the Modbus simulator is running on {self.host}:{self.port}")
                        return False
            return False
        except Exception as e:
            print(f"Modbus connection error to {self.host}:{self.port}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def disconnect(self):
        """Disconnect from Modbus server"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        if self.client:
            self.client.close()
        self.client = None
    
    def _worker_loop(self):
        """Worker thread loop - polls Modbus registers"""
        import time
        
        while self.running:
            try:
                with self.lock:
                    sensor_ids = list(self.sensor_register_map.keys())
                
                for sensor_id in sensor_ids:
                    if not self.running:
                        break
                    
                    reading = self._read_sensor(sensor_id)
                    if reading:
                        # Put in thread-safe queue (NOT updating GUI directly)
                        self.data_queue.put(reading)
                        
                        # Call callbacks (will be handled in main thread)
                        with self.lock:
                            for callback in self.callbacks:
                                try:
                                    callback(reading)
                                except Exception as e:
                                    print(f"Callback error: {e}")
                
                time.sleep(self.poll_interval)
            except Exception as e:
                if self.running:
                    print(f"Modbus worker error: {e}")
                time.sleep(self.poll_interval)
    
    def _read_sensor(self, sensor_id: int) -> Optional[SensorReading]:
        """Read sensor value from Modbus register"""
        try:
            with self.lock:
                if sensor_id not in self.sensor_register_map:
                    return None
                register = self.sensor_register_map[sensor_id]
                config = self.sensor_configs.get(sensor_id)
                # Get unit_id for this specific sensor (allows different unit_ids on same port)
                sensor_unit_id = self.sensor_unit_id_map.get(sensor_id, self.unit_id)
            
            # Check connection
            if not self.client:
                return None
            
            # Try to reconnect if socket is closed
            try:
                # Check if socket is open (different methods for different pymodbus versions)
                socket_open = False
                if hasattr(self.client, 'is_socket_open'):
                    socket_open = self.client.is_socket_open()
                elif hasattr(self.client, 'socket') and self.client.socket:
                    socket_open = True
                elif hasattr(self.client, '_connected'):
                    socket_open = self.client._connected
                
                if not socket_open:
                    try:
                        self.client.connect()
                    except:
                        return None
            except:
                # If we can't check, try to reconnect anyway
                try:
                    self.client.connect()
                except:
                    pass
            
            # Read holding register (function code 3)
            # Assuming 16-bit integer value, scale by 10 for decimal precision
            # Use sensor-specific unit_id (allows multiple sensors on same port)
            try:
                # For pymodbus 3.x, use slave parameter instead of unit
                # Try both methods for compatibility
                try:
                    result = self.client.read_holding_registers(register, 1, slave=sensor_unit_id)
                except TypeError:
                    # Fallback to unit parameter for older versions
                    result = self.client.read_holding_registers(register, 1, unit=sensor_unit_id)
            except Exception as e:
                # Connection error - try to reconnect
                print(f"Modbus read exception for sensor {sensor_id}: {e}")
                try:
                    self.client.connect()
                except:
                    pass
                if config:
                    return SensorReading(
                        sensor_id=sensor_id,
                        sensor_name=config.name,
                        value=-999.0,
                        timestamp=datetime.now(),
                        status=SensorStatus.FAULTY,
                        unit=config.unit
                    )
                return None
            
            if result.isError():
                error_msg = str(result)
                # Only print error occasionally to avoid spam
                if not hasattr(self, '_last_error_time') or (datetime.now().timestamp() - getattr(self, '_last_error_time', 0)) > 5:
                    print(f"Modbus read error for sensor {sensor_id} (register {register}): {error_msg}")
                    self._last_error_time = datetime.now().timestamp()
                
                # Try to reconnect
                try:
                    self.client.connect()
                except:
                    pass
                
                # Sensor faulty
                if config:
                    return SensorReading(
                        sensor_id=sensor_id,
                        sensor_name=config.name,
                        value=-999.0,
                        timestamp=datetime.now(),
                        status=SensorStatus.FAULTY,
                        unit=config.unit
                    )
                return None
            
            # Convert register value to float (assuming value is stored as integer * 10)
            if not hasattr(result, 'registers') or not result.registers:
                print(f"Modbus read: no registers returned for sensor {sensor_id}")
                return None
                
            raw_value = result.registers[0]
            
            # Handle negative values (two's complement for 16-bit)
            if raw_value > 32767:
                raw_value = raw_value - 65536
            
            value = raw_value / 10.0  # Scale down
            
            # Check if value indicates faulty sensor (-999.0)
            is_faulty = (value == -999.0)
            
            # Determine status
            with self.lock:
                if config:
                    status = config.get_status(value, is_faulty)
                else:
                    # Without config, check if -999 (faulty) or use OK
                    status = SensorStatus.FAULTY if is_faulty else SensorStatus.OK
            
            return SensorReading(
                sensor_id=sensor_id,
                sensor_name=config.name if config else f"Sensor {sensor_id}",
                value=value,
                timestamp=datetime.now(),
                status=status,
                unit=config.unit if config else ""
            )
        except ModbusException as e:
            print(f"Modbus read error for sensor {sensor_id}: {e}")
            # Return faulty reading
            with self.lock:
                config = self.sensor_configs.get(sensor_id)
                if config:
                    return SensorReading(
                        sensor_id=sensor_id,
                        sensor_name=config.name,
                        value=-999.0,
                        timestamp=datetime.now(),
                        status=SensorStatus.FAULTY,
                        unit=config.unit
                    )
        except Exception as e:
            print(f"Error reading sensor {sensor_id}: {e}")
        return None
    
    def get_latest_reading(self, timeout: float = 0.1) -> Optional[SensorReading]:
        """Get latest sensor reading from queue (thread-safe, non-blocking)"""
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None


"""
TCP Communication Module - Handles TCP socket communication with sensors
Connects to TCP sensor server and receives data relayed from sensor clients
Uses worker thread for communication, thread-safe queue for data

Communication Architecture:
- TCPSensorCommunicator: Main communication class
- Worker Thread: Receives data from TCP sensor server in background
- Thread-Safe Queue: Stores sensor readings for main thread consumption
- Callbacks: Notify main thread of new readings (via signals)
- Frame Format: JSON terminated by newline (\n)
- Protocol: One communicator per unique host:port combination
- Multiple sensors can share same server (identified by sensor_id in JSON)
- Server relays data from multiple sensor clients to application

Author: Mohammed Ismail AbdElmageid
"""
import socket
import json
import threading
import queue
import time
from datetime import datetime
from typing import Dict, Callable, Optional
from core.sensor_data import SensorReading, SensorStatus, SensorConfig, AlarmEvent


class TCPSensorCommunicator:
    """
    Handles TCP socket communication with sensors using worker thread
    
    Communication Flow:
    1. Connects to TCP sensor server (tcp_sensor_server.py)
    2. Server relays data from sensor clients to application
    3. Worker thread continuously receives JSON frames
    4. Parses JSON frames terminated by newline (\n)
    5. Creates SensorReading objects and queues them
    6. Callbacks notify main thread via signals
    
    Architecture:
    - Connects to TCP sensor server (tcp_sensor_server.py)
    - Receives data relayed from sensor clients (via start_tcp_system.py or run_tcp_sensor_clients.py)
    - Parses JSON frames and routes to correct sensor configurations
    
    Multi-Sensor Support:
    - Multiple sensors can share same TCP server
    - Each sensor identified by sensor_id in JSON frame
    - One communicator per unique host:port combination
    """
    
    def __init__(self, host: str = "localhost", port: int = 5000):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.worker_thread = None
        self.data_queue = queue.Queue()  # Thread-safe queue
        self.sensor_configs: Dict[int, SensorConfig] = {}
        self.callbacks: list = []
        self.lock = threading.Lock()
        
    def add_sensor_config(self, sensor_id: int, config: SensorConfig):
        """Add sensor configuration"""
        with self.lock:
            self.sensor_configs[sensor_id] = config
            print(f"TCP {self.host}:{self.port}: Added config for sensor_id={sensor_id} ({config.name}). "
                  f"Total configs: {list(self.sensor_configs.keys())}")
    
    def register_callback(self, callback: Callable):
        """Register callback for new sensor readings"""
        with self.lock:
            self.callbacks.append(callback)
    
    def connect(self) -> bool:
        """Connect to TCP sensor server"""
        try:
            print(f"Connecting to TCP sensor server at {self.host}:{self.port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            
            # Show which sensors are configured
            with self.lock:
                sensor_ids = list(self.sensor_configs.keys())
            if sensor_ids:
                print(f"✓ TCP connection established to {self.host}:{self.port}")
                print(f"  Monitoring sensors: {', '.join([f'Sensor {sid}' for sid in sensor_ids])}")
            else:
                print(f"✓ TCP connection established to {self.host}:{self.port}")
                print(f"  Waiting for sensor configurations...")
            
            return True
        except Exception as e:
            print(f"✗ TCP connection error to {self.host}:{self.port}: {e}")
            print(f"  Make sure TCP sensor server is running: python3 simulators/tcp_sensor_server.py")
            return False
    
    def disconnect(self):
        """Disconnect from sensor server"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.socket = None
    
    def _worker_loop(self):
        """Worker thread loop - receives data from TCP socket (relayed from sensor clients)"""
        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    print("TCP connection closed by server")
                    break
                
                buffer += data.decode('utf-8')
                
                # Process complete JSON messages
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            data_dict = json.loads(line)
                            reading = self._parse_sensor_data(data_dict)
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
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"TCP worker error: {e}")
                break
    
    def _parse_sensor_data(self, data_dict: Dict) -> Optional[SensorReading]:
        """Parse sensor data from JSON dictionary"""
        try:
            # Ensure sensor_id is an integer (JSON might have it as string or int)
            sensor_id_raw = data_dict.get("sensor_id")
            sensor_id = int(sensor_id_raw) if sensor_id_raw is not None else None
            
            if sensor_id is None:
                print(f"Error: sensor_id is missing in data: {data_dict}")
                return None
                
            sensor_name = data_dict.get("sensor_name", f"Sensor {sensor_id}")
            value = float(data_dict.get("value", 0))
            timestamp_str = data_dict.get("timestamp")
            status_str = data_dict.get("status", "OK")
            unit = data_dict.get("unit", "")
            
            # Parse timestamp
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # Determine status
            is_faulty = (status_str == "FAULTY" or value == -999.0)
            
            with self.lock:
                if sensor_id in self.sensor_configs:
                    config = self.sensor_configs[sensor_id]
                    status = config.get_status(value, is_faulty)
                else:
                    # Config not found - this shouldn't happen if sensor was properly added
                    # But as fallback, check if value is -999 (faulty) or use OK
                    # Note: Without config, we can't check alarm limits, so default to OK
                    # This is a safety fallback - the sensor should have been configured
                    print(f"Warning: Sensor config not found for sensor_id={sensor_id} (type: {type(sensor_id)}) "
                          f"on TCP communicator {self.host}:{self.port}. "
                          f"Status calculation may be incorrect. Value: {value}, "
                          f"Available configs: {list(self.sensor_configs.keys())}")
                    print(f"  This sensor's data is being received by the wrong TCP communicator!")
                    print(f"  Expected: Check config.json - sensor_id={sensor_id} should use port matching this communicator")
                    status = SensorStatus.FAULTY if is_faulty else SensorStatus.OK
            
            return SensorReading(
                sensor_id=sensor_id,
                sensor_name=sensor_name,
                value=value,
                timestamp=timestamp,
                status=status,
                unit=unit
            )
        except Exception as e:
            print(f"Parse error: {e}")
            return None
    
    def get_latest_reading(self, timeout: float = 0.1) -> Optional[SensorReading]:
        """Get latest sensor reading from queue (thread-safe, non-blocking)"""
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def check_alarm(self, reading: SensorReading) -> Optional[AlarmEvent]:
        """Check if reading triggers an alarm"""
        with self.lock:
            if reading.sensor_id in self.sensor_configs:
                config = self.sensor_configs[reading.sensor_id]
                return config.check_alarm(reading.value)
        return None


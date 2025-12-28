"""
Serial Communication Module - Handles serial port communication with sensors
Uses worker thread for communication, thread-safe queue for data
Supports both real serial ports and TCP sockets (for virtual testing)
"""
import serial
import serial.tools.list_ports
import threading
import queue
import json
import socket
from datetime import datetime
from typing import Optional, Callable
from core.sensor_data import SensorReading, SensorStatus, SensorConfig


class SerialSensorCommunicator:
    """Handles serial port communication with sensors using worker thread"""
    
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.running = False
        self.worker_thread = None
        self.data_queue = queue.Queue()  # Thread-safe queue
        self.sensor_configs: dict = {}
        self.callbacks: list = []
        self.lock = threading.Lock()
        
    def add_sensor_config(self, sensor_id: int, config: SensorConfig):
        """Add sensor configuration"""
        with self.lock:
            self.sensor_configs[sensor_id] = config
    
    def register_callback(self, callback: Callable):
        """Register callback for new sensor readings"""
        with self.lock:
            self.callbacks.append(callback)
    
    def connect(self) -> bool:
        """Connect to serial port (or TCP if port starts with localhost:)"""
        try:
            # If port looks like a TCP address, use TCP instead
            if self.port.startswith("localhost:") or ":" in self.port and not self.port.startswith("/"):
                # Parse as TCP address
                parts = self.port.split(":")
                host = parts[0] if parts[0] else "localhost"
                port = int(parts[1]) if len(parts) > 1 else 6000
                # Use TCP socket instead of serial
                self.serial_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.serial_conn.connect((host, port))
                self.serial_conn.settimeout(self.timeout)
                self.is_tcp = True
            else:
                # Real serial port
                self.serial_conn = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout
                )
                self.is_tcp = False
            
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            return True
        except Exception as e:
            print(f"Serial connection error on {self.port}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from serial port or TCP"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        if self.serial_conn:
            if hasattr(self, 'is_tcp') and self.is_tcp:
                # TCP socket
                try:
                    self.serial_conn.close()
                except:
                    pass
            else:
                # Serial port
                try:
                    if self.serial_conn.is_open:
                        self.serial_conn.close()
                except:
                    pass
        self.serial_conn = None
    
    def _worker_loop(self):
        """Worker thread loop - reads from serial port or TCP socket"""
        import socket
        buffer = ""
        while self.running:
            try:
                data_received = False
                
                if hasattr(self, 'is_tcp') and self.is_tcp:
                    # TCP socket mode
                    try:
                        data = self.serial_conn.recv(4096)
                        if not data:
                            break
                        buffer += data.decode('utf-8', errors='ignore')
                        data_received = True
                    except socket.timeout:
                        pass
                else:
                    # Serial port mode
                    if self.serial_conn and self.serial_conn.in_waiting > 0:
                        data = self.serial_conn.read(self.serial_conn.in_waiting)
                        buffer += data.decode('utf-8', errors='ignore')
                        data_received = True
                
                # Process complete JSON messages (for both TCP and serial)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        reading = self._parse_message(line.strip())
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
                
                # Small delay to avoid busy waiting if no data received
                if not data_received:
                    threading.Event().wait(0.1)
                    
            except Exception as e:
                if self.running:
                    print(f"Serial worker error on {self.port}: {e}")
                break
    
    def _parse_message(self, message: str) -> Optional[SensorReading]:
        """Parse sensor data from JSON message"""
        try:
            data = json.loads(message)
            sensor_id = data.get("sensor_id")
            sensor_name = data.get("sensor_name", f"Sensor {sensor_id}")
            value = float(data.get("value", 0))
            timestamp_str = data.get("timestamp")
            status_str = data.get("status", "OK")
            unit = data.get("unit", "")
            
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
    
    @staticmethod
    def list_available_ports():
        """List available serial ports"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]


"""
Unified Sensor Communication Manager
Manages multiple sensors across different protocols (Serial, TCP, Modbus)
All communication happens in worker threads, GUI updates via thread-safe queues/signals
"""
import threading
from typing import Dict, List, Optional
from PyQt5.QtCore import QObject, pyqtSignal

from core.sensor_data import SensorReading, SensorConfig, AlarmEvent
from sensors.sensor_serial_comm import SerialSensorCommunicator
from sensors.sensor_tcp_comm import TCPSensorCommunicator
from sensors.sensor_modbus_comm import ModbusSensorCommunicator


class SensorManager(QObject):
    """
    Unified manager for all sensor communications
    Uses worker threads for each protocol, thread-safe queues for data
    Signals are used to notify GUI thread (never update GUI from worker threads)
    """
    # Signals for thread-safe GUI updates (only main thread receives these)
    sensor_reading_received = pyqtSignal(object)  # SensorReading
    alarm_triggered = pyqtSignal(object)  # AlarmEvent
    
    def __init__(self):
        super().__init__()
        self.serial_communicators: Dict[str, SerialSensorCommunicator] = {}
        self.tcp_communicators: Dict[str, TCPSensorCommunicator] = {}
        self.modbus_communicators: Dict[str, ModbusSensorCommunicator] = {}
        self.sensor_configs: Dict[int, SensorConfig] = {}
        self.sensor_protocol_map: Dict[int, str] = {}  # sensor_id -> protocol_key
        self.lock = threading.Lock()
        
    def add_sensor(self, sensor_id: int, config: SensorConfig, protocol: str, 
                   protocol_config: dict):
        """
        Add a sensor with specified protocol
        
        Args:
            sensor_id: Unique sensor ID
            config: Sensor configuration
            protocol: 'serial', 'tcp', or 'modbus'
            protocol_config: Protocol-specific configuration
        """
        with self.lock:
            self.sensor_configs[sensor_id] = config
            
            if protocol == "serial":
                port = protocol_config.get("port")
                baudrate = protocol_config.get("baudrate", 9600)
                key = f"serial_{port}"
                
                if key not in self.serial_communicators:
                    comm = SerialSensorCommunicator(port=port, baudrate=baudrate)
                    comm.register_callback(self._on_reading_received)
                    self.serial_communicators[key] = comm
                else:
                    comm = self.serial_communicators[key]
                
                comm.add_sensor_config(sensor_id, config)
                self.sensor_protocol_map[sensor_id] = key
                
            elif protocol == "tcp":
                host = protocol_config.get("host", "localhost")
                port = protocol_config.get("port", 5000)
                key = f"tcp_{host}_{port}"
                
                if key not in self.tcp_communicators:
                    comm = TCPSensorCommunicator(host=host, port=port)
                    comm.register_callback(self._on_reading_received)
                    self.tcp_communicators[key] = comm
                else:
                    comm = self.tcp_communicators[key]
                
                comm.add_sensor_config(sensor_id, config)
                self.sensor_protocol_map[sensor_id] = key
                
            elif protocol == "modbus":
                host = protocol_config.get("host", "localhost")
                port = protocol_config.get("port", 502)
                unit_id = protocol_config.get("unit_id", 1)
                register = protocol_config.get("register", 0)
                key = f"modbus_{host}_{port}"
                
                if key not in self.modbus_communicators:
                    # Use first sensor's unit_id as default (for backward compatibility)
                    comm = ModbusSensorCommunicator(host=host, port=port, unit_id=unit_id)
                    comm.register_callback(self._on_reading_received)
                    self.modbus_communicators[key] = comm
                else:
                    comm = self.modbus_communicators[key]
                
                # Pass unit_id per sensor (allows multiple sensors on same port with different unit_ids)
                comm.add_sensor_config(sensor_id, config, register, unit_id=unit_id)
                self.sensor_protocol_map[sensor_id] = key
    
    def _on_reading_received(self, reading: SensorReading):
        """
        Callback from worker threads - emits signal for GUI thread
        This is the ONLY way worker threads communicate with GUI
        """
        # Emit signal (thread-safe, handled in main/GUI thread)
        self.sensor_reading_received.emit(reading)
        
        # Check for alarms
        with self.lock:
            if reading.sensor_id in self.sensor_configs:
                config = self.sensor_configs[reading.sensor_id]
                alarm = config.check_alarm(reading.value)
                if alarm:
                    # Emit alarm signal (thread-safe)
                    self.alarm_triggered.emit(alarm)
    
    def connect_all(self) -> Dict[str, bool]:
        """Connect all communicators, returns status for each"""
        results = {}
        
        # Connect serial communicators
        for key, comm in self.serial_communicators.items():
            results[key] = comm.connect()
        
        # Connect TCP communicators
        for key, comm in self.tcp_communicators.items():
            results[key] = comm.connect()
        
        # Connect Modbus communicators
        for key, comm in self.modbus_communicators.items():
            results[key] = comm.connect()
        
        return results
    
    def disconnect_all(self):
        """Disconnect all communicators"""
        for comm in self.serial_communicators.values():
            comm.disconnect()
        for comm in self.tcp_communicators.values():
            comm.disconnect()
        for comm in self.modbus_communicators.values():
            comm.disconnect()
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all communicators"""
        status = {}
        
        for key, comm in self.serial_communicators.items():
            status[key] = comm.serial_conn is not None and comm.serial_conn.is_open
        
        for key, comm in self.tcp_communicators.items():
            status[key] = comm.socket is not None
        
        for key, comm in self.modbus_communicators.items():
            status[key] = comm.client is not None and comm.client.is_socket_open()
        
        return status

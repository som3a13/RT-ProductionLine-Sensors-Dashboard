"""
Sensor Data Models and Alarm Logic
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class SensorStatus(Enum):
    """Sensor status enumeration"""
    OK = "OK"
    FAULTY = "Faulty Sensor"
    LOW_ALARM = "LOW Alarm"
    HIGH_ALARM = "HIGH Alarm"


@dataclass
class SensorReading:
    """Represents a single sensor reading"""
    sensor_id: int
    sensor_name: str
    value: float
    timestamp: datetime
    status: SensorStatus
    unit: str = ""


@dataclass
class AlarmEvent:
    """Represents an alarm event"""
    timestamp: datetime
    sensor_name: str
    sensor_id: int
    value: float
    alarm_type: str  # "LOW" or "HIGH"
    unit: str = ""


class SensorConfig:
    """Configuration for a sensor"""
    def __init__(self, name: str, sensor_id: int, low_limit: float, 
                 high_limit: float, unit: str = ""):
        self.name = name
        self.sensor_id = sensor_id
        self.low_limit = low_limit
        self.high_limit = high_limit
        self.unit = unit
    
    def check_alarm(self, value: float) -> Optional[AlarmEvent]:
        """Check if value triggers an alarm and return AlarmEvent if so"""
        if value < self.low_limit:
            return AlarmEvent(
                timestamp=datetime.now(),
                sensor_name=self.name,
                sensor_id=self.sensor_id,
                value=value,
                alarm_type="LOW",
                unit=self.unit
            )
        elif value > self.high_limit:
            return AlarmEvent(
                timestamp=datetime.now(),
                sensor_name=self.name,
                sensor_id=self.sensor_id,
                value=value,
                alarm_type="HIGH",
                unit=self.unit
            )
        return None
    
    def get_status(self, value: float, is_faulty: bool = False) -> SensorStatus:
        """Get sensor status based on value"""
        if is_faulty:
            return SensorStatus.FAULTY
        if value < self.low_limit:
            return SensorStatus.LOW_ALARM
        if value > self.high_limit:
            return SensorStatus.HIGH_ALARM
        return SensorStatus.OK


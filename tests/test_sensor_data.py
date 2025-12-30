"""
Unit tests for sensor data models and alarm logic
"""
import pytest
from datetime import datetime
from core.sensor_data import SensorConfig, SensorReading, SensorStatus, AlarmEvent


class TestSensorConfig:
    """Test SensorConfig class"""
    
    def test_sensor_config_creation(self):
        """Test creating a sensor configuration"""
        config = SensorConfig(
            name="Test Sensor",
            sensor_id=1,
            low_limit=10.0,
            high_limit=100.0,
            unit="°C"
        )
        assert config.name == "Test Sensor"
        assert config.sensor_id == 1
        assert config.low_limit == 10.0
        assert config.high_limit == 100.0
        assert config.unit == "°C"
    
    def test_low_alarm(self):
        """Test low alarm detection"""
        config = SensorConfig(
            name="Test Sensor",
            sensor_id=1,
            low_limit=10.0,
            high_limit=100.0
        )
        alarm = config.check_alarm(5.0)
        assert alarm is not None
        assert alarm.alarm_type == "LOW"
        assert alarm.value == 5.0
    
    def test_high_alarm(self):
        """Test high alarm detection"""
        config = SensorConfig(
            name="Test Sensor",
            sensor_id=1,
            low_limit=10.0,
            high_limit=100.0
        )
        alarm = config.check_alarm(150.0)
        assert alarm is not None
        assert alarm.alarm_type == "HIGH"
        assert alarm.value == 150.0
    
    def test_no_alarm(self):
        """Test no alarm when value is within limits"""
        config = SensorConfig(
            name="Test Sensor",
            sensor_id=1,
            low_limit=10.0,
            high_limit=100.0
        )
        alarm = config.check_alarm(50.0)
        assert alarm is None
    
    def test_get_status_ok(self):
        """Test status OK"""
        config = SensorConfig(
            name="Test Sensor",
            sensor_id=1,
            low_limit=10.0,
            high_limit=100.0
        )
        status = config.get_status(50.0)
        assert status == SensorStatus.OK
    
    def test_get_status_low_alarm(self):
        """Test status LOW_ALARM"""
        config = SensorConfig(
            name="Test Sensor",
            sensor_id=1,
            low_limit=10.0,
            high_limit=100.0
        )
        status = config.get_status(5.0)
        assert status == SensorStatus.LOW_ALARM
    
    def test_get_status_high_alarm(self):
        """Test status HIGH_ALARM"""
        config = SensorConfig(
            name="Test Sensor",
            sensor_id=1,
            low_limit=10.0,
            high_limit=100.0
        )
        status = config.get_status(150.0)
        assert status == SensorStatus.HIGH_ALARM
    
    def test_get_status_faulty(self):
        """Test status FAULTY"""
        config = SensorConfig(
            name="Test Sensor",
            sensor_id=1,
            low_limit=10.0,
            high_limit=100.0
        )
        status = config.get_status(50.0, is_faulty=True)
        assert status == SensorStatus.FAULTY


class TestSensorReading:
    """Test SensorReading class"""
    
    def test_sensor_reading_creation(self):
        """Test creating a sensor reading"""
        reading = SensorReading(
            sensor_id=1,
            sensor_name="Test Sensor",
            value=45.5,
            timestamp=datetime.now(),
            status=SensorStatus.OK,
            unit="°C"
        )
        assert reading.sensor_id == 1
        assert reading.sensor_name == "Test Sensor"
        assert reading.value == 45.5
        assert reading.status == SensorStatus.OK
        assert reading.unit == "°C"


class TestAlarmEvent:
    """Test AlarmEvent class"""
    
    def test_alarm_event_creation(self):
        """Test creating an alarm event"""
        alarm = AlarmEvent(
            timestamp=datetime.now(),
            sensor_name="Test Sensor",
            sensor_id=1,
            value=5.0,
            alarm_type="LOW",
            unit="°C"
        )
        assert alarm.sensor_name == "Test Sensor"
        assert alarm.sensor_id == 1
        assert alarm.value == 5.0
        assert alarm.alarm_type == "LOW"
        assert alarm.unit == "°C"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


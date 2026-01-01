"""
Comprehensive Project Verification Script
Tests all components to ensure everything is working correctly

Author: Mohammed Ismail AbdElmageid
"""
import sys
import json
import os
from pathlib import Path

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_success(text):
    """Print success message"""
    print(f"[OK] {text}")

def print_error(text):
    """Print error message"""
    print(f"✗ {text}")

def print_warning(text):
    """Print warning message"""
    print(f"⚠ {text}")

def check_file_exists(filepath, description):
    """Check if file exists"""
    if os.path.exists(filepath):
        print_success(f"{description}: {filepath}")
        return True
    else:
        print_error(f"{description} missing: {filepath}")
        return False

def check_imports():
    """Check if all required modules can be imported"""
    print_header("Checking Python Imports")
    
    modules = [
        ("PyQt5", "PyQt5"),
        ("pyqtgraph", "pyqtgraph"),
        ("numpy", "numpy"),
        ("serial", "pyserial"),
        ("pymodbus", "pymodbus"),
        ("websockets", "websockets"),
        ("aiohttp", "aiohttp"),
        ("requests", "requests"),
    ]
    
    all_ok = True
    for module_name, package_name in modules:
        try:
            __import__(module_name)
            print_success(f"{package_name} imported successfully")
        except ImportError as e:
            print_error(f"{package_name} not found: {e}")
            all_ok = False
    
    return all_ok

def check_config():
    """Check configuration file"""
    print_header("Checking Configuration")
    
    import os
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.json")
    if not check_file_exists(config_path, "Config file"):
        return False
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Check required sections
        required_sections = ["sensors", "update_rate", "alarm_settings", "remote_console"]
        for section in required_sections:
            if section in config:
                print_success(f"Config section '{section}' present")
            else:
                print_error(f"Config section '{section}' missing")
                return False
        
        # Check sensors
        sensors = config.get("sensors", [])
        if len(sensors) >= 5:
            print_success(f"Found {len(sensors)} sensors (required: 5+)")
        else:
            print_error(f"Only {len(sensors)} sensors found (required: 5+)")
            return False
        
        # Check protocols
        protocols = {}
        for sensor in sensors:
            protocol = sensor.get("protocol", "unknown")
            protocols[protocol] = protocols.get(protocol, 0) + 1
        
        print_success(f"Protocol distribution: {protocols}")
        
        # Verify protocol requirements
        required_protocols = {"serial": 2, "tcp": 2, "modbus": 1}
        for protocol, count in required_protocols.items():
            actual = protocols.get(protocol, 0)
            if actual >= count:
                print_success(f"{protocol.upper()}: {actual} sensors (required: {count})")
            else:
                print_error(f"{protocol.upper()}: {actual} sensors (required: {count})")
                return False
        
        return True
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in config.json: {e}")
        return False
    except Exception as e:
        print_error(f"Error reading config.json: {e}")
        return False

def check_core_modules():
    """Check if core modules can be imported"""
    print_header("Checking Core Modules")
    
    modules = [
        "core.sensor_data",
        "sensors.sensor_manager",
        "sensors.sensor_serial_comm",
        "sensors.sensor_tcp_comm",
        "sensors.sensor_modbus_comm",
        "services.alarm_notifications",
        "services.remote_console",
        "gui.main_gui",
    ]
    
    all_ok = True
    for module in modules:
        try:
            __import__(module)
            print_success(f"Module '{module}' imported successfully")
        except ImportError as e:
            print_error(f"Module '{module}' import failed: {e}")
            all_ok = False
        except Exception as e:
            print_error(f"Module '{module}' error: {e}")
            all_ok = False
    
    return all_ok

def check_project_structure():
    """Check project file structure"""
    print_header("Checking Project Structure")
    
    required_files = [
        ("main.py", "Main entry point"),
        ("gui/main_gui.py", "GUI application"),
        ("core/sensor_data.py", "Data models"),
        ("sensors/sensor_manager.py", "Sensor manager"),
        ("sensors/sensor_serial_comm.py", "Serial communication"),
        ("sensors/sensor_tcp_comm.py", "TCP communication"),
        ("sensors/sensor_modbus_comm.py", "Modbus communication"),
        ("services/alarm_notifications.py", "Notification system"),
        ("services/remote_console.py", "Remote console server"),
        ("simulators/sensor_serial.py", "Unified serial sensor simulator"),
        ("simulators/start_tcp_system.py", "TCP sensor system launcher"),
        ("simulators/sensor_modbus.py", "Unified Modbus sensor simulator"),
        ("config/config.json", "Configuration"),
        ("requirements.txt", "Dependencies"),
        ("README.md", "Documentation"),
    ]
    
    all_ok = True
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            all_ok = False
    
    # Check optional files
    optional_files = [
        "web/remote_console_client.html",
        "test_websocket.py",
        "test_modbus.py",
    ]
    
    for filepath in optional_files:
        if os.path.exists(filepath):
            print_success(f"Optional file present: {filepath}")
    
    return all_ok

def check_threading_architecture():
    """Verify threading architecture"""
    print_header("Checking Threading Architecture")
    
    try:
        from sensors.sensor_serial_comm import SerialSensorCommunicator
        from sensors.sensor_tcp_comm import TCPSensorCommunicator
        from sensors.sensor_modbus_comm import ModbusSensorCommunicator
        from sensors.sensor_manager import SensorManager
        
        # Check for thread-safe queues
        import queue
        
        # Check SerialSensorCommunicator - check in __init__ or instance
        import inspect
        serial_init = inspect.getsource(SerialSensorCommunicator.__init__)
        if 'data_queue' in serial_init or 'queue.Queue' in serial_init:
            print_success("SerialSensorCommunicator uses thread-safe queue")
        else:
            print_error("SerialSensorCommunicator missing data_queue")
            return False
        
        # Check TCPSensorCommunicator
        tcp_init = inspect.getsource(TCPSensorCommunicator.__init__)
        if 'data_queue' in tcp_init or 'queue.Queue' in tcp_init:
            print_success("TCPSensorCommunicator uses thread-safe queue")
        else:
            print_error("TCPSensorCommunicator missing data_queue")
            return False
        
        # Check ModbusSensorCommunicator
        modbus_init = inspect.getsource(ModbusSensorCommunicator.__init__)
        if 'data_queue' in modbus_init or 'queue.Queue' in modbus_init:
            print_success("ModbusSensorCommunicator uses thread-safe queue")
        else:
            print_error("ModbusSensorCommunicator missing data_queue")
            return False
        
        # Check SensorManager signals
        from PyQt5.QtCore import pyqtSignal
        if hasattr(SensorManager, 'sensor_reading_received'):
            print_success("SensorManager uses PyQt signals for thread-safe communication")
        else:
            print_error("SensorManager missing sensor_reading_received signal")
            return False
        
        return True
    except Exception as e:
        print_error(f"Threading architecture check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_sensor_data():
    """Test sensor data models"""
    print_header("Testing Sensor Data Models")
    
    try:
        from core.sensor_data import SensorReading, SensorStatus, SensorConfig, AlarmEvent
        from datetime import datetime
        
        # Test SensorConfig
        config = SensorConfig(
            name="Test Sensor",
            sensor_id=1,
            low_limit=10.0,
            high_limit=100.0,
            unit="°C"
        )
        print_success("SensorConfig created successfully")
        
        # Test status calculation
        status_ok = config.get_status(50.0, False)
        status_low = config.get_status(5.0, False)
        status_high = config.get_status(150.0, False)
        status_faulty = config.get_status(0.0, True)
        
        if status_ok == SensorStatus.OK:
            print_success("Status calculation: OK")
        else:
            print_error("Status calculation: OK failed")
            return False
        
        if status_low == SensorStatus.LOW_ALARM:
            print_success("Status calculation: LOW_ALARM")
        else:
            print_error("Status calculation: LOW_ALARM failed")
            return False
        
        if status_high == SensorStatus.HIGH_ALARM:
            print_success("Status calculation: HIGH_ALARM")
        else:
            print_error("Status calculation: HIGH_ALARM failed")
            return False
        
        if status_faulty == SensorStatus.FAULTY:
            print_success("Status calculation: FAULTY")
        else:
            print_error("Status calculation: FAULTY failed")
            return False
        
        # Test alarm detection
        alarm_low = config.check_alarm(5.0)
        alarm_high = config.check_alarm(150.0)
        alarm_none = config.check_alarm(50.0)
        
        if alarm_low and alarm_low.alarm_type == "LOW":
            print_success("Alarm detection: LOW")
        else:
            print_error("Alarm detection: LOW failed")
            return False
        
        if alarm_high and alarm_high.alarm_type == "HIGH":
            print_success("Alarm detection: HIGH")
        else:
            print_error("Alarm detection: HIGH failed")
            return False
        
        if alarm_none is None:
            print_success("Alarm detection: No alarm")
        else:
            print_error("Alarm detection: No alarm failed")
            return False
        
        # Test SensorReading
        reading = SensorReading(
            sensor_id=1,
            sensor_name="Test",
            value=50.0,
            timestamp=datetime.now(),
            status=SensorStatus.OK,
            unit="°C"
        )
        print_success("SensorReading created successfully")
        
        return True
    except Exception as e:
        print_error(f"Sensor data test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all verification checks"""
    print_header("Si-Ware Production Line Monitoring System - Project Verification")
    
    results = []
    
    # Run all checks
    results.append(("Project Structure", check_project_structure()))
    results.append(("Python Imports", check_imports()))
    results.append(("Configuration", check_config()))
    results.append(("Core Modules", check_core_modules()))
    results.append(("Threading Architecture", check_threading_architecture()))
    results.append(("Sensor Data Models", check_sensor_data()))
    
    # Print summary
    print_header("Verification Summary")
    
    all_passed = True
    for check_name, result in results:
        if result:
            print_success(f"{check_name}: PASSED")
        else:
            print_error(f"{check_name}: FAILED")
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("[OK] ALL CHECKS PASSED - Project is ready!")
        print("\nNext steps:")
        print("1. Start simulators: ./scripts/run_all_sensors.sh")
        print("2. Start application: python3 main.py")
        print("   (Remote console starts automatically on port 8080)")
    else:
        print("✗ SOME CHECKS FAILED - Please fix the issues above")
        sys.exit(1)
    print("="*60 + "\n")

if __name__ == "__main__":
    main()


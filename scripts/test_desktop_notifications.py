#!/usr/bin/env python3
"""
Test script for desktop notifications on Linux Ubuntu and Windows

Author: Mohammed Ismail AbdElmageid
"""
import sys
import json
import platform
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.sensor_data import AlarmEvent
from services.alarm_notifications import NotificationManager

def test_desktop_notifications():
    """Test desktop notifications"""
    print("=" * 60)
    print("Desktop Notifications Test")
    print("=" * 60)
    print(f"Platform: {platform.system()}")
    print()
    
    # Load config
    config_path = project_root / "config" / "config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Enable desktop notifications
    config["alarm_settings"]["enable_desktop_notifications"] = True
    
    print("\n1. Initializing NotificationManager...")
    try:
        manager = NotificationManager(config)
        print(f"   [OK] NotificationManager initialized")
        print(f"   - Desktop notifications enabled: {manager.desktop_enabled}")
        print(f"   - System tray available: {manager.tray_icon is not None}")
        if manager.is_windows:
            print(f"   - Windows toast available: {manager.win10toast_available}")
        elif manager.is_linux:
            print(f"   - Using notify-send: {manager.use_system_notify}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Create test alarms
    print("\n2. Creating test alarms...")
    alarms = [
        AlarmEvent(
            timestamp=datetime.now(),
            sensor_name="Temperature Sensor 1",
            sensor_id=1,
            value=85.5,
            alarm_type="HIGH",
            unit="°C"
        ),
        AlarmEvent(
            timestamp=datetime.now(),
            sensor_name="Pressure Sensor 1",
            sensor_id=2,
            value=45.0,
            alarm_type="LOW",
            unit="PSI"
        ),
    ]
    
    print(f"   [OK] Created {len(alarms)} test alarms")
    
    # Send notifications
    print("\n3. Sending desktop notifications...")
    print("   (You should see desktop notifications appear)")
    print()
    
    for i, alarm in enumerate(alarms, 1):
        print(f"   Sending notification {i}/{len(alarms)}: {alarm.sensor_name} - {alarm.alarm_type}")
        try:
            manager.send_desktop_notification(
                alarm,
                f"Test alarm: {alarm.sensor_name} - {alarm.alarm_type}"
            )
            print(f"   [OK] Notification sent")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    print("\nIf you didn't see notifications:")
    if platform.system() == "Windows":
        print("  - Windows: Check Windows notification settings (Settings > System > Notifications)")
        print("  - Make sure win10toast is installed: pip install win10toast")
        print("  - The application must be running for PyQt5 system tray to work")
    else:
        print("  - Linux: Make sure 'notify-send' is installed (sudo apt-get install libnotify-bin)")
        print("  - The application must be running for PyQt5 system tray to work")
    print()
    
    return True

if __name__ == "__main__":
    try:
        test_desktop_notifications()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)










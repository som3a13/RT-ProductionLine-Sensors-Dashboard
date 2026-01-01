#!/usr/bin/env python3
"""
Test Webhook POST Script
Tests webhook notifications to a remote server

Author: Mohammed Ismail AbdElmageid
"""
import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from services.alarm_notifications import NotificationManager
from core.sensor_data import AlarmEvent


def test_webhook_notification():
    """Test webhook notification with sample alarm"""
    
    # Load config
    import json
    config_path = os.path.join(project_root, "config", "config.json")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return False
    
    # Check webhook configuration
    alarm_settings = config.get("alarm_settings", {})
    webhook_url = alarm_settings.get("webhook_url", "")
    
    print("=" * 60)
    print("Webhook Notification Test")
    print("=" * 60)
    print(f"Webhook URL: {webhook_url}")
    print("=" * 60)
    
    # Check if webhook is configured
    if not webhook_url:
        print("\n❌ Webhook URL not configured!")
        print("\nPlease configure webhook URL in config/config.json:")
        print('  "webhook_url": "https://your-server.com/webhook"')
        print("\nExample webhook URLs:")
        print("  - https://httpbin.org/post (for testing)")
        print("  - https://your-api.com/alarms")
        print("  - http://localhost:3000/webhook (local server)")
        return False
    
    # Enable notifications
    alarm_settings["enable_notifications"] = True
    
    # Create notification manager
    try:
        notification_manager = NotificationManager(config)
    except Exception as e:
        print(f"Error creating notification manager: {e}")
        return False
    
    # Create a test alarm
    test_alarm = AlarmEvent(
        timestamp=datetime.now(),
        sensor_name="Temperature Sensor 1 (TEST)",
        sensor_id=1,
        value=95.5,
        alarm_type="HIGH",
        unit="°C"
    )
    
    print("\n📡 Sending test webhook POST request...")
    print(f"   Alarm: {test_alarm.alarm_type} on {test_alarm.sensor_name}")
    print(f"   Value: {test_alarm.value:.2f} {test_alarm.unit}")
    print(f"   URL: {webhook_url}")
    print()
    
    # Send webhook notification
    try:
        success = notification_manager.send_webhook(test_alarm)
        
        if success:
            print("✅ Webhook POST request sent successfully!")
            print(f"   Check your server at: {webhook_url}")
            return True
        else:
            print("❌ Failed to send webhook POST request")
            print("   Check your webhook URL and server availability")
            return False
    except Exception as e:
        print(f"❌ Error sending webhook: {e}")
        print("\nCommon issues:")
        print("  - Invalid webhook URL")
        print("  - Server not reachable")
        print("  - Firewall blocking connection")
        print("  - SSL certificate issues (for HTTPS)")
        return False


if __name__ == "__main__":
    print("\n")
    success = test_webhook_notification()
    print("\n")
    sys.exit(0 if success else 1)


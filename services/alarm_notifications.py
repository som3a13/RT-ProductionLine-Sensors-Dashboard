"""
Alarm Notification System - Supports Webhook and Desktop notifications
"""
import json
import requests
from typing import Dict, Optional
from core.sensor_data import AlarmEvent
from PyQt5.QtWidgets import QSystemTrayIcon, QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, pyqtSignal


class NotificationManager(QObject):
    """Manages all alarm notifications"""
    notification_sent = pyqtSignal(str, bool)  # message, success
    
    def __init__(self, config: Dict):
        super().__init__()
        self.config = config.get("alarm_settings", {})
        self.enabled = self.config.get("enable_notifications", False)
        self.desktop_enabled = self.config.get("enable_desktop_notifications", True)
        self.webhook_url = self.config.get("webhook_url", "")
        
        # Desktop notifications - works on Linux and Windows
        self.tray_icon = None
        self.use_system_notify = False
        
        # Try PyQt5 system tray first (works on both Linux and Windows)
        # Note: Requires QApplication to be running
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None and QSystemTrayIcon.isSystemTrayAvailable():
                try:
                    self.tray_icon = QSystemTrayIcon()
                    # Set a default icon if available
                    self.tray_icon.show()
                except Exception as e:
                    print(f"System tray initialization error: {e}")
        except Exception as e:
            # QApplication not available yet, will use fallback
            pass
        
        # Fallback: Check for Linux notify-send command
        if not self.tray_icon:
            import shutil
            if shutil.which("notify-send"):
                self.use_system_notify = True
                print("Using Linux notify-send for desktop notifications")
    
    def send_notification(self, alarm: AlarmEvent):
        """Send all enabled notifications for an alarm"""
        message = self._format_alarm_message(alarm)
        success_count = 0
        
        # Desktop notification (always enabled if system supports it, independent of other notifications)
        if self.desktop_enabled:
            self.send_desktop_notification(alarm, message)
        
        # Other notifications only if enabled
        if not self.enabled:
            return
        
        # Webhook POST
        if self.webhook_url:
            if self.send_webhook(alarm):
                success_count += 1
        
        self.notification_sent.emit(f"Sent {success_count} notification(s)", True)
    
    def _format_alarm_message(self, alarm: AlarmEvent) -> str:
        """Format alarm message"""
        return (f"ALARM: {alarm.alarm_type}\n"
                f"Sensor: {alarm.sensor_name}\n"
                f"Value: {alarm.value:.2f} {alarm.unit}\n"
                f"Time: {alarm.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def send_webhook(self, alarm: AlarmEvent) -> bool:
        """Send webhook POST notification"""
        try:
            payload = {
                "event_type": "alarm",
                "timestamp": alarm.timestamp.isoformat(),
                "sensor_id": alarm.sensor_id,
                "sensor_name": alarm.sensor_name,
                "value": alarm.value,
                "alarm_type": alarm.alarm_type,
                "unit": alarm.unit
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=5
            )
            return response.status_code in [200, 201, 202]
        except Exception as e:
            print(f"Webhook notification error: {e}")
            return False
    
    def send_desktop_notification(self, alarm: AlarmEvent, message: str):
        """Send desktop notification - works on Linux Ubuntu and Windows"""
        try:
            # Method 1: PyQt5 System Tray (works on both Linux and Windows)
            # Try to get/create tray icon if not already available
            if not self.tray_icon:
                try:
                    from PyQt5.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app is not None and QSystemTrayIcon.isSystemTrayAvailable():
                        self.tray_icon = QSystemTrayIcon()
                        self.tray_icon.show()
                except Exception:
                    pass
            
            if self.tray_icon:
                self.tray_icon.showMessage(
                    f"🚨 ALARM: {alarm.sensor_name}",
                    f"{alarm.alarm_type} Alarm - Value: {alarm.value:.2f} {alarm.unit}\n"
                    f"Time: {alarm.timestamp.strftime('%H:%M:%S')}",
                    QSystemTrayIcon.Critical,
                    5000  # 5 seconds
                )
                return
            
            # Method 2: Linux notify-send (fallback for Linux)
            if self.use_system_notify:
                import subprocess
                title = f"🚨 ALARM: {alarm.sensor_name}"
                body = f"{alarm.alarm_type} Alarm\nValue: {alarm.value:.2f} {alarm.unit}\nTime: {alarm.timestamp.strftime('%H:%M:%S')}"
                
                # Use urgency=critical for alarms
                subprocess.run([
                    "notify-send",
                    "--urgency=critical",
                    "--expire-time=5000",
                    "--icon=error",
                    title,
                    body
                ], check=False)
                return
            
            # Method 3: Windows toast notification (if available)
            try:
                import platform
                if platform.system() == "Windows":
                    try:
                        from win10toast import ToastNotifier
                        toaster = ToastNotifier()
                        toaster.show_toast(
                            f"🚨 ALARM: {alarm.sensor_name}",
                            f"{alarm.alarm_type} Alarm - Value: {alarm.value:.2f} {alarm.unit}",
                            duration=5,
                            threaded=True
                        )
                        return
                    except ImportError:
                        pass
            except Exception:
                pass
            
            # If all methods fail, print to console
            print(f"⚠️ DESKTOP NOTIFICATION: {message}")
            
        except Exception as e:
            print(f"Desktop notification error: {e}")
            # Fallback: print to console
            print(f"⚠️ ALARM: {alarm.sensor_name} - {alarm.alarm_type} - {alarm.value:.2f} {alarm.unit}")


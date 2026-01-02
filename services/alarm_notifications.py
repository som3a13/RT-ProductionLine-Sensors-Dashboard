"""
Alarm Notification System - Supports Webhook and Desktop notifications

Author: Mohammed Ismail AbdElmageid

Dependencies:
- PyQt5: System tray notifications (works on both Linux and Windows)
- win10toast: Windows toast notifications (Windows only, installed via requirements.txt)
- notify-send: Linux desktop notifications (system command, not a Python package)
  - Ubuntu/Debian: sudo apt-get install libnotify-bin
  - RedHat/CentOS: sudo yum install libnotify

Notification Methods (in order of preference):
1. PyQt5 System Tray - Works on both Linux and Windows
2. Platform-specific fallback:
   - Windows: win10toast (if available)
   - Linux: notify-send (if available)
3. Console fallback - Prints to console if all methods fail

Webhook Implementation:
- Webhooks are sent in background threads to prevent GUI freezing
- Works on both Windows and Linux without blocking the main thread
"""
import json
import platform
import requests
import threading
import warnings
from typing import Dict, Optional
from core.sensor_data import AlarmEvent
from PyQt5.QtWidgets import QSystemTrayIcon, QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, pyqtSignal

# Suppress win10toast deprecation warning (it's a library issue, not our code)
warnings.filterwarnings('ignore', category=UserWarning, module='win10toast')


class NotificationManager(QObject):
    """Manages all alarm notifications"""
    notification_sent = pyqtSignal(str, bool)  # message, success
    
    def __init__(self, config: Dict):
        super().__init__()
        self.config = config.get("alarm_settings", {})
        self.enabled = self.config.get("enable_notifications", False)
        self.desktop_enabled = self.config.get("enable_desktop_notifications", True)
        self.webhook_url = self.config.get("webhook_url", "")
        
        # Detect platform
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        
        # Thread lock for thread-safe webhook sending
        self._webhook_lock = threading.Lock()
        
        # Desktop notifications - works on Linux and Windows
        self.tray_icon = None
        self.use_system_notify = False
        self.win10toast_available = False
        self.toaster = None
        self.icon_path = None
        
        # Try to find fav.png icon for tray icon
        try:
            from pathlib import Path
            # Try to find fav.png in project root
            script_dir = Path(__file__).parent
            project_root = script_dir.parent
            icon_path = project_root / 'fav.png'
            if icon_path.exists():
                self.icon_path = str(icon_path)
        except Exception:
            pass
        
        # Platform-specific fallback initialization (do this first for Windows)
        if self.is_windows:
            # Windows: Try win10toast as primary method (more reliable on Windows)
            try:
                # Suppress deprecation warning when importing win10toast
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=UserWarning, module='win10toast')
                    from win10toast import ToastNotifier
                
                self.toaster = ToastNotifier()
                self.win10toast_available = True
                print("Windows toast notifications (win10toast) initialized")
            except ImportError:
                print("Warning: win10toast not available. Install with: pip install win10toast")
                self.win10toast_available = False
            except Exception as e:
                print(f"Warning: win10toast initialization error: {e}")
                self.win10toast_available = False
        elif self.is_linux:
            # Linux: Check for notify-send command
            import shutil
            if shutil.which("notify-send"):
                self.use_system_notify = True
                print("Using Linux notify-send for desktop notifications")
        
        # Try PyQt5 system tray as secondary method (works on both Linux and Windows)
        # Note: Requires QApplication to be running
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtGui import QIcon
            app = QApplication.instance()
            if app is not None and QSystemTrayIcon.isSystemTrayAvailable():
                try:
                    self.tray_icon = QSystemTrayIcon()
                    # Priority 1: Use fav.png if available
                    if self.icon_path:
                        try:
                            icon = QIcon(self.icon_path)
                            if not icon.isNull():
                                self.tray_icon.setIcon(icon)
                                self.tray_icon.show()
                                print("PyQt5 system tray icon initialized with fav.png")
                        except Exception as e:
                            print(f"Error loading fav.png for tray icon: {e}")
                    
                    # Priority 2: Try app icon if fav.png failed
                    if self.tray_icon.icon().isNull():
                        app_icon = app.windowIcon()
                        if not app_icon.isNull():
                            self.tray_icon.setIcon(app_icon)
                            self.tray_icon.show()
                            print("PyQt5 system tray icon initialized with app icon")
                        else:
                            self.tray_icon = None  # Can't use without icon
                            print("Warning: No icon available for system tray")
                except Exception as e:
                    print(f"System tray initialization error: {e}")
                    self.tray_icon = None
        except Exception as e:
            # QApplication not available yet, will use fallback
            pass
    
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
        """Send webhook POST notification (blocking - use send_webhook_async for non-blocking)"""
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
    
    def send_webhook_async(self, alarm: AlarmEvent):
        """Send webhook POST notification in a background thread (non-blocking)
        
        This method prevents GUI freezing by running the network request
        in a separate daemon thread. Use this instead of send_webhook()
        when called from the GUI thread.
        """
        if not self.webhook_url:
            return
        
        def _send_in_thread():
            """Internal function to send webhook in background thread"""
            try:
                with self._webhook_lock:  # Thread-safe
                    success = self.send_webhook(alarm)
                    if success:
                        print(f"Webhook sent successfully for alarm: {alarm.sensor_name}")
                    else:
                        print(f"Webhook failed for alarm: {alarm.sensor_name}")
            except Exception as e:
                print(f"Error in webhook thread: {e}")
        
        # Start webhook in background thread (daemon thread won't block app shutdown)
        thread = threading.Thread(target=_send_in_thread, daemon=True)
        thread.start()
    
    def send_desktop_notification(self, alarm: AlarmEvent, message: str):
        """Send desktop notification - works on Linux Ubuntu and Windows"""
        try:
            # On Windows, prefer win10toast (more reliable)
            if self.is_windows:
                if self.win10toast_available and self.toaster:
                    try:
                        self.toaster.show_toast(
                            f"ALARM: {alarm.sensor_name}",
                            f"{alarm.alarm_type} Alarm - Value: {alarm.value:.2f} {alarm.unit}",
                            duration=5,
                            threaded=True
                        )
                        return
                    except Exception as e:
                        print(f"Windows toast notification error: {e}")
                        # Fall through to PyQt5 tray icon
            
            # Method 1: PyQt5 System Tray (works on both Linux and Windows)
            # Try to get/create tray icon if not already available
            if not self.tray_icon:
                try:
                    from PyQt5.QtWidgets import QApplication
                    from PyQt5.QtGui import QIcon
                    app = QApplication.instance()
                    if app is not None and QSystemTrayIcon.isSystemTrayAvailable():
                        self.tray_icon = QSystemTrayIcon()
                        # Priority 1: Use fav.png if available
                        if self.icon_path:
                            try:
                                icon = QIcon(self.icon_path)
                                if not icon.isNull():
                                    self.tray_icon.setIcon(icon)
                            except Exception:
                                pass
                        # Priority 2: Try app icon if fav.png failed
                        if self.tray_icon.icon().isNull():
                            app_icon = app.windowIcon()
                            if not app_icon.isNull():
                                self.tray_icon.setIcon(app_icon)
                        # Only show if icon is set
                        if not self.tray_icon.icon().isNull():
                            self.tray_icon.show()
                except Exception as e:
                    print(f"Error creating tray icon: {e}")
            
            if self.tray_icon and not self.tray_icon.icon().isNull():
                try:
                    # Use QTimer to ensure showMessage is called from main thread
                    # This prevents WNDPROC errors on Windows
                    from PyQt5.QtCore import QTimer
                    def show_notification():
                        try:
                            if self.tray_icon and not self.tray_icon.icon().isNull():
                                self.tray_icon.showMessage(
                                    f"ALARM: {alarm.sensor_name}",
                                    f"{alarm.alarm_type} Alarm - Value: {alarm.value:.2f} {alarm.unit}\n"
                                    f"Time: {alarm.timestamp.strftime('%H:%M:%S')}",
                                    QSystemTrayIcon.Critical,
                                    5000  # 5 seconds
                                )
                        except Exception as e:
                            print(f"Tray icon notification error: {e}")
                    # Schedule in main thread (thread-safe)
                    QTimer.singleShot(0, show_notification)
                    return
                except Exception as e:
                    print(f"Tray icon notification error: {e}")
            
            # Method 2: Platform-specific fallbacks (if PyQt5 failed)
            if self.is_windows:
                # Windows: Try win10toast again if PyQt5 failed
                if self.win10toast_available and self.toaster:
                    try:
                        self.toaster.show_toast(
                            f"ALARM: {alarm.sensor_name}",
                            f"{alarm.alarm_type} Alarm - Value: {alarm.value:.2f} {alarm.unit}",
                            duration=5,
                            threaded=True
                        )
                        return
                    except Exception as e:
                        print(f"Windows toast notification error (fallback): {e}")
            
            elif self.is_linux:
                # Linux: Use notify-send (if available)
                if self.use_system_notify:
                    import subprocess
                    title = f"ALARM: {alarm.sensor_name}"
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
            
            # If all methods fail, print to console
            print(f"DESKTOP NOTIFICATION: {message}")
            
        except Exception as e:
            print(f"Desktop notification error: {e}")
            # Fallback: print to console
            print(f"ALARM: {alarm.sensor_name} - {alarm.alarm_type} - {alarm.value:.2f} {alarm.unit}")


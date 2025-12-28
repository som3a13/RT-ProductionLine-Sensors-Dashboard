"""
Main GUI Application - Production Line Monitoring System
"""
import sys
import json
from datetime import datetime
from typing import Dict, List
from collections import deque

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QLabel, QPushButton, QTabWidget, QTextEdit,
                             QHeaderView, QStatusBar, QMessageBox, QGridLayout)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QMetaObject
from PyQt5.QtGui import QColor, QFont

from .metric_card import MetricCard

import pyqtgraph as pg

from sensors.sensor_manager import SensorManager
from core.sensor_data import SensorReading, SensorStatus, SensorConfig, AlarmEvent
from services.alarm_notifications import NotificationManager
from services.remote_console import RemoteConsoleServer
import asyncio
import threading


class AlarmClearHelper(QObject):
    """Helper class for thread-safe alarm clearing"""
    clear_requested = pyqtSignal()
    
    def __init__(self, target_method):
        super().__init__()
        self.clear_requested.connect(target_method)


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Si-Ware Production Line Monitoring System")
        self.setGeometry(100, 100, 1400, 900)
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize sensor data storage
        self.sensor_readings: Dict[int, SensorReading] = {}
        self.sensor_history: Dict[int, deque] = {}
        self.alarm_log: List[AlarmEvent] = []
        self.max_history_points = 100
        
        # Initialize sensor configurations
        self.sensor_configs: Dict[int, SensorConfig] = {}
        for sensor_config in self.config["sensors"]:
            config = SensorConfig(
                name=sensor_config["name"],
                sensor_id=sensor_config["id"],
                low_limit=sensor_config["low_limit"],
                high_limit=sensor_config["high_limit"],
                unit=sensor_config.get("unit", "")
            )
            self.sensor_configs[sensor_config["id"]] = config
            self.sensor_history[sensor_config["id"]] = deque(maxlen=self.max_history_points)
        
        # Initialize unified sensor manager (handles all protocols with worker threads)
        self.sensor_manager = SensorManager()
        
        # Add sensors with their protocols
        for sensor_config in self.config["sensors"]:
            sensor_id = sensor_config["id"]
            protocol = sensor_config.get("protocol", "tcp")
            protocol_config = sensor_config.get("protocol_config", {})
            
            self.sensor_manager.add_sensor(
                sensor_id=sensor_id,
                config=self.sensor_configs[sensor_id],
                protocol=protocol,
                protocol_config=protocol_config
            )
        
        # Connect signals (thread-safe communication - signals are handled in GUI thread)
        self.sensor_manager.sensor_reading_received.connect(self.on_sensor_reading)
        self.sensor_manager.alarm_triggered.connect(self.on_alarm_triggered)
        
        # Initialize notification manager
        self.notification_manager = NotificationManager(self.config)
        # Connect alarm signal to notification manager
        self.sensor_manager.alarm_triggered.connect(self.notification_manager.send_notification)
        
        # Create helper for thread-safe alarm clearing from remote console
        self.alarm_clear_helper = AlarmClearHelper(self._do_clear_alarm_log)
        
        # Initialize remote console server
        self.remote_console = None
        self.console_thread = None
        self.console_loop = None
        self.console_started = False
        self.http_server = None
        self.http_thread = None
        self.start_remote_console()
        self.start_http_server()
        
        # Setup UI
        self.setup_ui()
        
        # Setup update timer
        update_rate = self.config.get("update_rate", 0.5)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(int(update_rate * 1000))  # Convert to milliseconds
        
        # Connect to sensors
        self.connect_to_sensors()
        
        # Update remote console with initial sensor data after a short delay
        QTimer.singleShot(1000, self.update_remote_console_initial)
        
        # System status
        self.system_status = "OK"
        
        # Initialize metric tracking
        self.metric_history = {
            'oee': deque(maxlen=100),
            'availability': deque(maxlen=100),
            'performance': deque(maxlen=100),
            'quality': deque(maxlen=100)
        }
    
    def load_config(self) -> dict:
        """Load configuration from config.json"""
        import os
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.json")
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            QMessageBox.warning(self, "Config Error", 
                              f"config.json not found at {config_path}. Using defaults.")
            return {
                "sensors": [],
                "communication": {"host": "localhost", "port": 5000},
                "update_rate": 0.5
            }
    
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background-color: #f5f5f5;")  # Light gray background
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header with title and connection button
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Production Line Monitoring Dashboard")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Connection button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        # System status indicator (removed from header, but keep for compatibility)
        self.status_label = QLabel("System Status: OK")
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
        self.status_label.hide()  # Hide since we're using cards now
        header_layout.addWidget(self.connect_btn)
        
        layout.addLayout(header_layout)
        
        # Tab widget
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #f5f5f5;
            }
            QTabBar::tab {
                background-color: white;
                padding: 10px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #f5f5f5;
                border-bottom: 2px solid #2196F3;
            }
        """)
        
        # Dashboard tab
        dashboard_tab = self.create_dashboard_tab()
        tabs.addTab(dashboard_tab, "Dashboard")
        
        # Alarm log tab
        alarm_tab = self.create_alarm_log_tab()
        tabs.addTab(alarm_tab, "Alarm Log")
        
        # System Tools tab
        tools_tab = self.create_system_tools_tab()
        tabs.addTab(tools_tab, "System Tools")
        
        layout.addWidget(tabs)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def create_dashboard_tab(self) -> QWidget:
        """Create the main dashboard tab with modern metric cards"""
        widget = QWidget()
        widget.setStyleSheet("background-color: #f5f5f5;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Metric cards row
        cards_layout = QGridLayout()
        cards_layout.setSpacing(20)
        
        # Create metric cards
        self.oee_card = MetricCard("OEE", color=QColor(255, 152, 0))  # Orange
        self.availability_card = MetricCard("Availability", color=QColor(76, 175, 80))  # Green
        self.performance_card = MetricCard("Performance", color=QColor(0, 188, 212))  # Teal
        self.quality_card = MetricCard("Quality", color=QColor(33, 150, 243))  # Blue
        
        cards_layout.addWidget(self.oee_card, 0, 0)
        cards_layout.addWidget(self.availability_card, 0, 1)
        cards_layout.addWidget(self.performance_card, 0, 2)
        cards_layout.addWidget(self.quality_card, 0, 3)
        
        layout.addLayout(cards_layout)
        
        # Sensor details table (below cards)
        details_label = QLabel("Sensor Details")
        details_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-top: 10px;")
        layout.addWidget(details_label)
        
        # Sensor table
        self.sensor_table = QTableWidget()
        self.sensor_table.setColumnCount(5)
        self.sensor_table.setHorizontalHeaderLabels([
            "Sensor Name", "Latest Value", "Timestamp", "Status", "Plot"
        ])
        self.sensor_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sensor_table.setRowCount(len(self.sensor_configs))
        self.sensor_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border-radius: 5px;
                border: 1px solid #e0e0e0;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 10px;
                font-weight: bold;
            }
        """)
        
        # Populate table with sensor configs
        row = 0
        for sensor_id, config in sorted(self.sensor_configs.items()):
            self.sensor_table.setItem(row, 0, QTableWidgetItem(config.name))
            self.sensor_table.setItem(row, 1, QTableWidgetItem("--"))
            self.sensor_table.setItem(row, 2, QTableWidgetItem("--"))
            self.sensor_table.setItem(row, 3, QTableWidgetItem("--"))
            
            # Create plot widget
            plot_widget = pg.PlotWidget()
            plot_widget.setBackground('w')
            plot_widget.setLabel('left', 'Value')
            plot_widget.setLabel('bottom', 'Time')
            plot_widget.setMouseEnabled(x=False, y=False)
            plot_widget.setMaximumHeight(150)
            plot_widget.setMinimumHeight(150)
            
            # Store plot widget reference
            plot_widget.setProperty("sensor_id", sensor_id)
            self.sensor_table.setCellWidget(row, 4, plot_widget)
            
            row += 1
        
        layout.addWidget(self.sensor_table)
        
        # Initialize metric values
        self.previous_metrics = {
            'oee': 74.0,
            'availability': 86.0,
            'performance': 87.0,
            'quality': 91.9
        }
        
        return widget
    
    def create_alarm_log_tab(self) -> QWidget:
        """Create the alarm log tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Alarm log table
        self.alarm_table = QTableWidget()
        self.alarm_table.setColumnCount(5)
        self.alarm_table.setHorizontalHeaderLabels([
            "Time", "Sensor Name", "Value", "Alarm Type", "Unit"
        ])
        self.alarm_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.alarm_table)
        
        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_alarm_log)
        layout.addWidget(clear_btn)
        
        return widget
    
    def create_system_tools_tab(self) -> QWidget:
        """Create the system tools tab with self-test and snapshot"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("System Tools")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        # Run Self-Test button
        self.test_btn = QPushButton("Run Self-Test")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.test_btn.clicked.connect(self.run_self_test)
        buttons_layout.addWidget(self.test_btn)
        
        # Get Snapshot button
        self.snapshot_btn = QPushButton("Get Snapshot")
        self.snapshot_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:pressed {
                background-color: #2E7D32;
            }
        """)
        self.snapshot_btn.clicked.connect(self.get_snapshot)
        buttons_layout.addWidget(self.snapshot_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Results display area
        results_label = QLabel("Results:")
        results_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-top: 20px;")
        layout.addWidget(results_label)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.results_text)
        
        # Clear button
        clear_btn = QPushButton("Clear Results")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        clear_btn.clicked.connect(lambda: self.results_text.clear())
        layout.addWidget(clear_btn)
        
        return widget
    
    def run_self_test(self):
        """Run system self-test"""
        self.results_text.clear()
        self.results_text.append("Running Self-Test...\n")
        self.results_text.append("=" * 60 + "\n")
        
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": []
        }
        
        # Test 1: Check sensor readings availability
        sensor_count = len(self.sensor_readings)
        sensor_test = {
            "name": "Sensor Readings",
            "status": "PASS" if sensor_count > 0 else "FAIL",
            "details": f"{sensor_count} sensors available"
        }
        test_results["tests"].append(sensor_test)
        
        # Test 2: Check each sensor
        for sensor_id, reading in self.sensor_readings.items():
            sensor_status_test = {
                "name": f"Sensor {sensor_id} ({reading.sensor_name})",
                "status": "PASS" if reading.status.value == "OK" else "WARN",
                "details": f"Value: {reading.value:.2f} {reading.unit}, Status: {reading.status.value}"
            }
            test_results["tests"].append(sensor_status_test)
        
        # Test 3: Check alarm log
        alarm_test = {
            "name": "Alarm Log",
            "status": "PASS",
            "details": f"{len(self.alarm_log)} alarms in log"
        }
        test_results["tests"].append(alarm_test)
        
        # Test 4: Check sensor manager connection status
        connection_status = self.sensor_manager.get_connection_status()
        connected_count = sum(1 for v in connection_status.values() if v)
        total_count = len(connection_status)
        connection_test = {
            "name": "Sensor Connections",
            "status": "PASS" if connected_count == total_count else "WARN",
            "details": f"{connected_count}/{total_count} connections active"
        }
        test_results["tests"].append(connection_test)
        
        # Calculate overall status
        all_passed = all(test["status"] == "PASS" for test in test_results["tests"])
        test_results["overall_status"] = "PASS" if all_passed else "WARN"
        test_results["total_tests"] = len(test_results["tests"])
        test_results["passed"] = sum(1 for test in test_results["tests"] if test["status"] == "PASS")
        test_results["failed"] = sum(1 for test in test_results["tests"] if test["status"] == "FAIL")
        test_results["warnings"] = sum(1 for test in test_results["tests"] if test["status"] == "WARN")
        
        # Display results
        self.results_text.append(f"Self-Test Results\n")
        self.results_text.append(f"Timestamp: {test_results['timestamp']}\n")
        self.results_text.append(f"Overall Status: {test_results['overall_status']}\n")
        self.results_text.append(f"Total Tests: {test_results['total_tests']}\n")
        self.results_text.append(f"Passed: {test_results['passed']}, Failed: {test_results['failed']}, Warnings: {test_results['warnings']}\n")
        self.results_text.append("\n" + "=" * 60 + "\n")
        self.results_text.append("Test Details:\n")
        self.results_text.append("-" * 60 + "\n")
        
        for test in test_results["tests"]:
            status_icon = "✓" if test["status"] == "PASS" else "⚠" if test["status"] == "WARN" else "✗"
            self.results_text.append(f"{status_icon} {test['name']}: {test['status']}\n")
            self.results_text.append(f"   {test['details']}\n")
            self.results_text.append("\n")
        
        self.results_text.append("=" * 60 + "\n")
        self.results_text.append("Self-Test Complete\n")
        
        # Show status bar message
        if test_results["overall_status"] == "PASS":
            self.statusBar().showMessage("Self-Test: PASSED", 5000)
        else:
            self.statusBar().showMessage("Self-Test: WARNINGS DETECTED", 5000)
    
    def get_snapshot(self):
        """Get detailed system snapshot"""
        self.results_text.clear()
        self.results_text.append("Generating System Snapshot...\n")
        self.results_text.append("=" * 60 + "\n")
        
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "system_status": {
                "sensor_count": len(self.sensor_readings),
                "alarm_count": len(self.alarm_log),
            },
            "sensors": []
        }
        
        # Get connection status
        connection_status = self.sensor_manager.get_connection_status()
        snapshot["system_status"]["connections"] = {
            "connected": sum(1 for v in connection_status.values() if v),
            "total": len(connection_status)
        }
        
        # Detailed sensor information
        for sensor_id, reading in self.sensor_readings.items():
            sensor_detail = {
                "id": reading.sensor_id,
                "name": reading.sensor_name,
                "value": reading.value,
                "status": reading.status.value,
                "unit": reading.unit,
                "timestamp": reading.timestamp.isoformat(),
                "is_alarm": reading.status.value in ["LOW Alarm", "HIGH Alarm", "Faulty Sensor"]
            }
            snapshot["sensors"].append(sensor_detail)
        
        # Recent alarms (last 10)
        snapshot["recent_alarms"] = []
        for alarm in self.alarm_log[-10:]:
            snapshot["recent_alarms"].append({
                "timestamp": alarm.timestamp.isoformat(),
                "sensor_id": alarm.sensor_id,
                "sensor_name": alarm.sensor_name,
                "alarm_type": alarm.alarm_type,
                "value": alarm.value,
                "unit": alarm.unit
            })
        
        # System health summary
        healthy_sensors = sum(1 for r in self.sensor_readings.values() if r.status.value == "OK")
        alarm_sensors = sum(1 for r in self.sensor_readings.values() if "Alarm" in r.status.value)
        faulty_sensors = sum(1 for r in self.sensor_readings.values() if r.status.value == "Faulty Sensor")
        
        snapshot["health_summary"] = {
            "healthy": healthy_sensors,
            "alarms": alarm_sensors,
            "faulty": faulty_sensors,
            "total": len(self.sensor_readings)
        }
        
        # Display snapshot
        self.results_text.append("System Snapshot\n")
        self.results_text.append(f"Timestamp: {snapshot['timestamp']}\n")
        self.results_text.append("\n" + "=" * 60 + "\n")
        self.results_text.append("System Status:\n")
        self.results_text.append(f"  Sensors: {snapshot['system_status']['sensor_count']}\n")
        self.results_text.append(f"  Alarms: {snapshot['system_status']['alarm_count']}\n")
        self.results_text.append(f"  Connections: {snapshot['system_status']['connections']['connected']}/{snapshot['system_status']['connections']['total']}\n")
        self.results_text.append("\n" + "-" * 60 + "\n")
        self.results_text.append("Health Summary:\n")
        self.results_text.append(f"  Healthy: {snapshot['health_summary']['healthy']}\n")
        self.results_text.append(f"  Alarms: {snapshot['health_summary']['alarms']}\n")
        self.results_text.append(f"  Faulty: {snapshot['health_summary']['faulty']}\n")
        self.results_text.append(f"  Total: {snapshot['health_summary']['total']}\n")
        self.results_text.append("\n" + "-" * 60 + "\n")
        self.results_text.append("Sensors:\n")
        
        for sensor in snapshot["sensors"]:
            status_icon = "✓" if sensor["status"] == "OK" else "⚠" if "Alarm" in sensor["status"] else "✗"
            self.results_text.append(f"{status_icon} {sensor['name']} (ID: {sensor['id']})\n")
            self.results_text.append(f"   Value: {sensor['value']:.2f} {sensor['unit']}\n")
            self.results_text.append(f"   Status: {sensor['status']}\n")
            self.results_text.append(f"   Timestamp: {sensor['timestamp']}\n")
            self.results_text.append("\n")
        
        if snapshot["recent_alarms"]:
            self.results_text.append("-" * 60 + "\n")
            self.results_text.append("Recent Alarms (Last 10):\n")
            for alarm in snapshot["recent_alarms"]:
                self.results_text.append(f"  [{alarm['timestamp']}] {alarm['sensor_name']}\n")
                self.results_text.append(f"    Type: {alarm['alarm_type']}, Value: {alarm['value']:.2f} {alarm['unit']}\n")
                self.results_text.append("\n")
        
        self.results_text.append("=" * 60 + "\n")
        self.results_text.append("Snapshot Complete\n")
        
        self.statusBar().showMessage("System snapshot generated", 3000)
    
    def connect_to_sensors(self):
        """Connect to all sensor communicators"""
        results = self.sensor_manager.connect_all()
        
        connected = sum(1 for v in results.values() if v)
        total = len(results)
        
        if connected > 0:
            self.statusBar().showMessage(f"Connected to {connected}/{total} communication channels")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("background-color: red;")
            
            # Show details
            status_details = []
            for key, status in results.items():
                status_details.append(f"{key}: {'✓' if status else '✗'}")
            
            if connected < total:
                QMessageBox.warning(self, "Partial Connection",
                                  f"Connected to {connected}/{total} channels:\n" + 
                                  "\n".join(status_details))
        else:
            self.statusBar().showMessage("Failed to connect to sensors")
            QMessageBox.warning(self, "Connection Error",
                              "Could not connect to any sensor communication channels.\n"
                              "Make sure the sensor simulators are running.")
    
    def toggle_connection(self):
        """Toggle connection to sensors"""
        status = self.sensor_manager.get_connection_status()
        if any(status.values()):
            self.sensor_manager.disconnect_all()
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.statusBar().showMessage("Disconnected")
        else:
            self.connect_to_sensors()
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
    
    def on_sensor_reading(self, reading: SensorReading):
        """Handle new sensor reading"""
        self.sensor_readings[reading.sensor_id] = reading
        
        # Update remote console
        if self.remote_console and self.console_loop:
            self.remote_console.set_sensor_readings(self.sensor_readings)
            # Broadcast update via WebSocket
            try:
                asyncio.run_coroutine_threadsafe(
                    self.remote_console.broadcast_sensor_update(reading),
                    self.console_loop
                )
            except Exception as e:
                print(f"Error broadcasting sensor update: {e}")
        
        # Add to history
        if reading.sensor_id in self.sensor_history:
            self.sensor_history[reading.sensor_id].append(reading.value)
    
    def on_alarm_triggered(self, alarm: AlarmEvent):
        """Handle alarm event"""
        self.alarm_log.append(alarm)
        
        # Update remote console
        if self.remote_console and self.console_loop:
            self.remote_console.add_alarm(alarm)
            # Broadcast alarm via WebSocket
            try:
                asyncio.run_coroutine_threadsafe(
                    self.remote_console.broadcast_alarm(alarm),
                    self.console_loop
                )
            except Exception as e:
                print(f"Error broadcasting alarm: {e}")
        
        # Update alarm log table
        row = self.alarm_table.rowCount()
        self.alarm_table.insertRow(row)
        
        self.alarm_table.setItem(row, 0, QTableWidgetItem(
            alarm.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ))
        self.alarm_table.setItem(row, 1, QTableWidgetItem(alarm.sensor_name))
        self.alarm_table.setItem(row, 2, QTableWidgetItem(f"{alarm.value:.2f}"))
        self.alarm_table.setItem(row, 3, QTableWidgetItem(alarm.alarm_type))
        self.alarm_table.setItem(row, 4, QTableWidgetItem(alarm.unit))
        
        # Scroll to bottom
        self.alarm_table.scrollToBottom()
    
    def calculate_metrics(self):
        """Calculate OEE metrics from sensor data"""
        # Calculate based on sensor readings
        total_sensors = len(self.sensor_configs)
        if total_sensors == 0:
            return {
                'oee': 94.0,
                'availability': 100.0,
                'performance': 94.0,
                'quality': 100.0
            }
        
        # Count sensors in different states
        ok_count = 0
        alarm_count = 0
        faulty_count = 0
        
        for sensor_id, reading in self.sensor_readings.items():
            if reading.status == SensorStatus.OK:
                ok_count += 1
            elif reading.status in [SensorStatus.LOW_ALARM, SensorStatus.HIGH_ALARM]:
                alarm_count += 1
            elif reading.status == SensorStatus.FAULTY:
                faulty_count += 1
        
        # Availability: percentage of sensors that are OK or in alarm (not faulty)
        availability = ((ok_count + alarm_count) / total_sensors * 100) if total_sensors > 0 else 100.0
        
        # Performance: based on how many sensors are within optimal range
        # For simplicity, use OK sensors as performance indicator
        performance = (ok_count / total_sensors * 100) if total_sensors > 0 else 94.0
        
        # Quality: inverse of alarm rate (simplified)
        quality = ((ok_count) / total_sensors * 100) if total_sensors > 0 else 100.0
        
        # OEE = Availability × Performance × Quality / 10000
        oee = (availability * performance * quality) / 10000
        
        return {
            'oee': min(100.0, max(0.0, oee)),
            'availability': min(100.0, max(0.0, availability)),
            'performance': min(100.0, max(0.0, performance)),
            'quality': min(100.0, max(0.0, quality))
        }
    
    def update_display(self):
        """Update the display with latest sensor data"""
        # Calculate and update metrics
        metrics = self.calculate_metrics()
        
        # Update metric cards
        self.oee_card.set_value(metrics['oee'])
        self.availability_card.set_value(metrics['availability'])
        self.performance_card.set_value(metrics['performance'])
        self.quality_card.set_value(metrics['quality'])
        
        # Calculate trends (change from previous)
        oee_trend = metrics['oee'] - self.previous_metrics['oee']
        availability_trend = metrics['availability'] - self.previous_metrics['availability']
        performance_trend = metrics['performance'] - self.previous_metrics['performance']
        quality_trend = metrics['quality'] - self.previous_metrics['quality']
        
        self.oee_card.set_trend(oee_trend)
        self.availability_card.set_trend(availability_trend)
        self.performance_card.set_trend(performance_trend)
        self.quality_card.set_trend(quality_trend)
        
        # Store current metrics for next trend calculation
        self.previous_metrics = metrics.copy()
        
        # Update sensor table
        row = 0
        has_alarm = False
        
        for sensor_id, config in sorted(self.sensor_configs.items()):
            reading = self.sensor_readings.get(sensor_id)
            
            if reading:
                # Update value
                value_item = QTableWidgetItem(f"{reading.value:.2f} {config.unit}")
                self.sensor_table.setItem(row, 1, value_item)
                
                # Update timestamp
                time_str = reading.timestamp.strftime("%H:%M:%S")
                self.sensor_table.setItem(row, 2, QTableWidgetItem(time_str))
                
                # Update status with color coding
                status_item = QTableWidgetItem(reading.status.value)
                if reading.status == SensorStatus.OK:
                    status_item.setBackground(QColor(144, 238, 144))  # Light green
                elif reading.status == SensorStatus.FAULTY:
                    status_item.setBackground(QColor(255, 192, 203))  # Light pink
                    has_alarm = True
                elif reading.status == SensorStatus.LOW_ALARM:
                    status_item.setBackground(QColor(255, 165, 0))  # Orange
                    has_alarm = True
                elif reading.status == SensorStatus.HIGH_ALARM:
                    status_item.setBackground(QColor(255, 0, 0))  # Red
                    has_alarm = True
                self.sensor_table.setItem(row, 3, status_item)
                
                # Highlight row if alarm
                if reading.status in [SensorStatus.LOW_ALARM, SensorStatus.HIGH_ALARM, SensorStatus.FAULTY]:
                    for col in range(5):
                        item = self.sensor_table.item(row, col)
                        if item:
                            item.setBackground(QColor(255, 200, 200))  # Light red
                
                # Update plot
                plot_widget = self.sensor_table.cellWidget(row, 4)
                if plot_widget and sensor_id in self.sensor_history:
                    history = list(self.sensor_history[sensor_id])
                    if history:
                        plot_widget.clear()
                        plot_widget.plot(history, pen=pg.mkPen(color='b', width=2))
                        plot_widget.setYRange(
                            min(history) * 0.9 if history else 0,
                            max(history) * 1.1 if history else 100
                        )
            else:
                # No data yet
                self.sensor_table.setItem(row, 1, QTableWidgetItem("--"))
                self.sensor_table.setItem(row, 2, QTableWidgetItem("--"))
                self.sensor_table.setItem(row, 3, QTableWidgetItem("Waiting..."))
            
            row += 1
        
        # Update system status
        if has_alarm:
            self.system_status = "ALARM"
            self.status_label.setText("System Status: ALARM")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")
        else:
            self.system_status = "OK"
            self.status_label.setText("System Status: OK")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
    
    def clear_alarm_log(self):
        """Clear the alarm log (called from GUI button)"""
        self.alarm_table.setRowCount(0)
        self.alarm_log.clear()
        if self.remote_console:
            self.remote_console.alarm_log.clear()
    
    def clear_alarm_log_from_remote(self):
        """Clear the alarm log (called from remote console - thread-safe)"""
        # This method is called from the remote console's asyncio thread
        # Emit signal to execute in GUI thread (thread-safe)
        self.alarm_clear_helper.clear_requested.emit()
    
    def _do_clear_alarm_log(self):
        """Actually clear the alarm log (executed in GUI thread)"""
        self.alarm_table.setRowCount(0)
        self.alarm_log.clear()
        # Note: remote console alarm log is already cleared by handle_clear_alarms
    
    def start_remote_console(self):
        """Start the remote console server in a separate thread"""
        try:
            console_config = self.config.get("remote_console", {})
            if not console_config.get("enabled", True):
                print("Remote console is disabled in config.json")
                return
            
            host = console_config.get("host", "localhost")
            port = console_config.get("port", 8765)
            users = console_config.get("users", None)
            
            print(f"Starting Remote Console Server on ws://{host}:{port}...")
            self.remote_console = RemoteConsoleServer(host=host, port=port, users=users)
            
            def run_console():
                self.console_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.console_loop)
                try:
                    # Give the server a moment to initialize
                    import time
                    time.sleep(0.5)
                    self.console_loop.run_until_complete(self.remote_console.start())
                except Exception as e:
                    print(f"Remote console error: {e}")
                    import traceback
                    traceback.print_exc()
                    self.console_started = False
                finally:
                    self.console_started = False
            
            self.console_thread = threading.Thread(target=run_console, daemon=True)
            self.console_thread.start()
            
            # Give thread a moment to start
            import time
            time.sleep(0.2)
            
            # Initialize remote console with current sensor readings
            if self.remote_console:
                self.remote_console.set_sensor_readings(self.sensor_readings)
                # Set callback to clear alarms in main GUI from remote console
                self.remote_console.set_clear_alarms_callback(self.clear_alarm_log_from_remote)
                self.console_started = True
                http_port = console_config.get("http_port", 8080)
                print(f"✓ Remote Console Server started successfully on ws://{host}:{port}")
                print(f"  Connect from web client at: http://localhost:{http_port}/web/remote_console_client.html")
            else:
                print("✗ Failed to initialize Remote Console Server")
        except Exception as e:
            print(f"Failed to start remote console: {e}")
            import traceback
            traceback.print_exc()
            self.remote_console = None
            self.console_started = False
    
    def start_http_server(self):
        """Start HTTP server to serve remote console client HTML"""
        try:
            console_config = self.config.get("remote_console", {})
            if not console_config.get("enabled", True):
                return
            
            import http.server
            import socketserver
            import os
            
            # HTTP server port (default 8080)
            http_port = console_config.get("http_port", 8080)
            
            # Get project root directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            
            # Get WebSocket URL from config
            ws_host = console_config.get("host", "localhost")
            ws_port = console_config.get("port", 8765)
            ws_url = f"ws://{ws_host}:{ws_port}"
            
            class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
                """Custom HTTP request handler"""
                
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=project_root, **kwargs)
                
                def end_headers(self):
                    # Add CORS headers
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    super().end_headers()
                
                def log_message(self, format, *args):
                    # Suppress default logging for favicon and other common requests
                    if 'favicon.ico' not in format % args:
                        # Only log important requests
                        pass
                
                def do_GET(self):
                    """Handle GET requests"""
                    # Handle favicon requests gracefully
                    if self.path == '/favicon.ico':
                        self.send_response(204)  # No Content
                        self.end_headers()
                        return
                    
                    # Inject WebSocket URL into HTML file
                    if self.path == '/web/remote_console_client.html' or self.path == '/web/remote_console_client.html/':
                        try:
                            html_path = os.path.join(project_root, 'web', 'remote_console_client.html')
                            with open(html_path, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            
                            # Replace hardcoded WebSocket URL with config value
                            # Find and replace the wsUrl line (handles both single and double quotes)
                            import re
                            # Match both single and double quotes
                            html_content = re.sub(
                                r'const wsUrl = ["\']ws://[^"\']+["\'];',
                                f'const wsUrl = "{ws_url}";',
                                html_content
                            )
                            
                            # Send the modified HTML
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html; charset=utf-8')
                            self.end_headers()
                            try:
                                self.wfile.write(html_content.encode('utf-8'))
                            except (BrokenPipeError, ConnectionResetError):
                                # Client disconnected before response completed - ignore
                                pass
                            return
                        except (BrokenPipeError, ConnectionResetError):
                            # Client disconnected - ignore
                            return
                        except Exception as e:
                            # Only log non-connection errors
                            if "Broken pipe" not in str(e) and "Connection reset" not in str(e):
                                print(f"Error serving HTML: {e}")
                            # Fall through to default handler
                    
                    # Serve other files normally
                    try:
                        super().do_GET()
                    except BrokenPipeError:
                        # Client disconnected, ignore
                        pass
                    except Exception as e:
                        # Log other errors but don't crash
                        pass
            
            def run_http_server():
                try:
                    with socketserver.TCPServer(("", http_port), MyHTTPRequestHandler) as httpd:
                        self.http_server = httpd
                        print(f"✓ HTTP Server started on http://localhost:{http_port}")
                        print(f"  Remote Console Client: http://localhost:{http_port}/web/remote_console_client.html")
                        httpd.serve_forever()
                except OSError as e:
                    if "Address already in use" in str(e):
                        print(f"⚠ HTTP port {http_port} is already in use. Remote console client may not be accessible.")
                        print(f"  Try accessing: http://localhost:{http_port}/web/remote_console_client.html")
                    else:
                        print(f"⚠ HTTP server error: {e}")
                except Exception as e:
                    print(f"⚠ HTTP server error: {e}")
            
            self.http_thread = threading.Thread(target=run_http_server, daemon=True)
            self.http_thread.start()
            
            # Give server a moment to start
            import time
            time.sleep(0.3)
            
        except Exception as e:
            print(f"Failed to start HTTP server: {e}")
            import traceback
            traceback.print_exc()
            self.http_server = None
    
    def update_remote_console_initial(self):
        """Update remote console with initial sensor data"""
        if self.remote_console:
            self.remote_console.set_sensor_readings(self.sensor_readings)
            print("Remote console initialized with sensor data")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.sensor_manager.disconnect_all()
        
        # Stop HTTP server
        if self.http_server:
            try:
                self.http_server.shutdown()
            except:
                pass
        
        # Stop remote console
        if self.remote_console and hasattr(self, 'console_loop') and self.console_loop:
            try:
                # Stop the event loop gracefully
                self.console_loop.call_soon_threadsafe(self.console_loop.stop)
            except:
                pass
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


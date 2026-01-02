"""
Main GUI Application - Production Line Monitoring System

Author: Mohammed Ismail AbdElmageid
"""
import sys
import json
import math
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from collections import deque

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QLabel, QPushButton, QTabWidget, QTextEdit,
                             QHeaderView, QStatusBar, QMessageBox, QGridLayout,
                             QScrollArea, QSplitter, QSizePolicy, QLineEdit,
                             QDialog, QDialogButtonBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QMetaObject, QSize, QBuffer, QIODevice
from PyQt5.QtGui import QColor, QFont, QIcon, QPixmap, QPainter

import pyqtgraph as pg

from sensors.sensor_manager import SensorManager
from core.sensor_data import SensorReading, SensorStatus, SensorConfig, AlarmEvent
from services.alarm_notifications import NotificationManager
from services.remote_console import RemoteConsoleServer
from gui.components import NonResizableSplitter, AlarmClearHelper
import asyncio
import threading


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Si-Ware Production Line Monitoring System")
        self.setGeometry(100, 100, 1400, 900)
        # Allow window to be resized
        self.setMinimumSize(800, 600)
        
        # Load configuration
        self.config = self.load_config()
        
        # Set application icon
        self.set_application_icon()
        
        # Load stylesheet
        self.apply_stylesheet()
        
        # Initialize sensor data storage
        self.sensor_readings: Dict[int, SensorReading] = {}
        self.sensor_history: Dict[int, deque] = {}  # Stores (timestamp, value) tuples
        self.sensor_timestamps: Dict[int, deque] = {}  # Separate timestamps for easier access
        self.alarm_log: List[AlarmEvent] = []
        # Track previous sensor status for notification transition detection
        self.previous_sensor_status: Dict[int, SensorStatus] = {}
        self.max_history_points = 100
        self.plot_start_time = datetime.now()  # Track when plotting started
        self.plot_time_window = 20  # Rolling window in seconds (10-20 seconds range)
        
        # Maintenance console authentication state
        self.maintenance_authenticated = False
        self.maintenance_user = None
        
        # Helper function to get defaults based on sensor type
        def get_defaults_for_type(sensor_type: str):
            """Get default values for sensor type"""
            defaults = {
                'flow': {'low': 10.0, 'high': 100.0, 'unit': 'L/min', 'name': 'Flow Rate'},
                'vibration': {'low': 0.0, 'high': 5.0, 'unit': 'mm/s', 'name': 'Vibration'},
                'temperature': {'low': 20.0, 'high': 80.0, 'unit': '°C', 'name': 'Temperature'},
                'pressure': {'low': 50.0, 'high': 150.0, 'unit': 'PSI', 'name': 'Pressure'},
                'voltage': {'low': 200.0, 'high': 240.0, 'unit': 'V', 'name': 'Voltage'},
                'speed': {'low': 0.0, 'high': 600.0, 'unit': 'RPM', 'name': 'Speed'},
                'optical': {'low': 50.0, 'high': 60.0, 'unit': '%', 'name': 'Optical'},
            }
            
            sensor_type_lower = sensor_type.lower()
            for key, value in defaults.items():
                if key in sensor_type_lower or sensor_type_lower in key:
                    return value
            
            # Default fallback
            return {'low': 0.0, 'high': 100.0, 'unit': '', 'name': 'Sensor'}
        
        # Initialize sensor configurations
        self.sensor_configs: Dict[int, SensorConfig] = {}
        for sensor_config in self.config["sensors"]:
            # Get sensor type from config or infer from name
            sensor_type = sensor_config.get("sensor_type", "").lower() or sensor_config.get("name", "").lower()
            
            # Get defaults based on sensor type
            defaults = get_defaults_for_type(sensor_type)
            
            # Use config values if provided, otherwise use defaults
            low_limit = sensor_config.get("low_limit")
            if low_limit is None:
                low_limit = defaults['low']
            
            high_limit = sensor_config.get("high_limit")
            if high_limit is None:
                high_limit = defaults['high']
            
            unit = sensor_config.get("unit", "")
            if not unit:
                unit = defaults['unit']
            
            config = SensorConfig(
                name=sensor_config["name"],
                sensor_id=sensor_config["id"],
                low_limit=low_limit,
                high_limit=high_limit,
                unit=unit
            )
            self.sensor_configs[sensor_config["id"]] = config
            self.sensor_history[sensor_config["id"]] = deque(maxlen=self.max_history_points)
            self.sensor_timestamps[sensor_config["id"]] = deque(maxlen=self.max_history_points)
        
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
        # Don't connect alarm signal directly - we'll handle notifications manually on state transitions
        
        # Create helper for thread-safe alarm clearing from remote console
        self.alarm_clear_helper = AlarmClearHelper(self._do_clear_alarm_log)
        
        # Initialize remote console server
        self.remote_console = None
        self.console_thread = None
        self.console_loop = None
        self.console_started = False
        self.http_server = None
        self.http_thread = None
        
        # Setup UI first (non-blocking)
        self.setup_ui()
        
        # Setup update timer
        update_rate = self.config.get("update_rate", 0.5)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(int(update_rate * 1000))  # Convert to milliseconds
        
        # Defer blocking operations until after window is shown
        # This prevents freezing on Windows during initialization
        QTimer.singleShot(100, self._deferred_initialization)
        
        # System status
        self.system_status = "OK"
        
        # Initialize sensor statistics tracking
        self.sensor_stats = {}
        for sensor_id in self.sensor_configs.keys():
            self.sensor_stats[sensor_id] = {
                'total_readings': 0,
                'ok_count': 0,
                'alarm_count': 0,
                'faulty_count': 0,
                'value_sum': 0.0,
                'alarm_events': 0
            }
    
    def eventFilter(self, obj, event):
        """Event filter to prevent splitter handle resizing"""
        from PyQt5.QtCore import QEvent
        # Block mouse events on splitter handles
        if isinstance(obj, QWidget) and obj.parent() and isinstance(obj.parent(), QSplitter):
            if event.type() in [QEvent.MouseButtonPress, QEvent.MouseMove, QEvent.MouseButtonRelease, QEvent.HoverEnter, QEvent.HoverMove]:
                event.accept()  # Accept the event to prevent further processing
                return True  # Block the event - return True to indicate event was handled
        # Call parent's eventFilter - ensure it always returns a boolean
        try:
            result = super().eventFilter(obj, event)
            return bool(result)  # Ensure we always return a boolean
        except Exception:
            return False  # Return False if parent's eventFilter fails
    
    def apply_stylesheet(self):
        """Load and apply stylesheet from file"""
        stylesheet_path = Path(__file__).parent / 'stylesheet' / 'styles.qss'
        try:
            with open(stylesheet_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
                self.setStyleSheet(stylesheet)
        except FileNotFoundError:
            # If stylesheet file doesn't exist, use default styles
            print(f"Warning: Stylesheet file not found at {stylesheet_path}, using default styles")
        except Exception as e:
            print(f"Error loading stylesheet: {e}")
    
    def set_application_icon(self):
        """Set application icon from fav.png for window title bar and taskbar (Windows/Linux)"""
        # Get project root directory
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        icon_path = project_root / 'fav.png'
        
        if icon_path.exists():
            # Use absolute path for better Windows compatibility
            abs_icon_path = str(icon_path.resolve())
            icon = QIcon(abs_icon_path)
            
            # Verify icon is valid
            if not icon.isNull():
                # Set window icon (appears in window title bar)
                self.setWindowIcon(icon)
                # Set application-wide icon (appears in taskbar on Windows/Linux)
                QApplication.setWindowIcon(icon)
                # Also set on QApplication instance (Windows sometimes needs this)
                app = QApplication.instance()
                if app:
                    app.setWindowIcon(icon)
                print(f"Window icon set from: {abs_icon_path}")
            else:
                print(f"Warning: Icon file exists but could not be loaded: {abs_icon_path}")
        else:
            print(f"Warning: Icon file not found at {icon_path}, using default icon")
    
    def load_config(self) -> dict:
        """Load configuration from config.json"""
        config_path = Path(__file__).parent.parent / "config" / "config.json"
        try:
            with open(config_path, "r", encoding='utf-8') as f:
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
        
        # Global System Health Indicator - beside connect button
        health_indicator = self.create_global_health_indicator()
        header_layout.addWidget(health_indicator)
        header_layout.addWidget(self.connect_btn)
        
        # Update health indicator to show correct initial state (Disconnected)
        self.update_global_health_indicator()
        
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
        
        # Reports tab
        reports_tab = self.create_reports_tab()
        tabs.addTab(reports_tab, "Reports")
        
        # Maintenance Console tab (with authentication)
        maintenance_tab = self.create_maintenance_console_tab()
        tabs.addTab(maintenance_tab, "Maintenance Console")
        
        layout.addWidget(tabs)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def create_dashboard_tab(self) -> QWidget:
        """Create the main dashboard tab with plots on left half and sensor info on right"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
        """)
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Create splitter to divide dashboard in half
        # Use custom non-resizable splitter
        splitter = NonResizableSplitter(Qt.Horizontal)
        splitter.setHandleWidth(3)
        # Splitter styles are handled by stylesheet
        
        # LEFT SIDE: Sensor Status (50% of width) - Scrollable
        info_widget = QWidget()
        info_widget.setProperty("statusWidget", True)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(15)
        
        # Title
        info_title = QLabel("Sensor Status")
        info_title.setProperty("statusTitle", True)
        info_layout.addWidget(info_title)
        
        # Sensor status table - wrapped in scroll area
        table_scroll = QScrollArea()
        table_scroll.setWidgetResizable(True)
        # Scroll area styles are handled by stylesheet
        
        # Sensor status table
        self.sensor_status_table = QTableWidget()
        self.sensor_status_table.setColumnCount(6)
        self.sensor_status_table.setHorizontalHeaderLabels([
            "ID", "Sensor Name", "Latest Value", "Unit", "Timestamp", "Status"
        ])
        
        # Set column resize modes - size columns based on content
        header = self.sensor_status_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID - fit content
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Sensor Name - stretch to fill space
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Latest Value - fit content (max length)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Unit - fit content
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Timestamp - fit content
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Status - fit content
        
        # Set table size policy to expand
        self.sensor_status_table.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        
        self.sensor_status_table.setRowCount(len(self.sensor_configs))
        self.sensor_status_table.verticalHeader().setVisible(False)
        self.sensor_status_table.setShowGrid(False)
        self.sensor_status_table.setAlternatingRowColors(False)  # Disabled - using status-based row colors
        self.sensor_status_table.setProperty("sensorStatusTable", True)
        # Make table read-only
        self.sensor_status_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Populate status table
        row = 0
        for sensor_id, config in sorted(self.sensor_configs.items()):
            # ID column
            id_item = QTableWidgetItem(str(config.sensor_id))
            id_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.sensor_status_table.setItem(row, 0, id_item)
            
            # Sensor Name column
            name_item = QTableWidgetItem(config.name)
            name_item.setFont(QFont("Segoe UI", 9, QFont.Bold))  # Reduced font size
            self.sensor_status_table.setItem(row, 1, name_item)
            
            # Latest Value column
            self.sensor_status_table.setItem(row, 2, QTableWidgetItem("--"))
            
            # Unit column
            unit_item = QTableWidgetItem(config.unit if config.unit else "--")
            self.sensor_status_table.setItem(row, 3, unit_item)
            
            # Timestamp column
            self.sensor_status_table.setItem(row, 4, QTableWidgetItem("--"))
            
            # Status column
            self.sensor_status_table.setItem(row, 5, QTableWidgetItem("--"))
            
            row += 1
        
        table_scroll.setWidget(self.sensor_status_table)
        table_scroll.setWidgetResizable(True)
        table_scroll.setMinimumWidth(470)  # Minimum width for the table area (increased by 30 from 440)
        info_layout.addWidget(table_scroll, 1)  # Add stretch factor to make it expand
        
        # Alarm Log Table - Small table under sensor status
        alarm_log_title = QLabel("Alarm Log")
        alarm_log_title.setProperty("statusTitle", True)
        info_layout.addWidget(alarm_log_title)
        
        # Small alarm log table
        self.dashboard_alarm_table = QTableWidget()
        self.dashboard_alarm_table.setColumnCount(4)
        self.dashboard_alarm_table.setHorizontalHeaderLabels([
            "Time", "Sensor Name", "Value", "Type"
        ])
        
        # Set column resize modes
        alarm_header = self.dashboard_alarm_table.horizontalHeader()
        alarm_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Time
        alarm_header.setSectionResizeMode(1, QHeaderView.Stretch)  # Sensor Name
        alarm_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Value
        alarm_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Type
        
        # Set table properties
        self.dashboard_alarm_table.setMaximumHeight(150)  # Limit height for compact display
        self.dashboard_alarm_table.verticalHeader().setVisible(False)
        self.dashboard_alarm_table.setShowGrid(False)
        self.dashboard_alarm_table.setAlternatingRowColors(True)
        self.dashboard_alarm_table.setProperty("sensorStatusTable", True)
        self.dashboard_alarm_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dashboard_alarm_table.setRowCount(0)  # Start with no rows
        
        info_layout.addWidget(self.dashboard_alarm_table)
        
        splitter.addWidget(info_widget)
        
        # RIGHT SIDE: Plots (50% of width) - Scrollable for variable number of sensors
        plots_scroll = QScrollArea()
        plots_scroll.setWidgetResizable(True)
        plots_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #f5f5f5;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #e0e0e0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #b0b0b0;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #909090;
            }
        """)
        
        plots_widget = QWidget()
        plots_widget.setStyleSheet("background-color: #f5f5f5;")
        plots_layout = QVBoxLayout(plots_widget)
        plots_layout.setSpacing(15)
        plots_layout.setContentsMargins(5, 5, 5, 5)
        
        # Store plot widgets in a dictionary for easy access
        self.sensor_plots = {}
        
        # Calculate plot height - reduced size for more compact display
        num_sensors = len(self.sensor_configs)
        if num_sensors > 0:
            # Smaller plots - reduced height for more compact display
            estimated_height_per_plot = max(180, 200)
        else:
            estimated_height_per_plot = 200
        
        # Create a plot for each sensor, stacked vertically
        for sensor_id, config in sorted(self.sensor_configs.items()):
            # Container widget for each sensor plot
            plot_container = QWidget()
            plot_container.setProperty("plotContainer", True)
            container_layout = QVBoxLayout(plot_container)
            container_layout.setContentsMargins(8, 8, 8, 10)  # Reduced margins for compact display
            container_layout.setSpacing(3)
            
            # Sensor name label - smaller font and compact spacing
            sensor_label = QLabel(f"{config.name} (S{config.sensor_id:02d})")
            sensor_label.setProperty("sensorLabel", True)
            sensor_label.setStyleSheet("font-size: 10px; margin-bottom: 2px;")  # Smaller label
            container_layout.addWidget(sensor_label)
            
            # Create plot widget with professional light theme - compact size
            plot_widget = pg.PlotWidget()
            plot_widget.setBackground('#ffffff')
            
            # Set axis labels - smaller fonts for cleaner look
            if config.unit:
                plot_widget.setLabel('left', config.unit, **{'color': '#333333', 'font-size': '9pt'})
            else:
                plot_widget.setLabel('left', 'Value', **{'color': '#333333', 'font-size': '9pt'})
            plot_widget.setLabel('bottom', 'Time', **{'color': '#333333', 'font-size': '9pt'})
            
            plot_widget.setMouseEnabled(x=True, y=True)  # Enable zooming
            plot_widget.showGrid(x=True, y=True, alpha=0.2)  # Subtle professional grid
            plot_widget.setMinimumHeight(estimated_height_per_plot - 40)  # Compact plots
            plot_widget.setMaximumHeight(estimated_height_per_plot - 40)
            
            # Professional light theme plot styling
            plot_widget.getAxis('left').setPen(pg.mkPen(color='#999999', width=1.5))
            plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#999999', width=1.5))
            plot_widget.getAxis('left').setTextPen(pg.mkPen(color='#333333', width=1))
            plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#333333', width=1))
            
            # Style tick marks - smaller fonts
            plot_widget.getAxis('left').setTickFont(QFont('Arial', 8))
            plot_widget.getAxis('bottom').setTickFont(QFont('Arial', 8))
            
            # Ensure x-axis labels are visible with proper spacing
            plot_widget.getAxis('bottom').setHeight(40)  # Reduced height for compact display
            plot_widget.getAxis('left').setWidth(50)  # Reduced width for compact display
            
            # Store plot widget reference by sensor_id
            plot_widget.setProperty("sensor_id", sensor_id)
            self.sensor_plots[sensor_id] = plot_widget
            
            container_layout.addWidget(plot_widget)
            plots_layout.addWidget(plot_container)
        
        plots_layout.addStretch()
        
        # Set the scrollable widget
        plots_scroll.setWidget(plots_widget)
        splitter.addWidget(plots_scroll)
        
        # Set fixed sizes for both panels to prevent resizing
        # Calculate based on window width or use fixed pixel values
        total_width = 1400  # Default window width
        left_width = int(total_width * 0.4) + 70  # 40% for sensor status + 70 pixels (40 + 30)
        right_width = int(total_width * 0.6) - 150  # 60% for plots - 150 pixels (reduced width by 50px total)
        
        splitter.setSizes([left_width, right_width])
        
        # Splitter is already non-resizable via NonResizableSplitter class
        
        main_layout.addWidget(splitter)
        
        return widget
    
    def create_global_health_indicator(self) -> QWidget:
        """Create global system health indicator"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 8px;
                border: 2px solid #d0d0d0;
                padding: 15px;
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Overall System Health")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333333;")
        layout.addWidget(title_label)
        
        # Status indicator (will be updated dynamically)
        # Initialize as Disconnected since no sensors are connected at startup
        self.global_health_status_label = QLabel("● Disconnected")
        self.global_health_status_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #757575;
            padding: 8px 15px;
            background-color: #e0e0e0;
            border-radius: 5px;
            border: 1px solid #9e9e9e;
        """)
        layout.addWidget(self.global_health_status_label)
        
        layout.addStretch()
        
        return widget
    
    def update_global_health_indicator(self):
        """Update the global system health indicator based on sensor states"""
        if not hasattr(self, 'global_health_status_label'):
            return
        
        # Check if system is connected
        connection_status = self.sensor_manager.get_connection_status()
        is_connected = any(connection_status.values()) if connection_status else False
        
        # Count sensor states
        sensors_with_data = len(self.sensor_readings)
        
        # Show Disconnected if:
        # 1. No communication channels are connected, OR
        # 2. No sensor data has been received (even if connections exist, no data means disconnected)
        if not is_connected or sensors_with_data == 0:
            # System is disconnected - no active connections or no sensor data
            status_text = "● Disconnected"
            status_color = "#757575"
            status_bg = "#e0e0e0"
            border_color = "#9e9e9e"  # Gray border for disconnected
        else:
            # We have connections AND sensor data - check health status
            # Check for faulty sensors (Critical)
            faulty_count = sum(1 for r in self.sensor_readings.values() 
                             if r.status == SensorStatus.FAULTY)
            
            # Check for alarms (Warning)
            alarm_count = sum(1 for r in self.sensor_readings.values() 
                            if r.status in [SensorStatus.LOW_ALARM, SensorStatus.HIGH_ALARM])
            
            # Determine overall health
            if faulty_count > 0:
                # Critical - has faulty sensors
                status_text = "● Critical / Fault"  # Using bullet instead of emoji for better compatibility
                status_color = "#ffffff"
                status_bg = "#c62828"
                border_color = "#8b1a1a"  # Dark red border for critical
            elif alarm_count > 0:
                # Warning - has alarms but no faulty sensors
                status_text = "● Warning / Degraded"  # Using bullet instead of emoji
                status_color = "#f57c00"
                status_bg = "#fff9c4"
                border_color = "#e65100"  # Dark orange border for warning
            else:
                # Normal - all sensors OK
                status_text = "● Normal / Healthy"  # Using bullet instead of emoji
                status_color = "#2e7d32"
                status_bg = "#c8e6c9"
                border_color = "#a5d6a7"  # Dark green border for normal
        
        # Update the label
        self.global_health_status_label.setText(status_text)
        
        self.global_health_status_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {status_color};
            padding: 6px 12px;
            background-color: {status_bg};
            border-radius: 5px;
            border: 1px solid {border_color};
        """)
    
    def create_reports_tab(self) -> QWidget:
        """Create the reports tab with OEE-style reports"""
        widget = QWidget()
        widget.setStyleSheet("background-color: #f5f5f5;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Reports")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Create scrollable area for reports
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #f5f5f5;")
        
        reports_widget = QWidget()
        reports_layout = QVBoxLayout(reports_widget)
        reports_layout.setSpacing(30)
        
        # Sensor Reports Section
        sensor_reports_section = self.create_sensor_reports_section()
        reports_layout.addWidget(sensor_reports_section)
        
        reports_layout.addStretch()
        scroll.setWidget(reports_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def create_sensor_reports_section(self) -> QWidget:
        """Create sensor reports section with detailed sensor analytics"""
        widget = QWidget()
        widget.setStyleSheet("background-color: white; border-radius: 10px; padding: 20px;")
        layout = QVBoxLayout(widget)
        
        title = QLabel("Sensor Performance Reports")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #333; margin-bottom: 15px;")
        layout.addWidget(title)
        
        # Sensor reports table
        self.sensor_reports_table = QTableWidget()
        self.sensor_reports_table.setColumnCount(3)
        self.sensor_reports_table.setHorizontalHeaderLabels([
            "Sensor Name", "Value", "State"
        ])
        self.sensor_reports_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sensor_reports_table.setRowCount(len(self.sensor_configs))
        self.sensor_reports_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 10px;
                font-weight: bold;
            }
        """)
        
        # Initialize sensor tracking
        self.sensor_stats = {}
        for sensor_id, config in self.sensor_configs.items():
            self.sensor_stats[sensor_id] = {
                'total_readings': 0,
                'ok_count': 0,
                'alarm_count': 0,
                'faulty_count': 0,
                'value_sum': 0.0,
                'alarm_events': 0
            }
        
        # Populate table with sensor configs
        row = 0
        for sensor_id, config in sorted(self.sensor_configs.items()):
            self.sensor_reports_table.setItem(row, 0, QTableWidgetItem(config.name))
            self.sensor_reports_table.setItem(row, 1, QTableWidgetItem("--"))
            self.sensor_reports_table.setItem(row, 2, QTableWidgetItem("--"))
            row += 1
        
        layout.addWidget(self.sensor_reports_table)
        
        # Sensor performance summary
        summary_label = QLabel("Sensor Performance Summary")
        summary_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; margin-top: 20px;")
        layout.addWidget(summary_label)
        
        summary_layout = QHBoxLayout()
        
        # Healthy sensors
        self.healthy_sensors_label = QLabel("Healthy: 0")
        self.healthy_sensors_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #4CAF50; padding: 10px;")
        summary_layout.addWidget(self.healthy_sensors_label)
        
        # Sensors in alarm
        self.alarm_sensors_label = QLabel("In Alarm: 0")
        self.alarm_sensors_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FF9800; padding: 10px;")
        summary_layout.addWidget(self.alarm_sensors_label)
        
        # Faulty sensors
        self.faulty_sensors_label = QLabel("Faulty: 0")
        self.faulty_sensors_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #F44336; padding: 10px;")
        summary_layout.addWidget(self.faulty_sensors_label)
        
        # Total sensors
        self.total_sensors_label = QLabel(f"Total: {len(self.sensor_configs)}")
        self.total_sensors_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; padding: 10px;")
        summary_layout.addWidget(self.total_sensors_label)
        
        summary_layout.addStretch()
        layout.addLayout(summary_layout)
        
        # Sensor trend plots (combined view)
        trends_label = QLabel("Sensor Value Trends (All Sensors)")
        trends_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; margin-top: 20px;")
        layout.addWidget(trends_label)
        
        self.sensor_trends_plot = pg.PlotWidget()
        self.sensor_trends_plot.setBackground('w')
        self.sensor_trends_plot.setLabel('left', 'Value')
        self.sensor_trends_plot.setLabel('bottom', 'Time')
        self.sensor_trends_plot.showGrid(x=True, y=True, alpha=0.3)
        self.sensor_trends_plot.setMinimumHeight(300)
        self.sensor_trends_plot.addLegend()
        layout.addWidget(self.sensor_trends_plot)
        
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
        self.results_text.setReadOnly(True)  # Already read-only
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
    
    def create_maintenance_console_tab(self) -> QWidget:
        """Create the maintenance console tab with authentication"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Login section at the top (always visible)
        login_section = QWidget()
        login_section.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        login_layout = QHBoxLayout(login_section)
        login_layout.setSpacing(15)
        login_layout.setContentsMargins(15, 10, 15, 10)
        
        # Login title
        login_title = QLabel("Maintenance Console")
        login_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        login_layout.addWidget(login_title)
        
        # Username field
        username_label = QLabel("Username:")
        username_label.setStyleSheet("font-size: 12px; color: #333;")
        login_layout.addWidget(username_label)
        self.maintenance_username_input = QLineEdit()
        self.maintenance_username_input.setPlaceholderText("Enter username")
        self.maintenance_username_input.setMinimumWidth(150)
        self.maintenance_username_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                font-size: 12px;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
        """)
        login_layout.addWidget(self.maintenance_username_input)
        
        # Password field
        password_label = QLabel("Password:")
        password_label.setStyleSheet("font-size: 12px; color: #333;")
        login_layout.addWidget(password_label)
        self.maintenance_password_input = QLineEdit()
        self.maintenance_password_input.setPlaceholderText("Enter password")
        self.maintenance_password_input.setEchoMode(QLineEdit.Password)
        self.maintenance_password_input.setMinimumWidth(150)
        self.maintenance_password_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                font-size: 12px;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
        """)
        login_layout.addWidget(self.maintenance_password_input)
        
        # Login button
        self.maintenance_login_btn = QPushButton("Login")
        self.maintenance_login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 3px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.maintenance_login_btn.clicked.connect(self.authenticate_maintenance_console)
        login_layout.addWidget(self.maintenance_login_btn)
        
        # Status label (shows logged in status or error)
        self.maintenance_status_label = QLabel("Not logged in")
        self.maintenance_status_label.setStyleSheet("font-size: 12px; color: #757575; font-weight: bold;")
        login_layout.addWidget(self.maintenance_status_label)
        
        # Webserver link
        console_config = self.config.get("remote_console", {})
        http_port = console_config.get("http_port", 8080)
        self.maintenance_webserver_link = QLabel(f"<a href='http://localhost:{http_port}/web/remote_console_client.html'>Web Console</a>")
        self.maintenance_webserver_link.setOpenExternalLinks(True)
        self.maintenance_webserver_link.setStyleSheet("font-size: 12px; color: #2196F3;")
        login_layout.addWidget(self.maintenance_webserver_link)
        
        login_layout.addStretch()
        
        # Logout button (initially hidden)
        self.maintenance_logout_btn = QPushButton("Logout")
        self.maintenance_logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 8px 20px;
                font-size: 12px;
                border-radius: 3px;
                border: none;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        self.maintenance_logout_btn.clicked.connect(self.logout_maintenance_console)
        self.maintenance_logout_btn.hide()
        login_layout.addWidget(self.maintenance_logout_btn)
        
        layout.addWidget(login_section)
        
        # Error label (below login section)
        self.maintenance_error_label = QLabel("")
        self.maintenance_error_label.setStyleSheet("color: #F44336; font-size: 11px; padding: 5px;")
        self.maintenance_error_label.setAlignment(Qt.AlignCenter)
        self.maintenance_error_label.hide()
        layout.addWidget(self.maintenance_error_label)
        
        # Content section (always visible, but disabled until authenticated)
        self.maintenance_content_widget = QWidget()
        content_layout = QVBoxLayout(self.maintenance_content_widget)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sub-tabs for maintenance console
        self.maintenance_tabs = QTabWidget()
        self.maintenance_tabs.setStyleSheet("""
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
        
        # Alarm Log sub-tab
        alarm_tab = self.create_alarm_log_tab()
        self.maintenance_tabs.addTab(alarm_tab, "Alarm Log")
        
        # System Tools sub-tab
        tools_tab = self.create_system_tools_tab()
        self.maintenance_tabs.addTab(tools_tab, "System Tools")
        
        # Live Log Viewer sub-tab
        log_viewer_tab = self.create_live_log_viewer_tab()
        self.maintenance_tabs.addTab(log_viewer_tab, "Live Log Viewer")
        
        content_layout.addWidget(self.maintenance_tabs)
        layout.addWidget(self.maintenance_content_widget)
        
        # Initially disable content (not authenticated)
        self.set_maintenance_content_enabled(False)
        
        return widget
    
    def set_maintenance_content_enabled(self, enabled: bool):
        """Enable or disable maintenance console content"""
        if hasattr(self, 'maintenance_tabs'):
            self.maintenance_tabs.setEnabled(enabled)
            # Also disable/enable all child widgets
            for i in range(self.maintenance_tabs.count()):
                tab_widget = self.maintenance_tabs.widget(i)
                if tab_widget:
                    tab_widget.setEnabled(enabled)
    
    def authenticate_maintenance_console(self):
        """Authenticate user for maintenance console"""
        username = self.maintenance_username_input.text().strip()
        password = self.maintenance_password_input.text()
        
        if not username or not password:
            self.maintenance_error_label.setText("Please enter both username and password")
            self.maintenance_error_label.show()
            return
        
        # Get users from config
        console_config = self.config.get("remote_console", {})
        users = console_config.get("users", {})
        
        # Check credentials
        if username in users:
            user_config = users[username]
            if user_config.get("password") == password:
                # Authentication successful
                self.maintenance_authenticated = True
                self.maintenance_user = username
                
                # Enable content
                self.set_maintenance_content_enabled(True)
                
                # Update UI elements
                self.maintenance_status_label.setText(f"Logged in as: {username}")
                self.maintenance_status_label.setStyleSheet("font-size: 12px; color: #4CAF50; font-weight: bold;")
                self.maintenance_login_btn.hide()
                self.maintenance_logout_btn.show()
                self.maintenance_username_input.setEnabled(False)
                self.maintenance_password_input.setEnabled(False)
                
                # Clear password field and error
                self.maintenance_password_input.clear()
                self.maintenance_error_label.hide()
                
                # Populate alarm log table with existing alarms
                if hasattr(self, 'alarm_table'):
                    self.alarm_table.setRowCount(0)  # Clear first
                    for alarm in self.alarm_log:
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
                
                # Add login entry to log viewer
                self.add_log_entry(f"User '{username}' logged into Maintenance Console", "INFO")
                
                return
        
        # Authentication failed
        self.maintenance_error_label.setText("Invalid username or password")
        self.maintenance_error_label.show()
        self.maintenance_password_input.clear()
    
    def logout_maintenance_console(self):
        """Logout from maintenance console"""
        username = self.maintenance_user
        self.maintenance_authenticated = False
        self.maintenance_user = None
        
        # Disable content
        self.set_maintenance_content_enabled(False)
        
        # Update UI elements
        self.maintenance_status_label.setText("Not logged in")
        self.maintenance_status_label.setStyleSheet("font-size: 12px; color: #757575; font-weight: bold;")
        self.maintenance_login_btn.show()
        self.maintenance_logout_btn.hide()
        self.maintenance_username_input.setEnabled(True)
        self.maintenance_password_input.setEnabled(True)
        
        # Clear inputs
        self.maintenance_username_input.clear()
        self.maintenance_password_input.clear()
        self.maintenance_error_label.hide()
        
        # Clear alarm log table (hide data when logged out)
        if hasattr(self, 'alarm_table'):
            self.alarm_table.setRowCount(0)
        
        # Add logout entry to log viewer
        if username:
            self.add_log_entry(f"User '{username}' logged out from Maintenance Console", "INFO")
    
    def create_live_log_viewer_tab(self) -> QWidget:
        """Create the live log viewer tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Live Log Viewer")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Log viewer text area
        self.live_log_viewer = QTextEdit()
        self.live_log_viewer.setReadOnly(True)
        self.live_log_viewer.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.live_log_viewer)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.setStyleSheet("""
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
        clear_log_btn.clicked.connect(lambda: self.live_log_viewer.clear())
        buttons_layout.addWidget(clear_log_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Initialize log viewer with welcome message
        self.live_log_viewer.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Log viewer initialized")
        
        return widget
    
    def add_log_entry(self, message: str, level: str = "INFO"):
        """Add an entry to the live log viewer"""
        if hasattr(self, 'live_log_viewer') and self.live_log_viewer:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # Color code based on level
            if level == "ALARM" or level == "FAULT":
                color = "#ff6b6b"  # Red
            elif level == "WARNING":
                color = "#ffa94d"  # Orange
            elif level == "INFO":
                color = "#51cf66"  # Green
            else:
                color = "#d4d4d4"  # Default gray
            
            log_entry = f'<span style="color: {color}">[{timestamp}] [{level}] {message}</span>'
            self.live_log_viewer.append(log_entry)
            # Don't auto-scroll - let user control scrolling manually
    
    def run_self_test(self):
        """Run system self-test"""
        self.add_log_entry("Self-test initiated", "INFO")
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
        # Count sensors that have actually received readings (active connections)
        sensors_with_readings = set(self.sensor_readings.keys())
        total_count = len(self.sensor_configs)
        connected_count = len(sensors_with_readings)
        connection_test = {
            "name": "Sensor Connections",
            "status": "PASS" if connected_count == total_count else "WARN",
            "details": f"{connected_count}/{total_count} connections active (sensors receiving data)"
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
            status_icon = "[PASS]" if test["status"] == "PASS" else "[WARN]" if test["status"] == "WARN" else "[FAIL]"
            self.results_text.append(f"{status_icon} {test['name']}: {test['status']}\n")
            self.results_text.append(f"   {test['details']}\n")
            self.results_text.append("\n")
        
        self.results_text.append("=" * 60 + "\n")
        self.results_text.append("Self-Test Complete\n")
        
        # Add to log viewer
        status_msg = f"Self-test completed: {test_results['overall_status']} ({test_results['passed']}/{test_results['total_tests']} passed)"
        log_level = "WARNING" if test_results['overall_status'] == "WARN" else "INFO"
        self.add_log_entry(status_msg, log_level)
        
        # Show status bar message
        if test_results["overall_status"] == "PASS":
            self.statusBar().showMessage("Self-Test: PASSED", 5000)
        else:
            self.statusBar().showMessage("Self-Test: WARNINGS DETECTED", 5000)
    
    def get_snapshot(self):
        """Get detailed system snapshot"""
        self.add_log_entry("System snapshot requested", "INFO")
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
            status_icon = "[OK]" if sensor["status"] == "OK" else "[WARN]" if "Alarm" in sensor["status"] else "[FAIL]"
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
        
        # Add to log viewer
        self.add_log_entry(f"System snapshot generated: {snapshot['system_status']['sensor_count']} sensors, {snapshot['system_status']['alarm_count']} alarms", "INFO")
        
        self.statusBar().showMessage("System snapshot generated", 3000)
    
    def connect_to_sensors(self):
        """Connect to all sensor communicators"""
        self.add_log_entry("Attempting to connect to sensors...", "INFO")
        
        results = self.sensor_manager.connect_all()
        
        connected = sum(1 for v in results.values() if v)
        total = len(results)
        
        # Log connection results for each communicator
        for key, status in results.items():
            # Parse key to get protocol and endpoint info
            if key.startswith("serial_"):
                port = key.replace("serial_", "")
                # Find sensors using this port
                sensors_on_port = []
                for sensor_id, config in self.sensor_configs.items():
                    sensor_config = None
                    for sc in self.config.get("sensors", []):
                        if sc["id"] == sensor_id:
                            sensor_config = sc
                            break
                    if sensor_config and sensor_config.get("protocol_config", {}).get("port") == port:
                        sensors_on_port.append(config.name)
                
                sensor_names = ", ".join(sensors_on_port) if sensors_on_port else f"port {port}"
                if status:
                    self.add_log_entry(f"Successfully connected to serial port {port} (sensors: {sensor_names})", "INFO")
                else:
                    self.add_log_entry(f"Failed to connect to serial port {port} (sensors: {sensor_names})", "WARNING")
            elif key.startswith("tcp_"):
                parts = key.replace("tcp_", "").split("_")
                if len(parts) >= 2:
                    host = parts[0]
                    port = parts[1]
                    # Find sensors using this TCP server
                    sensors_on_server = []
                    for sensor_id, config in self.sensor_configs.items():
                        sensor_config = None
                        for sc in self.config.get("sensors", []):
                            if sc["id"] == sensor_id:
                                sensor_config = sc
                                break
                        if sensor_config:
                            pc = sensor_config.get("protocol_config", {})
                            if pc.get("host") == host and str(pc.get("port")) == port:
                                sensors_on_server.append(config.name)
                    
                    sensor_names = ", ".join(sensors_on_server) if sensors_on_server else f"{host}:{port}"
                    if status:
                        self.add_log_entry(f"Successfully connected to TCP server {host}:{port} (sensors: {sensor_names})", "INFO")
                    else:
                        self.add_log_entry(f"Failed to connect to TCP server {host}:{port} (sensors: {sensor_names})", "WARNING")
            elif key.startswith("modbus_"):
                parts = key.replace("modbus_", "").split("_")
                if len(parts) >= 2:
                    host = parts[0]
                    port = parts[1]
                    # Find sensors using this Modbus server
                    sensors_on_server = []
                    for sensor_id, config in self.sensor_configs.items():
                        sensor_config = None
                        for sc in self.config.get("sensors", []):
                            if sc["id"] == sensor_id:
                                sensor_config = sc
                                break
                        if sensor_config:
                            pc = sensor_config.get("protocol_config", {})
                            if pc.get("host") == host and str(pc.get("port")) == port:
                                sensors_on_server.append(config.name)
                    
                    sensor_names = ", ".join(sensors_on_server) if sensors_on_server else f"{host}:{port}"
                    if status:
                        self.add_log_entry(f"Successfully connected to Modbus server {host}:{port} (sensors: {sensor_names})", "INFO")
                    else:
                        self.add_log_entry(f"Failed to connect to Modbus server {host}:{port} (sensors: {sensor_names})", "WARNING")
            else:
                if status:
                    self.add_log_entry(f"Successfully connected to {key}", "INFO")
                else:
                    self.add_log_entry(f"Failed to connect to {key}", "WARNING")
        
        if connected > 0:
            self.statusBar().showMessage(f"Connected to {connected}/{total} communication channels")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("background-color: red;")
            
            if connected == total:
                self.add_log_entry(f"All sensor connections established ({connected}/{total})", "INFO")
            else:
                self.add_log_entry(f"Partial connection established ({connected}/{total} channels connected)", "WARNING")
            
            # Show details
            status_details = []
            for key, status in results.items():
                status_details.append(f"{key}: {'[OK]' if status else '[FAIL]'}")
            
            if connected < total:
                QMessageBox.warning(self, "Partial Connection",
                                  f"Connected to {connected}/{total} channels:\n" + 
                                  "\n".join(status_details))
        else:
            self.statusBar().showMessage("Failed to connect to sensors")
            self.add_log_entry("Failed to connect to any sensor communication channels", "WARNING")
            QMessageBox.warning(self, "Connection Error",
                              "Could not connect to any sensor communication channels.\n"
                              "Make sure the sensors are connected and available.")
        
        # Update global health indicator to reflect connection status
        self.update_global_health_indicator()
    
    def toggle_connection(self):
        """Toggle connection to sensors"""
        status = self.sensor_manager.get_connection_status()
        if any(status.values()):
            # Disconnecting
            connected_count = sum(1 for v in status.values() if v)
            self.add_log_entry(f"Disconnecting from {connected_count} sensor communication channel(s)...", "INFO")
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
            self.add_log_entry("Disconnected from all sensors", "INFO")
            # Update global health indicator to show disconnected
            self.update_global_health_indicator()
        else:
            # Connecting
            self.connect_to_sensors()
    
    def on_sensor_reading(self, reading: SensorReading):
        """Handle new sensor reading"""
        # Get previous reading and status before updating (for transition detection)
        prev_reading = self.sensor_readings.get(reading.sensor_id)
        prev_status = self.previous_sensor_status.get(reading.sensor_id, SensorStatus.OK)
        self.sensor_readings[reading.sensor_id] = reading
        
        # Update previous status tracking
        current_status = reading.status
        self.previous_sensor_status[reading.sensor_id] = current_status
        
        # Update sensor statistics
        if reading.sensor_id in self.sensor_stats:
            stats = self.sensor_stats[reading.sensor_id]
            stats['total_readings'] += 1
            stats['value_sum'] += reading.value
            
            if reading.status == SensorStatus.OK:
                stats['ok_count'] += 1
            elif reading.status in [SensorStatus.LOW_ALARM, SensorStatus.HIGH_ALARM]:
                stats['alarm_count'] += 1
            elif reading.status == SensorStatus.FAULTY:
                stats['faulty_count'] += 1
        
        # Update remote console
        if self.remote_console and self.console_loop:
            self.remote_console.set_sensor_readings(self.sensor_readings)
            # Broadcast update via WebSocket
            try:
                # Check if event loop is running before scheduling coroutine
                if self.console_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.remote_console.broadcast_sensor_update(reading),
                        self.console_loop
                    )
                # If loop is not running yet, the update will be sent when loop starts
            except RuntimeError as e:
                # Event loop might be closed or not ready yet
                if "Event loop is closed" not in str(e):
                    print(f"Error broadcasting sensor update: {e}")
            except Exception as e:
                print(f"Error broadcasting sensor update: {e}")
        
        # Check for FAULTY status or -999 value and add to dashboard alarm table
        is_faulty = (reading.status == SensorStatus.FAULTY) or (reading.value == -999.0)
        prev_was_faulty = prev_status == SensorStatus.FAULTY or (prev_reading and prev_reading.value == -999.0)
        
        if is_faulty:
            # Only notify/add to dashboard if sensor just became faulty (transition)
            if not prev_was_faulty:
                # Send notification for faulty sensor (only once on transition)
                if reading.value == -999.0:
                    config = self.sensor_configs.get(reading.sensor_id)
                    fault_alarm = AlarmEvent(
                        timestamp=reading.timestamp,
                        sensor_name=reading.sensor_name,
                        sensor_id=reading.sensor_id,
                        value=reading.value,
                        alarm_type="FAULT",
                        unit=reading.unit
                    )
                    # Send webhook for ALL fault alarms (no limits) - non-blocking
                    if self.notification_manager.webhook_url:
                        self.notification_manager.send_webhook_async(fault_alarm)
                    # Send desktop notification
                    message = self.notification_manager._format_alarm_message(fault_alarm)
                    self.notification_manager.send_desktop_notification(fault_alarm, message)
                # Sensor just became faulty - add to dashboard alarm table
                if hasattr(self, 'dashboard_alarm_table'):
                    max_rows = 10
                    current_rows = self.dashboard_alarm_table.rowCount()
                    
                    # Insert new row at the top
                    self.dashboard_alarm_table.insertRow(0)
                    
                    # Time column
                    time_item = QTableWidgetItem(reading.timestamp.strftime("%H:%M:%S"))
                    self.dashboard_alarm_table.setItem(0, 0, time_item)
                    
                    # Sensor Name column
                    name_item = QTableWidgetItem(reading.sensor_name)
                    self.dashboard_alarm_table.setItem(0, 1, name_item)
                    
                    # Value column
                    value_item = QTableWidgetItem(f"{reading.value:.2f}")
                    self.dashboard_alarm_table.setItem(0, 2, value_item)
                    
                    # Type column - FAULT
                    type_item = QTableWidgetItem("FAULT")
                    type_item.setForeground(QColor('#c62828'))  # Red for fault
                    self.dashboard_alarm_table.setItem(0, 3, type_item)
                    
                    # Remove old rows if exceeding max
                    if current_rows >= max_rows:
                        self.dashboard_alarm_table.removeRow(max_rows)
                
                # Add to live log viewer
                self.add_log_entry(f"FAULT detected on {reading.sensor_name} (ID: {reading.sensor_id}): Value = {reading.value:.2f} {reading.unit}", "FAULT")
        
        # Update status tracking when sensor recovers (for future transition detection)
        if reading.status == SensorStatus.OK and prev_status != SensorStatus.OK:
            # Sensor recovered from alarm/fault - update status so we can detect next transition
            self.previous_sensor_status[reading.sensor_id] = SensorStatus.OK
        elif not is_faulty and prev_was_faulty:
            # Sensor recovered from faulty state
            self.previous_sensor_status[reading.sensor_id] = reading.status
        
        # Add to history with timestamp
        if reading.sensor_id in self.sensor_history:
            self.sensor_history[reading.sensor_id].append(reading.value)
            # Store actual timestamp for rolling window filtering
            self.sensor_timestamps[reading.sensor_id].append(reading.timestamp)
    
    def on_alarm_triggered(self, alarm: AlarmEvent):
        """Handle alarm event - send webhook and desktop notifications for all alarms (no limits)"""
        # Get previous status to check for transition
        prev_status = self.previous_sensor_status.get(alarm.sensor_id, SensorStatus.OK)
        
        # Determine current status based on alarm type
        if alarm.alarm_type == "LOW":
            current_status = SensorStatus.LOW_ALARM
        elif alarm.alarm_type == "HIGH":
            current_status = SensorStatus.HIGH_ALARM
        else:
            current_status = SensorStatus.OK
        
        # Send webhook for ALL alarms (no limits) - non-blocking
        if self.notification_manager.webhook_url:
            self.notification_manager.send_webhook_async(alarm)
        
        # Send desktop notification for ALL alarms (no limits)
        message = self.notification_manager._format_alarm_message(alarm)
        self.notification_manager.send_desktop_notification(alarm, message)
        
        # Update previous status
        self.previous_sensor_status[alarm.sensor_id] = current_status
        
        # Always add to alarm log (even if not a transition, for historical record)
        self.alarm_log.append(alarm)
        
        # Update sensor statistics
        if alarm.sensor_id in self.sensor_stats:
            self.sensor_stats[alarm.sensor_id]['alarm_events'] += 1
        
        # Update remote console
        if self.remote_console and self.console_loop:
            self.remote_console.add_alarm(alarm)
            # Broadcast alarm via WebSocket
            try:
                # Check if event loop is running before scheduling coroutine
                if self.console_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.remote_console.broadcast_alarm(alarm),
                        self.console_loop
                    )
                # If loop is not running yet, the update will be sent when loop starts
            except RuntimeError as e:
                # Event loop might be closed or not ready yet
                if "Event loop is closed" not in str(e):
                    print(f"Error broadcasting alarm: {e}")
            except Exception as e:
                print(f"Error broadcasting alarm: {e}")
        
        # Update alarm log table (only if authenticated in maintenance console)
        if self.maintenance_authenticated and hasattr(self, 'alarm_table'):
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
        
        # Update dashboard alarm table (small table under sensor status)
        if hasattr(self, 'dashboard_alarm_table'):
            # Limit to last 10 alarms for compact display
            max_rows = 10
            current_rows = self.dashboard_alarm_table.rowCount()
            
            # Insert new row at the top
            self.dashboard_alarm_table.insertRow(0)
            
            # Time column
            time_item = QTableWidgetItem(alarm.timestamp.strftime("%H:%M:%S"))
            self.dashboard_alarm_table.setItem(0, 0, time_item)
            
            # Sensor Name column
            name_item = QTableWidgetItem(alarm.sensor_name)
            self.dashboard_alarm_table.setItem(0, 1, name_item)
            
            # Value column
            value_item = QTableWidgetItem(f"{alarm.value:.2f}")
            self.dashboard_alarm_table.setItem(0, 2, value_item)
            
            # Type column - display as LOW/HIGH/FAULT
            alarm_type_display = alarm.alarm_type.upper()  # Ensure uppercase
            type_item = QTableWidgetItem(alarm_type_display)
            # Color code based on alarm type
            if alarm.alarm_type.upper() == "LOW":
                type_item.setForeground(QColor('#f57c00'))
            elif alarm.alarm_type.upper() == "HIGH":
                type_item.setForeground(QColor('#c62828'))
            elif alarm.alarm_type.upper() == "FAULT":
                type_item.setForeground(QColor('#c62828'))  # Red for fault
            self.dashboard_alarm_table.setItem(0, 3, type_item)
            
            # Remove old rows if exceeding max
            if current_rows >= max_rows:
                self.dashboard_alarm_table.removeRow(max_rows)
        
        # Add to live log viewer
        self.add_log_entry(f"{alarm.alarm_type} alarm on {alarm.sensor_name} (ID: {alarm.sensor_id}): Value = {alarm.value:.2f} {alarm.unit}", "ALARM")
    
    def update_display(self):
        """Update the display with latest sensor data"""
        # Update reports tab plots if it exists
        if hasattr(self, 'sensor_reports_table'):
            self.update_reports_plots({})
        
        # Update global health indicator
        self.update_global_health_indicator()
        
        # Update stacked plots and sensor status table
        has_alarm = False
        row = 0
        
        for sensor_id, config in sorted(self.sensor_configs.items()):
            reading = self.sensor_readings.get(sensor_id)
            
            # Update sensor status table
            if hasattr(self, 'sensor_status_table'):
                if reading:
                    # Determine row background color based on status
                    if reading.status == SensorStatus.OK:
                        # Green - Healthy
                        row_bg_color = QColor('#c8e6c9')
                        row_text_color = QColor('#2e7d32')
                    elif reading.status == SensorStatus.FAULTY:
                        # Red - Critical
                        row_bg_color = QColor('#c62828')
                        row_text_color = QColor('#ffffff')
                        has_alarm = True
                    elif reading.status in [SensorStatus.LOW_ALARM, SensorStatus.HIGH_ALARM]:
                        # Yellow - Warning
                        row_bg_color = QColor('#fff9c4')
                        row_text_color = QColor('#f57c00')
                        has_alarm = True
                    else:
                        # Default
                        row_bg_color = QColor('#ffffff')
                        row_text_color = QColor('#333333')
                    
                    # Update latest value (column 2) - value only, no unit
                    value_item = QTableWidgetItem(f"{reading.value:.2f}")
                    value_item.setForeground(row_text_color)
                    value_item.setBackground(row_bg_color)
                    self.sensor_status_table.setItem(row, 2, value_item)
                    
                    # Update unit column (column 3) - apply row color
                    unit_item = self.sensor_status_table.item(row, 3)
                    if unit_item:
                        unit_item.setForeground(row_text_color)
                        unit_item.setBackground(row_bg_color)
                    
                    # Update timestamp (column 4)
                    time_str = reading.timestamp.strftime("%H:%M:%S")
                    time_item = QTableWidgetItem(time_str)
                    time_item.setForeground(row_text_color)
                    time_item.setBackground(row_bg_color)
                    self.sensor_status_table.setItem(row, 4, time_item)
                    
                    # Update status (column 5)
                    status_item = QTableWidgetItem(reading.status.value)
                    status_item.setForeground(row_text_color)
                    status_item.setBackground(row_bg_color)
                    self.sensor_status_table.setItem(row, 5, status_item)
                    
                    # Apply row colors to ID and Sensor Name columns as well
                    id_item = self.sensor_status_table.item(row, 0)
                    if id_item:
                        id_item.setBackground(row_bg_color)
                        id_item.setForeground(row_text_color)
                    
                    name_item = self.sensor_status_table.item(row, 1)
                    if name_item:
                        name_item.setBackground(row_bg_color)
                        name_item.setForeground(row_text_color)
                else:
                    # No data yet - default colors
                    for col in [2, 4, 5]:  # Latest Value, Timestamp, Status
                        item = QTableWidgetItem("--")
                        item.setForeground(QColor('#999999'))
                        item.setBackground(QColor('#ffffff'))
                        self.sensor_status_table.setItem(row, col, item)
            
            # Update plot if it exists
            if sensor_id in self.sensor_plots and sensor_id in self.sensor_history:
                plot_widget = self.sensor_plots[sensor_id]
                history = list(self.sensor_history[sensor_id])
                timestamps = list(self.sensor_timestamps[sensor_id])
                
                if history and len(history) == len(timestamps):
                    plot_widget.clear()
                    
                    # Professional line color based on status
                    if reading:
                        if reading.status == SensorStatus.OK:
                            color = '#ff6b35'  # Orange for normal operation
                        elif reading.status in [SensorStatus.LOW_ALARM, SensorStatus.HIGH_ALARM]:
                            color = '#ff4444'  # Red for alarms
                            has_alarm = True
                        elif reading.status == SensorStatus.FAULTY:
                            color = '#ff0000'  # Bright red for faulty
                            has_alarm = True
                        else:
                            color = '#ff6b35'  # Default orange
                    else:
                        color = '#ff6b35'  # Default orange
                    
                    # Filter data to show only last 10-20 seconds (rolling window)
                    current_time = timestamps[-1] if timestamps else datetime.now()
                    window_start_time = current_time - timedelta(seconds=self.plot_time_window)
                    
                    # Filter history and timestamps to rolling window
                    filtered_history = []
                    filtered_timestamps_numeric = []
                    for ts, val in zip(timestamps, history):
                        if ts >= window_start_time:
                            # Convert datetime to numeric (seconds since window start)
                            time_diff = (ts - window_start_time).total_seconds()
                            filtered_timestamps_numeric.append(time_diff)
                            filtered_history.append(val)
                    
                    if filtered_history and len(filtered_history) == len(filtered_timestamps_numeric):
                        # Plot with time on x-axis - thinner line for cleaner look
                        plot_widget.plot(filtered_timestamps_numeric, filtered_history, 
                                        pen=pg.mkPen(color=color, width=1.5, style=Qt.SolidLine),
                                        antialias=True)
                        
                        # Set fixed Y axis range based on sensor limits
                        if sensor_id in self.sensor_configs:
                            config = self.sensor_configs[sensor_id]
                            # Calculate range and add padding (10% above and below)
                            range_val = config.high_limit - config.low_limit
                            padding = range_val * 0.1 if range_val > 0 else 10
                            
                            # Set fixed y-axis range with 20 units below low_limit
                            plot_widget.setYRange(
                                config.low_limit - 20 - padding,
                                config.high_limit + padding
                            )
                            
                            # Add horizontal lines for alarm limits - professional dashed lines
                            plot_widget.addLine(y=config.low_limit, 
                                              pen=pg.mkPen(color='#ffaa00', width=1.5, style=Qt.DashLine))
                            plot_widget.addLine(y=config.high_limit, 
                                              pen=pg.mkPen(color='#ff4444', width=1.5, style=Qt.DashLine))
                        
                        # Set X-axis to show rolling window (10-20 seconds)
                        if filtered_timestamps_numeric:
                            plot_widget.setXRange(0, self.plot_time_window, padding=0)
                            
                            # Custom tick formatter for time axis (every 5 seconds)
                            tick_positions = []
                            tick_labels = []
                            for i in range(0, self.plot_time_window + 1, 5):  # Every 5 seconds
                                tick_positions.append(float(i))
                                tick_labels.append(f"{i}s")
                            
                            if tick_positions:
                                plot_widget.getAxis('bottom').setTicks([[(pos, label) for pos, label in zip(tick_positions, tick_labels)]])
            
            row += 1
        
        # Update system status (legacy)
        if has_alarm:
            self.system_status = "ALARM"
            if hasattr(self, 'status_label'):
                self.status_label.setText("System Status: ALARM")
                self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")
        else:
            self.system_status = "OK"
            if hasattr(self, 'status_label'):
                self.status_label.setText("System Status: OK")
                self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
    
    def update_system_status_indicator(self):
        """Update the global system status indicator"""
        if not hasattr(self, 'sensors_connections_label'):
            return
        
        # Count sensor statuses
        total_sensors = len(self.sensor_configs)
        connected_sensors = len(self.sensor_readings)
        healthy_count = sum(1 for r in self.sensor_readings.values() if r.status == SensorStatus.OK)
        faulty_count = sum(1 for r in self.sensor_readings.values() if r.status == SensorStatus.FAULTY)
        
        # Update sensors connections
        self.sensors_connections_label.setText(f"Connections: {connected_sensors}/{total_sensors}")
        
        # Update healthy sensors
        self.healthy_sensors_label.setText(f"Healthy: {healthy_count}")
        
        # Update faulty sensors
        self.faulty_sensors_label.setText(f"Faulty: {faulty_count}")
        
        # Update remote console status
        console_status = "Running" if (hasattr(self, 'console_started') and self.console_started) else "Stopped"
        console_color = "#2e7d32" if console_status == "Running" else "#c62828"
        self.remote_console_status_label.setText(f"Remote Console: {console_status}")
        self.remote_console_status_label.setStyleSheet(f"font-size: 12px; color: {console_color}; font-weight: bold;")
        
        # Update web server status
        webserver_status = "Running" if (hasattr(self, 'http_server') and self.http_server is not None) else "Stopped"
        webserver_color = "#2e7d32" if webserver_status == "Running" else "#c62828"
        self.webserver_status_label.setText(f"Web Server: {webserver_status}")
        self.webserver_status_label.setStyleSheet(f"font-size: 12px; color: {webserver_color}; font-weight: bold;")
    
    def clear_alarm_log(self):
        """Clear the alarm log (called from GUI button)"""
        reply = QMessageBox.question(self, 'Clear Alarm Log', 
                                    'Are you sure you want to clear the alarm log?',
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
        if reply == QMessageBox.Yes:
            alarm_count = len(self.alarm_log)
            self.alarm_table.setRowCount(0)
            self.alarm_log.clear()
            if self.remote_console:
                self.remote_console.alarm_log.clear()
            
            # Add log entry for alarm clearing from desktop app
            self.add_log_entry(f"Alarm log cleared from desktop application ({alarm_count} alarms removed)", "INFO")
            
            self.statusBar().showMessage("Alarm log cleared", 3000)
    
    def export_alarm_log_to_csv(self):
        """Export alarm log to CSV file"""
        import os
        import csv
        from PyQt5.QtWidgets import QFileDialog
        
        if not self.alarm_log:
            QMessageBox.information(self, "Export Alarm Log", 
                                  "No alarm data to export.")
            return
        
        # Get save location
        default_filename = f"alarm_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Alarm Log to CSV",
            default_filename,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not filepath:
            return  # User cancelled
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow([
                    'Timestamp', 'Sensor ID', 'Sensor Name', 'Value', 
                    'Alarm Type', 'Unit', 'Status'
                ])
                
                # Write alarm data
                for alarm in self.alarm_log:
                    writer.writerow([
                        alarm.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        alarm.sensor_id,
                        alarm.sensor_name,
                        f"{alarm.value:.2f}",
                        alarm.alarm_type,
                        alarm.unit,
                        'Active'
                    ])
            
            QMessageBox.information(self, "Export Successful", 
                                  f"Alarm log exported successfully to:\n{filepath}")
            self.statusBar().showMessage(f"Alarm log exported to {Path(filepath).name}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", 
                               f"Failed to export alarm log:\n{str(e)}")
            self.statusBar().showMessage("Export failed", 5000)
    
    def export_alarm_log_to_csv(self):
        """Export alarm log to CSV file"""
        import os
        import csv
        from PyQt5.QtWidgets import QFileDialog
        
        if not self.alarm_log:
            QMessageBox.information(self, "Export Alarm Log", 
                                  "No alarm data to export.")
            return
        
        # Get save location
        default_filename = f"alarm_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Alarm Log to CSV",
            default_filename,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not filepath:
            return  # User cancelled
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow([
                    'Timestamp', 'Sensor ID', 'Sensor Name', 'Value', 
                    'Alarm Type', 'Unit', 'Status'
                ])
                
                # Write alarm data
                for alarm in self.alarm_log:
                    writer.writerow([
                        alarm.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        alarm.sensor_id,
                        alarm.sensor_name,
                        f"{alarm.value:.2f}",
                        alarm.alarm_type,
                        alarm.unit,
                        'Active' if alarm in self.alarm_log else 'Cleared'
                    ])
            
            QMessageBox.information(self, "Export Successful", 
                                  f"Alarm log exported successfully to:\n{filepath}")
            self.statusBar().showMessage(f"Alarm log exported to {Path(filepath).name}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", 
                               f"Failed to export alarm log:\n{str(e)}")
            self.statusBar().showMessage("Export failed", 5000)
    
    def clear_alarm_log_from_remote(self):
        """Clear the alarm log (called from remote console - thread-safe)"""
        # This method is called from the remote console's asyncio thread
        # Emit signal to execute in GUI thread (thread-safe)
        self.alarm_clear_helper.clear_requested.emit()
    
    def _do_clear_alarm_log(self):
        """Actually clear the alarm log (executed in GUI thread)"""
        alarm_count = len(self.alarm_log)
        self.alarm_table.setRowCount(0)
        self.alarm_log.clear()
        # Note: remote console alarm log is already cleared by handle_clear_alarms
        
        # Add log entry for alarm clearing from remote console
        self.add_log_entry(f"Alarm log cleared from remote console ({alarm_count} alarms removed)", "INFO")
    
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
                # Fix for Windows: Create event loop with proper policy
                if sys.platform == 'win32':
                    # On Windows, create a new event loop with the proper policy
                    self.console_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self.console_loop)
                else:
                    # On Linux/Unix, use default event loop
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
                    # Clean up event loop
                    try:
                        self.console_loop.close()
                    except:
                        pass
            
            self.console_thread = threading.Thread(target=run_console, daemon=True)
            self.console_thread.start()
            
            # Initialize remote console with current sensor readings (non-blocking)
            # Use QTimer to defer this check until after thread has time to start
            def init_console_callback():
                if self.remote_console:
                    self.remote_console.set_sensor_readings(self.sensor_readings)
                    # Set callback to clear alarms in main GUI from remote console
                    self.remote_console.set_clear_alarms_callback(self.clear_alarm_log_from_remote)
                    self.console_started = True
                    http_port = console_config.get("http_port", 8080)
                    print(f"[OK] Remote Console Server started successfully on ws://{host}:{port}")
                    print(f"  Connect from web client at: http://localhost:{http_port}/web/remote_console_client.html")
                else:
                    print("✗ Failed to initialize Remote Console Server")
            
            # Defer initialization check to avoid blocking (Windows fix)
            QTimer.singleShot(500, init_console_callback)
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
            script_dir = Path(__file__).parent
            project_root = script_dir.parent
            
            # Get WebSocket URL from config
            ws_host = console_config.get("host", "localhost")
            ws_port = console_config.get("port", 8765)
            ws_url = f"ws://{ws_host}:{ws_port}"
            
            class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
                """Custom HTTP request handler"""
                
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(project_root), **kwargs)
                
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
                    # Handle favicon requests
                    if self.path == '/favicon.ico' or self.path == '/fav.png':
                        try:
                            # Load favicon from fav.png file
                            favicon_path = project_root / 'fav.png'
                            if favicon_path.exists():
                                with open(favicon_path, 'rb') as f:
                                    icon_data = f.read()
                                
                                self.send_response(200)
                                self.send_header('Content-type', 'image/png')
                                self.send_header('Content-length', str(len(icon_data)))
                                self.end_headers()
                                self.wfile.write(icon_data)
                                return
                            else:
                                # Fallback if file doesn't exist
                                self.send_response(204)
                                self.end_headers()
                                return
                        except Exception as e:
                            # Fallback to 204 if icon loading fails
                            print(f"Error loading favicon: {e}")
                            self.send_response(204)
                            self.end_headers()
                            return
                    
                    # Inject WebSocket URL into HTML file
                    if self.path == '/web/remote_console_client.html' or self.path == '/web/remote_console_client.html/':
                        try:
                            html_path = project_root / 'web' / 'remote_console_client.html'
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
                        print(f"[OK] HTTP Server started on http://localhost:{http_port}")
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
            
            # Server starts in background thread, no need to wait
            
        except Exception as e:
            print(f"Failed to start HTTP server: {e}")
            import traceback
            traceback.print_exc()
            self.http_server = None
    
    def _deferred_initialization(self):
        """Deferred initialization to prevent blocking during window creation (Windows fix)"""
        # Start remote console and HTTP server (non-blocking, in threads)
        self.start_remote_console()
        self.start_http_server()
        
        # Connect to sensors (may take time, but won't block window creation)
        self.connect_to_sensors()
        
        # Update remote console with initial sensor data after a delay
        QTimer.singleShot(1000, self.update_remote_console_initial)
    
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
    
    def update_reports_plots(self, metrics: dict):
        """Update plots in the Reports tab"""
        # Update sensor reports
        if hasattr(self, 'sensor_reports_table'):
            self.update_sensor_reports()
    
    def update_sensor_reports(self):
        """Update sensor reports table and plots"""
        if not hasattr(self, 'sensor_reports_table'):
            return
        
        row = 0
        healthy_count = 0
        alarm_count = 0
        faulty_count = 0
        
        # Colors for different sensor types
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336', '#00BCD4']
        
        # Clear sensor trends plot
        if hasattr(self, 'sensor_trends_plot'):
            self.sensor_trends_plot.clear()
            self.sensor_trends_plot.addLegend()
        
        for sensor_id, config in sorted(self.sensor_configs.items()):
            reading = self.sensor_readings.get(sensor_id)
            stats = self.sensor_stats.get(sensor_id, {
                'total_readings': 0,
                'ok_count': 0,
                'alarm_count': 0,
                'faulty_count': 0,
                'value_sum': 0.0,
                'alarm_events': 0
            })
            
            if reading:
                # Update current value (column 1)
                value_str = f"{reading.value:.2f} {config.unit}"
                self.sensor_reports_table.setItem(row, 1, QTableWidgetItem(value_str))
                
                # Update status/state (column 2)
                status_item = QTableWidgetItem(reading.status.value)
                if reading.status == SensorStatus.OK:
                    status_item.setBackground(QColor(200, 255, 200))
                    healthy_count += 1
                elif reading.status in [SensorStatus.LOW_ALARM, SensorStatus.HIGH_ALARM]:
                    status_item.setBackground(QColor(255, 235, 200))
                    alarm_count += 1
                else:
                    status_item.setBackground(QColor(255, 200, 200))
                    faulty_count += 1
                self.sensor_reports_table.setItem(row, 2, status_item)
                
                # Add to trends plot
                if hasattr(self, 'sensor_trends_plot') and sensor_id in self.sensor_history:
                    history = list(self.sensor_history[sensor_id])
                    if history:
                        color_idx = sensor_id % len(colors)
                        pen = pg.mkPen(color=colors[color_idx], width=2)
                        self.sensor_trends_plot.plot(
                            history, 
                            pen=pen, 
                            name=f"{config.name} (ID: {sensor_id})"
                        )
            else:
                # No data yet
                self.sensor_reports_table.setItem(row, 1, QTableWidgetItem("--"))
                self.sensor_reports_table.setItem(row, 2, QTableWidgetItem("No Data"))
            
            row += 1
        
        # Update summary labels
        if hasattr(self, 'healthy_sensors_label'):
            self.healthy_sensors_label.setText(f"Healthy: {healthy_count}")
        if hasattr(self, 'alarm_sensors_label'):
            self.alarm_sensors_label.setText(f"In Alarm: {alarm_count}")
        if hasattr(self, 'faulty_sensors_label'):
            self.faulty_sensors_label.setText(f"Faulty: {faulty_count}")
        if hasattr(self, 'total_sensors_label'):
            self.total_sensors_label.setText(f"Total: {len(self.sensor_configs)}")


def main():
    """Main entry point"""
    # Fix for Windows: Set asyncio event loop policy before creating QApplication
    # This prevents hangs on Windows when mixing asyncio with PyQt5
    if sys.platform == 'win32':
        # Use ProactorEventLoopPolicy on Windows for better compatibility
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    app = QApplication(sys.argv)
    
    # Set application icon early (before creating window) for taskbar icon
    # This ensures the icon appears in taskbar on both Windows and Linux
    # On Windows, the icon must be set on QApplication before creating any windows
    try:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        icon_path = project_root / 'fav.png'
        if icon_path.exists():
            # Use absolute path for better Windows compatibility
            abs_icon_path = str(icon_path.resolve())
            
            # On Windows, try to create icon with proper sizes for better taskbar display
            if sys.platform == 'win32':
                try:
                    # Load as pixmap first, then create icon with multiple sizes
                    pixmap = QPixmap(abs_icon_path)
                    if not pixmap.isNull():
                        icon = QIcon()
                        # Add multiple sizes for Windows (16x16, 32x32, 48x48, 256x256)
                        sizes = [16, 32, 48, 256]
                        for size in sizes:
                            scaled = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            icon.addPixmap(scaled)
                        # Also add the original
                        icon.addPixmap(pixmap)
                    else:
                        icon = QIcon(abs_icon_path)
                except Exception:
                    icon = QIcon(abs_icon_path)
            else:
                icon = QIcon(abs_icon_path)
            
            # Verify icon is valid
            if not icon.isNull():
                # Set on QApplication first (required for Windows taskbar)
                QApplication.setWindowIcon(icon)
                app.setWindowIcon(icon)
                print(f"Application icon set from: {abs_icon_path}")
            else:
                print(f"Warning: Icon file exists but could not be loaded: {abs_icon_path}")
        else:
            print(f"Warning: Icon file not found at: {icon_path}")
    except Exception as e:
        print(f"Warning: Could not set application icon: {e}")
        import traceback
        traceback.print_exc()
    
    window = MainWindow()
    # Ensure window icon is also set (Windows sometimes needs both)
    try:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        icon_path = project_root / 'fav.png'
        if icon_path.exists():
            abs_icon_path = str(icon_path.resolve())
            icon = QIcon(abs_icon_path)
            if not icon.isNull():
                window.setWindowIcon(icon)
    except Exception as e:
        pass  # Already set in set_application_icon()
    
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


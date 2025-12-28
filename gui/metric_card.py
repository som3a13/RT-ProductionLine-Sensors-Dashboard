"""
Metric Card Widget for Dashboard
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QIcon
from .circular_progress import CircularProgressWidget


class MetricCard(QWidget):
    """Card widget displaying a metric with circular progress"""
    
    def __init__(self, title, parent=None, color=QColor(0, 150, 255)):
        super().__init__(parent)
        self.title = title
        self.color = color
        self.value = 0
        self.trend = 0
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Card styling
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        # Header with info icon
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        
        # Info button (small 'i' icon)
        info_btn = QPushButton("i")
        info_btn.setFixedSize(20, 20)
        info_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                color: #666;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        info_btn.setToolTip(f"Information about {self.title}")
        header_layout.addWidget(info_btn)
        
        layout.addLayout(header_layout)
        
        # Circular progress widget (text is drawn inside by the widget itself)
        self.progress_widget = CircularProgressWidget(self, size=180, line_width=25)
        self.progress_widget.set_color(self.color)
        layout.addWidget(self.progress_widget, alignment=Qt.AlignCenter)
        
        # Title label
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-top: 10px;")
        layout.addWidget(title_label)
        
        # Trend indicator
        trend_layout = QHBoxLayout()
        trend_layout.addStretch()
        
        self.trend_label = QLabel("+0%")
        self.trend_label.setStyleSheet("font-size: 14px; color: #4CAF50; font-weight: bold;")
        trend_layout.addWidget(self.trend_label)
        
        # Green arrow (using Unicode)
        arrow_label = QLabel("↑")
        arrow_label.setStyleSheet("font-size: 16px; color: #4CAF50; font-weight: bold;")
        trend_layout.addWidget(arrow_label)
        
        trend_layout.addStretch()
        layout.addLayout(trend_layout)
    
    def set_value(self, value):
        """Set the metric value (0-100)"""
        self.value = max(0, min(100, value))
        self.progress_widget.set_value(self.value)
    
    def set_trend(self, trend):
        """Set the trend percentage"""
        self.trend = trend
        if trend >= 0:
            self.trend_label.setText(f"+{trend:.1f}%")
            self.trend_label.setStyleSheet("font-size: 14px; color: #4CAF50; font-weight: bold;")
        else:
            self.trend_label.setText(f"{trend:.1f}%")
            self.trend_label.setStyleSheet("font-size: 14px; color: #F44336; font-weight: bold;")
    
    def set_color(self, color):
        """Set the progress color"""
        self.color = color
        self.progress_widget.set_color(color)


"""
Circular Progress Widget for Dashboard Metrics
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QFont, QPen
import math


class CircularProgressWidget(QWidget):
    """Custom circular progress indicator"""
    
    def __init__(self, parent=None, size=200, line_width=20):
        super().__init__(parent)
        self.size = size
        self.line_width = line_width
        self.value = 0  # 0-100
        self.color = QColor(0, 150, 255)  # Default blue
        self.setMinimumSize(size, size)
        self.setMaximumSize(size, size)
    
    def set_value(self, value):
        """Set progress value (0-100)"""
        self.value = max(0, min(100, value))
        self.update()
    
    def set_color(self, color):
        """Set progress color"""
        self.color = color
        self.update()
    
    def paintEvent(self, event):
        """Draw the circular progress"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate dimensions
        rect = QRectF(0, 0, self.width(), self.height())
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2 - self.line_width / 2
        
        # Draw background circle
        bg_pen = QPen(QColor(230, 230, 230), self.line_width)
        painter.setPen(bg_pen)
        painter.drawEllipse(center, radius, radius)
        
        # Draw progress arc
        if self.value > 0:
            progress_pen = QPen(self.color, self.line_width)
            progress_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(progress_pen)
            
            # Calculate angle (270 degrees = top, clockwise)
            start_angle = 90 * 16  # Start from top (in 1/16th degrees)
            span_angle = -int(self.value * 3.6 * 16)  # Convert percentage to degrees
            
            painter.drawArc(
                int(center.x() - radius),
                int(center.y() - radius),
                int(radius * 2),
                int(radius * 2),
                start_angle,
                span_angle
            )
        
        # Draw percentage text in center
        font = QFont()
        font.setPointSize(36)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self.color)
        text = f"{int(self.value)}%"
        text_rect = QRectF(0, 0, self.width(), self.height())
        painter.drawText(text_rect, Qt.AlignCenter, text)


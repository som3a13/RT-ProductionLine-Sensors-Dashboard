"""
Non-resizable splitter component

Author: Mohammed Ismail AbdElmageid
"""
from PyQt5.QtWidgets import QSplitter
from PyQt5.QtCore import Qt, QEvent


class NonResizableSplitter(QSplitter):
    """Custom splitter that cannot be resized by user"""
    
    def __init__(self, orientation):
        super().__init__(orientation)
        self.setChildrenCollapsible(False)
    
    def mousePressEvent(self, event):
        """Override to prevent mouse press on splitter handle"""
        # Check if click is on a handle
        handle_index = self.handleAt(event.pos())
        if handle_index >= 0:
            # Block the event completely
            event.ignore()
            return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Override to prevent mouse move for resizing"""
        # Always ignore mouse move events to prevent resizing
        event.ignore()
        return
    
    def mouseReleaseEvent(self, event):
        """Override to prevent mouse release after drag"""
        # Check if release is on a handle
        handle_index = self.handleAt(event.pos())
        if handle_index >= 0:
            event.ignore()
            return
        super().mouseReleaseEvent(event)
    
    def createHandle(self):
        """Create a non-interactive handle"""
        handle = super().createHandle()
        handle.setEnabled(False)
        handle.setCursor(Qt.ArrowCursor)
        # Install event filter on handle to block all mouse events
        handle.installEventFilter(self)
        return handle
    
    def eventFilter(self, obj, event):
        """Event filter to block all mouse events on handles"""
        # Check if the object is one of our handles
        for i in range(self.count() - 1):
            if obj == self.handle(i):
                if event.type() in [QEvent.MouseButtonPress, QEvent.MouseMove, 
                                    QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick]:
                    return True  # Block the event
        return super().eventFilter(obj, event)









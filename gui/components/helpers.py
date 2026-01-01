"""
Helper classes for GUI

Author: Mohammed Ismail AbdElmageid
"""
from PyQt5.QtCore import QObject, pyqtSignal


class AlarmClearHelper(QObject):
    """Helper class for thread-safe alarm clearing"""
    clear_requested = pyqtSignal()
    
    def __init__(self, target_method):
        super().__init__()
        self.clear_requested.connect(target_method)









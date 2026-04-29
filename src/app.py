"""
Main application class for Webpage Launcher.
"""

import sys
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow


class WebpageLauncherApp:
    """Main application controller."""

    def __init__(self):
        """Initialize the application."""
        self.qt_app = QApplication(sys.argv)
        self.main_window = MainWindow()

    def run(self):
        """Run the application."""
        self.main_window.show()
        return self.qt_app.exec_()

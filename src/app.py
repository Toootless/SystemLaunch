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
        
        # Check if we should auto-launch
        self.auto_launch = "--auto-launch" in sys.argv

    def run(self):
        """Run the application."""
        if self.auto_launch:
            # Auto-launch all apps without showing GUI
            try:
                self.main_window.launch_all()
                # Close immediately after launching
                self.qt_app.quit()
                return 0
            except Exception as e:
                print(f"Error during auto-launch: {e}")
                return 1
        else:
            # Show GUI normally
            self.main_window.show()
            return self.qt_app.exec_()

"""
Monitor detection and management.
"""

import pygetwindow as gw


class MonitorManager:
    """Manages multi-monitor detection and information."""

    def __init__(self):
        """Initialize the monitor manager."""
        self.monitors = []
        self.detect_monitors()

    def detect_monitors(self):
        """Detect all connected monitors."""
        # TODO: Implement monitor detection using Windows API
        # For now, we'll use a placeholder
        pass

    def get_monitor_count(self):
        """Get the number of connected monitors."""
        return len(self.monitors)

    def get_monitor_info(self, monitor_index):
        """Get information about a specific monitor."""
        if 0 <= monitor_index < len(self.monitors):
            return self.monitors[monitor_index]
        return None

    def get_all_monitors(self):
        """Get information about all monitors."""
        return self.monitors

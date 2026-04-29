"""
DisplayFusion API wrapper for window positioning.
"""

import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional
import json
import tempfile
from datetime import datetime


class LaunchLogger:
    """Simple logger to capture launch events."""
    def __init__(self):
        self.log_file = Path(__file__).parent.parent.parent / "launch_log.txt"
    
    def log(self, message: str):
        """Write message to log file."""
        with open(self.log_file, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        print(message)
    
    def clear(self):
        """Clear the log file."""
        self.log_file.write_text("")


class DisplayFusionManager:
    """Manages DisplayFusion scripting and window positioning."""

    # Monitor layout configuration (describes visual arrangement, not tab limits)
    MONITOR_LAYOUTS = {
        1: {"layout": "split-left-right", "sections": 2, "cols": 2, "rows": 1},
        2: {"layout": "grid-2x3", "sections": 6, "cols": 3, "rows": 2},
        3: {"layout": "full-screen", "sections": 1, "cols": 1, "rows": 1},
        4: {"layout": "full-screen", "sections": 1, "cols": 1, "rows": 1},
        5: {"layout": "split-left-right-groups", "sections": 2, "cols": 2, "rows": 1},
    }

    # Display name mapping
    DISPLAY_NAMES = {
        1: "DISPLAY6",
        2: "DISPLAY7",
        3: "DISPLAY1",
        4: "DISPLAY2",
        5: "DISPLAY3",
    }

    def __init__(self):
        """Initialize the DisplayFusion manager."""
        self.logger = LaunchLogger()
        self.logger.clear()
        self.logger.log("="*60)
        self.logger.log("Webpage Launcher Started")
        self.logger.log("="*60)
        
        self.displayfusion_path = self.find_displayfusion()
        self.monitor_info = {}
        self.detect_monitors()

    def find_displayfusion(self) -> Optional[Path]:
        """Locate DisplayFusion executable."""
        common_paths = [
            Path("C:\\Program Files\\DisplayFusion\\DisplayFusion.exe"),
            Path("C:\\Program Files (x86)\\DisplayFusion\\DisplayFusion.exe"),
        ]

        for path in common_paths:
            if path.exists():
                return path

        return None

    def detect_monitors(self):
        """Detect connected monitors and their dimensions."""
        try:
            import screeninfo
            monitors = screeninfo.get_monitors()
            for i, monitor in enumerate(monitors, 1):
                self.monitor_info[i] = {
                    "width": monitor.width,
                    "height": monitor.height,
                    "x": monitor.x,
                    "y": monitor.y,
                }
        except Exception as e:
            print(f"Error detecting monitors: {e}")

    def get_field_bounds(self, monitor: int, field_index: int, location_id: str = None) -> Tuple[int, int, int, int]:
        """
        Calculate window bounds for a specific field on a monitor.
        
        Args:
            monitor: Monitor number
            field_index: 0-based field index
            location_id: Optional location identifier (top-left, center, etc.)
        
        Returns: (x, y, width, height)
        """
        if monitor not in self.monitor_info:
            return (0, 0, 800, 600)

        layout = self.MONITOR_LAYOUTS.get(monitor, {"fields": 1, "cols": 1, "rows": 1})
        mon_info = self.monitor_info[monitor]

        cols = layout["cols"]
        rows = layout["rows"]

        col = field_index % cols
        row = field_index // cols

        x = mon_info["x"] + (col * mon_info["width"]) // cols
        y = mon_info["y"] + (row * mon_info["height"]) // rows
        width = mon_info["width"] // cols
        height = mon_info["height"] // rows

        return (x, y, width, height)

    def create_displayfusion_script(self, monitor: int, position: int, location_id: str, app_type: str, target: str) -> str:
        """
        Create a DisplayFusion script to launch and position an application.
        """
        x, y, width, height = self.get_field_bounds(monitor, position - 1, location_id)

        if app_type.lower() == "chrome":
            script = f"""
// DisplayFusion Script to open Chrome tab and position window
// Location: {location_id}
BFS.Window.MoveToMonitor({monitor}, "{target}");
var w = BFS.Window.WaitForWindow(0, 6000);
if (w > 0) {{
    BFS.Window.SetWindowPosition(w, {x}, {y}, {width}, {height});
}}
"""
        else:  # program
            script = f"""
// DisplayFusion Script to launch program and position window
// Location: {location_id}
BFS.Process.Start("{target}");
var w = BFS.Window.WaitForWindow(1000, 6000);
if (w > 0) {{
    BFS.Window.SetWindowPosition(w, {x}, {y}, {width}, {height});
}}
"""
        return script

    def launch_apps(self, app_configs: list):
        """
        Launch all applications using DisplayFusion.
        
        Args:
            app_configs: List of AppConfig objects
        """
        self.logger.log(f"\n{'='*60}")
        self.logger.log(f"Starting to launch {len(app_configs)} applications...")
        self.logger.log(f"{'='*60}\n")
        
        if not self.displayfusion_path:
            self.logger.log("WARNING: DisplayFusion not found. Using fallback launch mode.")
        
        for i, config in enumerate(app_configs, 1):
            try:
                self.logger.log(f"[{i}/{len(app_configs)}] Launching {config.app_type.upper()}: {config.target}")
                if config.app_type.lower() == "chrome":
                    self._launch_chrome(config)
                else:
                    self._launch_program(config)
                self.logger.log(f"  [OK] Success\n")
            except Exception as e:
                self.logger.log(f"  [ERROR] {e}\n")
        
        # After all apps launched, position windows
        self.logger.log(f"\n{'='*60}")
        self.logger.log("Positioning windows to monitors...")
        self.logger.log(f"{'='*60}\n")
        
        import time
        time.sleep(2)  # Give apps time to open
        
        self._position_windows(app_configs)

    def _launch_chrome(self, config):
        """Launch a Chrome tab and position it."""
        from src.core.chrome_manager import ChromeManager
        chrome_mgr = ChromeManager()
        
        display_name = self.DISPLAY_NAMES.get(config.monitor, f"DISPLAY{config.monitor}")
        if chrome_mgr.open_url(config.target):
            # Position the window (DisplayFusion will handle this)
            self.logger.log(f"Opened Chrome tab on Monitor {config.monitor} ({display_name}), Location {config.location_id}: {config.target[:60]}...")
        else:
            self.logger.log(f"Failed to open Chrome tab: {config.target}")

    def _launch_program(self, config):
        """Launch a program and position it."""
        x, y, width, height = self.get_field_bounds(config.monitor, config.position - 1, config.location_id)
        
        display_name = self.DISPLAY_NAMES.get(config.monitor, f"DISPLAY{config.monitor}")
        try:
            import os
            import shutil
            
            # Try to find the program
            program_name = config.target
            
            self.logger.log(f"    Searching for: {program_name}")
            
            # Check if it's a full path
            if Path(program_name).exists():
                self.logger.log(f"    Found at: {program_name}")
                os.startfile(str(program_name))
                self.logger.log(f"    Launched via os.startfile()")
            else:
                import shutil
                # Try to find in PATH
                found_path = shutil.which(program_name)
                if found_path:
                    self.logger.log(f"    Found in PATH: {found_path}")
                    os.startfile(str(found_path))
                    self.logger.log(f"    Launched via os.startfile()")
                else:
                    # Try common application paths with more thorough search
                    self.logger.log(f"    Not in PATH, checking common locations...")
                    possible_paths = [
                        # Direct Program Files searches
                        Path("C:\\Program Files") / program_name,
                        Path("C:\\Program Files (x86)") / program_name,
                        Path.home() / "AppData" / "Local" / "Programs" / program_name,
                        
                        # Specific common apps - VS Code
                        Path.home() / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "Code.exe" if "code" in program_name.lower() else None,
                        Path("C:\\Program Files\\Microsoft VS Code\\Code.exe") if "code" in program_name.lower() else None,
                        
                        # Common app folder locations with executable
                        Path("C:\\Program Files") / program_name / (program_name + ".exe"),
                        Path("C:\\Program Files (x86)") / program_name / (program_name + ".exe"),
                        
                        # AppData programs
                        Path.home() / "AppData" / "Local" / "Programs" / program_name / (program_name + ".exe"),
                        Path.home() / "AppData" / "Local" / program_name / (program_name + ".exe"),
                    ]
                    
                    found = False
                    for path in possible_paths:
                        if path and path.exists():
                            self.logger.log(f"    Found at: {path}")
                            os.startfile(str(path))
                            self.logger.log(f"    Launched via os.startfile()")
                            found = True
                            break
                    
                    if not found:
                        self.logger.log(f"    [NOT FOUND] anywhere")
                        self.logger.log(f"    Tried: {program_name}, PATH, Program Files, AppData")
                        return
            
            self.logger.log(f"    [LAUNCHED] on Monitor {config.monitor} ({display_name}), Location {config.location_id}")
        except Exception as e:
            self.logger.log(f"    Exception: {e}")

    def _launch_without_displayfusion(self, app_configs: list):
        """Launch apps without DisplayFusion (fallback)."""
        from src.core.chrome_manager import ChromeManager
        import subprocess
        
        chrome_mgr = ChromeManager()
        
        for config in app_configs:
            try:
                if config.app_type.lower() == "chrome":
                    chrome_mgr.open_url(config.target)
                else:
                    subprocess.Popen(config.target)
            except Exception as e:
                print(f"Error launching {config.target}: {e}")
    
    def _position_windows(self, app_configs: list):
        """Position all launched windows to their assigned monitors and locations."""
        try:
            import pygetwindow as gw
            import time
        except ImportError:
            self.logger.log("WARNING: pygetwindow not available for window positioning")
            return
        
        for config in app_configs:
            try:
                x, y, width, height = self.get_field_bounds(config.monitor, config.position - 1, config.location_id)
                
                display_name = self.DISPLAY_NAMES.get(config.monitor, f"DISPLAY{config.monitor}")
                self.logger.log(f"Positioning {config.app_type.upper()}: {config.target[:40]}")
                self.logger.log(f"  Target: Monitor {config.monitor} ({display_name}), Location {config.location_id}")
                self.logger.log(f"  Bounds: ({x}, {y}) {width}x{height}")
                
                # Find the window
                windows = gw.getAllWindows()
                target_window = None
                
                if config.app_type.lower() == "chrome":
                    # For Chrome, look for window with URL title
                    for win in windows:
                        if "chrome" in win.title.lower() and len(win.title) > 10:
                            # Skip if already positioned
                            if win.left != 0 or win.top != 0:
                                target_window = win
                                break
                else:
                    # For programs, look for window with program name
                    program_name = config.target
                    for win in windows:
                        if program_name.replace(".exe", "").lower() in win.title.lower():
                            target_window = win
                            break
                
                if target_window:
                    self.logger.log(f"  Found window: {target_window.title[:50]}")
                    try:
                        target_window.moveTo(x, y)
                        target_window.resizeTo(width, height)
                        self.logger.log(f"  [POSITIONED] to Monitor {config.monitor}")
                    except Exception as e:
                        self.logger.log(f"  Could not position: {e}")
                else:
                    self.logger.log(f"  Window not found")
                
                self.logger.log("")
                
            except Exception as e:
                self.logger.log(f"  Error positioning: {e}\n")

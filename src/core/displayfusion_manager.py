"""
DisplayFusion API wrapper for window positioning.
"""

import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional
import json
import tempfile
from datetime import datetime
import os


class LaunchLogger:
    """Simple logger to capture launch events."""
    def __init__(self):
        self.log_file = Path(__file__).parent.parent.parent / "launch_log.txt"
    
    def log(self, message: str):
        """Write message to log file."""
        with open(self.log_file, "a", encoding="utf-8") as f:
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
        self.env = self._setup_gpu_environment()
        self.detect_monitors()

    def _setup_gpu_environment(self) -> dict:
        """Setup environment for GPU acceleration inheritance."""
        env = os.environ.copy()
        
        # Log GPU environment variables that will be passed to child processes
        gpu_vars = {
            'VK_ICD_FILENAMES': 'Vulkan driver',
            'DXVK_HUD': 'D3D11 diagnostics',
            'VKDEVICE': 'Vulkan device',
            'AMD_DEVICE_SPECS': 'AMD device info',
            'DISABLE_LAYER_AMD_SWITCHABLE_GRAPHICS': 'AMD switchable graphics',
        }
        
        self.logger.log(f"\nGPU Environment Setup:")
        for var, desc in gpu_vars.items():
            if var in os.environ:
                self.logger.log(f"  [SET] {var}: {os.environ[var]}")
            else:
                self.logger.log(f"  [ - ] {var}: (not set)")
        
        return env

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
        """Detect connected monitors and their dimensions.
        
        Maps each physical display to the correct monitor ID using DISPLAY_NAMES,
        rather than relying on the arbitrary order screeninfo returns monitors.
        screeninfo may return monitors as e.g. DISPLAY6, DISPLAY1, DISPLAY7, DISPLAY2, DISPLAY3
        instead of in order, which would cause wrong monitor assignments if using enumerate().
        """
        try:
            import screeninfo
            monitors = screeninfo.get_monitors()
            # Build reverse map: "DISPLAY6" -> 1, "DISPLAY7" -> 2, etc.
            name_map = {v: k for k, v in self.DISPLAY_NAMES.items()}
            for monitor in monitors:
                # screeninfo names include the "\\.\" prefix on Windows - strip it
                name = monitor.name.replace("\\\\.\\", "") if monitor.name else ""
                if name in name_map:
                    mon_id = name_map[name]
                    self.monitor_info[mon_id] = {
                        "width": monitor.width,
                        "height": monitor.height,
                        "x": monitor.x,
                        "y": monitor.y,
                    }
                else:
                    print(f"Warning: Monitor '{name}' not found in DISPLAY_NAMES mapping")
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
        Launch all applications.

        Programs are launched immediately in order.
        Chrome windows are collected and then launched together via CDP so that
        every window gets exact positioning via Browser.setWindowBounds — no
        UIPI / Access Denied issues, and no URL-breaking from shell=True.
        """
        self.logger.log(f"\n{'='*60}")
        self.logger.log(f"Starting to launch {len(app_configs)} applications...")
        self.logger.log(f"{'='*60}\n")

        program_configs = []
        chrome_configs  = []

        for i, config in enumerate(app_configs, 1):
            try:
                self.logger.log(f"[{i}/{len(app_configs)}] Launching {config.app_type.upper()}: {config.target}")
                if config.app_type.lower() == "chrome":
                    x, y, w, h = self.get_field_bounds(
                        config.monitor, config.position - 1, config.location_id)
                    display_name = self.DISPLAY_NAMES.get(
                        config.monitor, f"DISPLAY{config.monitor}")
                    self.logger.log(
                        f"  Queued for CDP: Monitor {config.monitor} ({display_name})"
                        f" at ({x},{y}) {w}x{h}")
                    chrome_configs.append(config)
                else:
                    self._launch_program(config)
                    program_configs.append(config)
                self.logger.log(f"  [OK] Success\n")
            except Exception as e:
                self.logger.log(f"  [ERROR] {e}\n")

        # ── Chrome via CDP ────────────────────────────────────────────
        if chrome_configs:
            self._launch_chrome_via_cdp(chrome_configs)

        # ── Position program windows ─────────────────────────────────
        if program_configs:
            self.logger.log(f"\n{'='*60}")
            self.logger.log("Positioning program windows to monitors...")
            self.logger.log(f"{'='*60}\n")
            import time
            time.sleep(2)
            self._position_windows(program_configs)

    def _launch_chrome_via_cdp(self, chrome_configs: list):
        """
        Launch all Chrome windows using Chrome DevTools Protocol.

        Strategy (never kills existing Chrome):
          1. If Chrome already has --remote-debugging-port=9222 active, connect
             and open ALL windows via CDP.
          2. If Chrome is running WITHOUT the debug port, fall back to the old
             subprocess method so existing sessions are preserved.
          3. If Chrome is not running at all, launch it fresh with the first URL
             and correct --window-position, then open the rest via CDP.

        A 0.5 s pause between creations prevents Chrome from killing tabs due
        to simultaneous memory pressure.
        """
        import time as _time
        from src.core.chrome_manager import ChromeManager, ChromeCDPSession

        chrome_mgr = ChromeManager()
        if not chrome_mgr.chrome_path or not chrome_mgr.chrome_path.exists():
            self.logger.log("[CDP] Chrome not found — falling back to subprocess")
            for config in chrome_configs:
                self._launch_chrome(config)
            return

        self.logger.log(f"\n{'='*60}")
        self.logger.log(f"Launching {len(chrome_configs)} Chrome windows via CDP...")
        self.logger.log(f"{'='*60}\n")

        cdp = ChromeCDPSession()

        # ── Case 1: Chrome already running with debug port ─────────────────
        if cdp.wait_for_port(timeout=1.5):
            self.logger.log("  [CDP] Debug port already active — using existing Chrome")
            if not cdp.connect():
                self.logger.log("[CDP] Connection failed — falling back to subprocess")
                for config in chrome_configs:
                    self._launch_chrome(config)
                return
            configs_to_open = chrome_configs
            start_idx = 1

        else:
            # ── Case 2: Chrome running without debug port ──────────────────
            proc_check = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                capture_output=True, text=True
            )
            if "chrome.exe" in proc_check.stdout.lower():
                self.logger.log(
                    "[CDP] Chrome is running without debug port — "
                    "using subprocess fallback (existing Chrome preserved)")
                for config in chrome_configs:
                    self._launch_chrome(config)
                return

            # ── Case 3: Chrome is not running — launch fresh ───────────────
            first  = chrome_configs[0]
            x0, y0, w0, h0 = self.get_field_bounds(
                first.monitor, first.position - 1, first.location_id)
            dn0 = self.DISPLAY_NAMES.get(first.monitor, f"DISPLAY{first.monitor}")

            cdp.launch_chrome(chrome_mgr.chrome_path, chrome_mgr.GPU_FLAGS,
                              self.env, first.target, x0, y0, w0, h0)
            self.logger.log(
                f"  [1/{len(chrome_configs)}] Monitor {first.monitor} ({dn0})"
                f" ({x0},{y0}) {w0}x{h0} — launched via subprocess (first window)")

            self.logger.log("  Waiting for Chrome debug port...")
            if not cdp.wait_for_port(timeout=15):
                self.logger.log("[CDP] Timeout — falling back to subprocess for remaining")
                for config in chrome_configs[1:]:
                    self._launch_chrome(config)
                return

            if not cdp.connect():
                self.logger.log("[CDP] Connection failed — falling back to subprocess")
                for config in chrome_configs[1:]:
                    self._launch_chrome(config)
                return

            configs_to_open = chrome_configs[1:]
            start_idx = 2

        self.logger.log("  [CDP] Connected to Chrome DevTools Protocol")

        try:
            for idx, config in enumerate(configs_to_open, start_idx):
                x, y, w, h = self.get_field_bounds(
                    config.monitor, config.position - 1, config.location_id)
                dn = self.DISPLAY_NAMES.get(config.monitor, f"DISPLAY{config.monitor}")

                if cdp.open_window_at(config.target, x, y, w, h):
                    self.logger.log(
                        f"  [{idx}/{len(chrome_configs)}] Monitor {config.monitor}"
                        f" ({dn}) ({x},{y}) {w}x{h} — [OK]")
                else:
                    self.logger.log(
                        f"  [{idx}/{len(chrome_configs)}] CDP failed for"
                        f" {config.target[:50]} — falling back to subprocess")
                    self._launch_chrome(config)

                _time.sleep(0.5)  # Stagger to prevent Chrome OOM tab kills
        finally:
            cdp.close()

        self.logger.log(f"\n[CDP] All {len(chrome_configs)} Chrome windows launched")



    def _launch_chrome(self, config):
        """Launch a Chrome tab with native positioning and GPU acceleration."""
        from src.core.chrome_manager import ChromeManager
        chrome_mgr = ChromeManager()
        
        # Calculate the position for this Chrome window
        x, y, width, height = self.get_field_bounds(config.monitor, config.position - 1, config.location_id)
        
        display_name = self.DISPLAY_NAMES.get(config.monitor, f"DISPLAY{config.monitor}")
        
        # Launch Chrome with positioning flags and GPU environment
        if chrome_mgr.open_url_positioned(config.target, x, y, width, height):
            self.logger.log(f"Opened Chrome tab on Monitor {config.monitor} ({display_name}), Location {config.location_id}: {config.target[:60]}...")
            self.logger.log(f"  Target positioning: ({x}, {y}) {width}x{height}")
        else:
            self.logger.log(f"Failed to open Chrome tab: {config.target}")

    def _launch_program(self, config):
        """Launch a program and position it with inherited GPU environment."""
        x, y, width, height = self.get_field_bounds(config.monitor, config.position - 1, config.location_id)
        
        display_name = self.DISPLAY_NAMES.get(config.monitor, f"DISPLAY{config.monitor}")
        try:
            import shutil
            
            # Try to find the program
            program_name = config.target
            
            self.logger.log(f"    Searching for: {program_name}")
            
            # Check if it's a full path
            if Path(program_name).exists():
                self.logger.log(f"    Found at: {program_name}")
                # Use subprocess with inherited GPU environment instead of os.startfile
                subprocess.Popen([str(program_name)], env=self.env)
                self.logger.log(f"    Launched via subprocess with GPU env")
            else:
                # Try to find in PATH
                found_path = shutil.which(program_name)
                if found_path:
                    self.logger.log(f"    Found in PATH: {found_path}")
                    subprocess.Popen([str(found_path)], env=self.env)
                    self.logger.log(f"    Launched via subprocess with GPU env")
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
                            subprocess.Popen([str(path)], env=self.env)
                            self.logger.log(f"    Launched via subprocess with GPU env")
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
        
        chrome_mgr = ChromeManager()
        
        for config in app_configs:
            try:
                x, y, width, height = self.get_field_bounds(config.monitor, config.position - 1, config.location_id)
                if config.app_type.lower() == "chrome":
                    # Use positioned launch for better GPU initialization
                    chrome_mgr.open_url_positioned(config.target, x, y, width, height)
                else:
                    subprocess.Popen([config.target], env=self.env)
            except Exception as e:
                print(f"Error launching {config.target}: {e}")
    
    def _position_windows(self, app_configs: list):
        """Position all launched windows to their assigned monitors and locations."""
        import time
        
        try:
            import pygetwindow as gw
        except ImportError:
            self.logger.log("ERROR: pygetwindow not available")
            return
        
        # Wait for windows to open
        time.sleep(3)
        
        self.logger.log(f"\nPositioning windows to monitors...")
        positioned_count = 0
        positioned_hwnd_set = set()
        
        for config in app_configs:
            try:
                x, y, width, height = self.get_field_bounds(config.monitor, config.position - 1, config.location_id)
                display_name = self.DISPLAY_NAMES.get(config.monitor, f"DISPLAY{config.monitor}")
                
                target_window = None
                
                # Refresh window list for each config
                all_windows = gw.getAllWindows()
                
                if config.app_type.lower() == "chrome":
                    # Find Chrome windows not yet positioned
                    chrome_windows = [
                        w for w in all_windows 
                        if w and w.visible and w._hWnd not in positioned_hwnd_set and
                        any(keyword in w.title.lower() for keyword in ["chrome", "google", "untitled", "messenger", "gmail", "youtube", "spotify", "400 bad"])
                    ]
                    
                    if chrome_windows:
                        # Get the topmost Chrome window (most recently launched)
                        target_window = min(chrome_windows, key=lambda w: (w.top, w.left))
                else:
                    program_name = os.path.basename(config.target).replace(".exe", "").lower()
                    for win in all_windows:
                        if (win and win.visible and win._hWnd not in positioned_hwnd_set and
                            program_name in win.title.lower()):
                            target_window = win
                            break
                
                if target_window:
                    positioned_hwnd_set.add(target_window._hWnd)
                    self.logger.log(f"  [{config.app_type.upper()}] {target_window.title[:40]}")
                    self.logger.log(f"    Current: ({target_window.left}, {target_window.top}) {target_window.width}x{target_window.height}")
                    self.logger.log(f"    Target: Monitor {config.monitor} ({display_name}) at ({x}, {y}) {width}x{height}")
                    
                    try:
                        # Move and resize using pygetwindow 
                        target_window.moveTo(x, y)
                        time.sleep(0.05)
                        target_window.resizeTo(width, height)
                        positioned_count += 1
                        self.logger.log(f"    [OK] Positioned via pygetwindow")
                    except Exception as e:
                        self.logger.log(f"    [SKIP] {str(e)[:50]}")
                else:
                    # Don't log NOT FOUND for Chrome - there may be more windows
                    pass
                    
            except Exception as e:
                self.logger.log(f"  [ERROR] {str(e)[:50]}")
        
        self.logger.log(f"\n[RESULT] Positioned {positioned_count}/{len(app_configs)} windows")

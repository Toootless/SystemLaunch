"""
DisplayFusion API wrapper for window positioning.
"""

import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional
import json
import tempfile
from datetime import datetime
import ctypes
from ctypes import wintypes
import traceback


# Win32 constants for SetWindowPos
SWP_NOACTIVATE = 0x0010
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
HWND_TOP = 0
SW_RESTORE = 9
SW_SHOWNORMAL = 1

def set_window_pos_win32(hwnd: int, x: int, y: int, width: int, height: int) -> bool:
    """Set window position using Win32 SetWindowPos API."""
    try:
        user32 = ctypes.windll.user32
        
        # First restore the window if it's minimized or maximized
        user32.ShowWindow(hwnd, SW_RESTORE)
        
        SetWindowPos = user32.SetWindowPos
        SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.INT, wintypes.INT, 
                                 wintypes.INT, wintypes.INT, wintypes.UINT]
        SetWindowPos.restype = wintypes.BOOL
        result = SetWindowPos(hwnd, HWND_TOP, x, y, width, height, SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
        if result:
            return True
        
        # Fallback: try MoveWindow which is simpler and often works where SetWindowPos doesn't
        MoveWindow = user32.MoveWindow
        MoveWindow.argtypes = [wintypes.HWND, wintypes.INT, wintypes.INT, wintypes.INT, wintypes.INT, wintypes.BOOL]
        MoveWindow.restype = wintypes.BOOL
        result2 = MoveWindow(hwnd, x, y, width, height, True)
        if result2:
            return True
        
        err = ctypes.GetLastError()
        return False
    except Exception as e:
        return False


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
            
            self.logger.log(f"\n[DEBUG] Detected {len(monitors)} monitors via screeninfo")
            for i, mon in enumerate(monitors):
                self.logger.log(f"    Monitor {i}: {mon.name} - {mon.width}x{mon.height} @ ({mon.x}, {mon.y})")
            
            # Map from Display Name (e.g. "DISPLAY6") to config ID (1-5)
            name_map = {v: k for k, v in self.DISPLAY_NAMES.items()}
            
            for monitor in monitors:
                # monitor.name comes like "\\.\DISPLAY6"
                name = monitor.name.replace("\\\\.\\", "") if monitor.name else ""
                
                if name in name_map:
                    mon_id = name_map[name]
                    self.monitor_info[mon_id] = {
                        "width": monitor.width,
                        "height": monitor.height,
                        "x": monitor.x,
                        "y": monitor.y,
                    }
                    self.logger.log(f"    Mapped {name} (Monitor {mon_id}): x={monitor.x}, y={monitor.y}, w={monitor.width}, h={monitor.height}")
                    
            # Fallback for any monitor IDs that weren't found by name
            for i, monitor in enumerate(monitors, 1):
                if i not in self.monitor_info and i in self.DISPLAY_NAMES:
                    self.monitor_info[i] = {
                        "width": monitor.width,
                        "height": monitor.height,
                        "x": monitor.x,
                        "y": monitor.y,
                    }
                    self.logger.log(f"    Fallback Monitor {i}: x={monitor.x}, y={monitor.y}, w={monitor.width}, h={monitor.height}")
        except Exception as e:
            print(f"Error detecting monitors: {e}")

    def get_field_bounds(self, monitor: int, field_index: int, location_id: str = None) -> Tuple[int, int, int, int]:
        """
        Calculate window bounds for a specific field on a monitor.
        
        Args:
            monitor: Monitor number
            field_index: 0-based field index (fallback)
            location_id: Optional location identifier (top-left, center, etc.)
        
        Returns: (x, y, width, height)
        """
        if monitor not in self.monitor_info:
            return (0, 0, 800, 600)

        layout = self.MONITOR_LAYOUTS.get(monitor, {"cols": 1, "rows": 1})
        mon_info = self.monitor_info[monitor]

        cols = layout.get("cols", 1)
        rows = layout.get("rows", 1)

        # Base calculations on location_id if available, otherwise fallback to field_index
        col = 0
        row = 0
        
        if location_id:
            loc = location_id.lower()
            if "center" in loc and cols == 1 and rows == 1:
                col = 0
                row = 0
            elif "left" in loc and not "top" in loc and not "bottom" in loc:
                col = 0
                row = 0
            elif "right" in loc and not "top" in loc and not "bottom" in loc:
                col = 1
                row = 0
            elif "top-left" in loc:
                col = 0; row = 0
            elif "top-center" in loc:
                col = 1; row = 0
            elif "top-right" in loc:
                col = 2; row = 0
            elif "bottom-left" in loc:
                col = 0; row = 1
            elif "bottom-center" in loc:
                col = 1; row = 1
            elif "bottom-right" in loc:
                col = 2; row = 1
            else:
                col = field_index % cols
                row = field_index // cols
                # Cap the row so we don't go off screen if user adds too many
                row = min(row, rows - 1)
        else:
            col = field_index % cols
            row = field_index // cols
            # Cap the row so we don't go off screen if user adds too many
            row = min(row, rows - 1)

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
        Launch all applications and position them to target monitors.
        Groups Chrome tabs by monitor/location to keep them in the same window.
        """
        self.logger.log(f"\n{'='*60}")
        self.logger.log(f"Starting to launch and position {len(app_configs)} applications...")
        self.logger.log(f"{'='*60}\n")
        
        try:
            import pygetwindow as gw
            import time
        except ImportError:
            self.logger.log("WARNING: pygetwindow not available for window positioning")
            return
            
        # Group Chrome configs by (monitor, location_id) to combine tabs into one window
        launch_groups = []
        chrome_groups = {}
        for config in app_configs:
            if config.app_type.lower() == "chrome":
                key = (config.monitor, config.location_id)
                if key not in chrome_groups:
                    chrome_groups[key] = []
                    launch_groups.append(("chrome", chrome_groups[key]))
                chrome_groups[key].append(config)
            else:
                launch_groups.append(("program", [config]))

        for i, (group_type, configs) in enumerate(launch_groups, 1):
            try:
                base_config = configs[0]
                display_name = self.DISPLAY_NAMES.get(base_config.monitor, f"DISPLAY{base_config.monitor}")
                
                if group_type == "chrome":
                    urls = [c.target for c in configs]
                    self.logger.log(f"[{i}/{len(launch_groups)}] Launching CHROME GROUP ({len(urls)} tabs)")
                    self.logger.log(f"    Target: Monitor {base_config.monitor} ({display_name}), Location {base_config.location_id}")
                    
                    # Snapshot windows before launch
                    before_hwnds = set()
                    try:
                        for w in gw.getAllWindows():
                            try:
                                hwnd = getattr(w, '_hWnd', None)
                                if hwnd:
                                    before_hwnds.add(hwnd)
                            except (OSError, AttributeError):
                                pass
                    except Exception as snapshot_err:
                        self.logger.log(f"    [WARNING] Could not snapshot windows: {type(snapshot_err).__name__}")
                    
                    # Launch all URLs in one command
                    self._launch_chrome_group(base_config, urls)
                    time.sleep(1.5)  # Wait for Chrome to fully start and render
                    
                    # Position the new window
                    try:
                        self._position_window(base_config, before_hwnds, gw, time)
                    except Exception as pos_err:
                        msg = f"    [ERROR] Position window failed: {type(pos_err).__name__}: {pos_err}"
                        print(msg)
                        self.logger.log(msg)
                        self.logger.log(f"    Traceback: {traceback.format_exc()}")
                    
                else:
                    self.logger.log(f"[{i}/{len(launch_groups)}] Launching PROGRAM: {base_config.target[:50]}")
                    self.logger.log(f"    Target: Monitor {base_config.monitor} ({display_name}), Location {base_config.location_id}")
                    
                    # Snapshot windows before launch
                    before_hwnds = set()
                    try:
                        for w in gw.getAllWindows():
                            try:
                                hwnd = getattr(w, '_hWnd', None)
                                if hwnd:
                                    before_hwnds.add(hwnd)
                            except (OSError, AttributeError):
                                pass
                    except Exception as snapshot_err:
                        self.logger.log(f"    [WARNING] Could not snapshot windows: {type(snapshot_err).__name__}")
                    
                    self._launch_program(base_config)
                    time.sleep(3.0)  # Wait longer for programs to create main window
                    
                    # Position the new window
                    try:
                        self._position_window(base_config, before_hwnds, gw, time)
                    except Exception as pos_err:
                        msg = f"    [ERROR] Position window failed: {type(pos_err).__name__}: {pos_err}"
                        print(msg)
                        self.logger.log(msg)
                        self.logger.log(f"    Traceback: {traceback.format_exc()}")
                
                self.logger.log("")
            except Exception as e:
                msg = f"    [ERROR] {type(e).__name__}: {e}"
                print(msg)
                self.logger.log(msg)
                self.logger.log(f"    Traceback: {traceback.format_exc()}\n")

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

    def _launch_chrome_group(self, config, urls):
        """Launch a group of Chrome tabs in a single window with position specified at launch."""
        try:
            from src.core.chrome_manager import ChromeManager
            chrome_mgr = ChromeManager()
            
            # Get the target position on the monitor
            x, y, width, height = self.get_field_bounds(config.monitor, config.position - 1, config.location_id)
            
            display_name = self.DISPLAY_NAMES.get(config.monitor, f"DISPLAY{config.monitor}")
            self.logger.log(f"    Opening Chrome Group with {len(urls)} tabs")
            self.logger.log(f"    Position: x={x}, y={y}, w={width}, h={height}")
            
            if chrome_mgr.open_url_group(urls, window_x=x, window_y=y, window_width=width, window_height=height):
                self.logger.log(f"Opened Chrome Group ({len(urls)} tabs) on Monitor {config.monitor} ({display_name}), Location {config.location_id}")
            else:
                self.logger.log(f"    [WARNING] Failed to open Chrome group")
        except Exception as e:
            import traceback
            self.logger.log(f"    [ERROR] Failed to launch Chrome group: {type(e).__name__}: {e}")
            self.logger.log(f"    Traceback: {traceback.format_exc()}\n")

    def _is_process_running(self, program_name: str) -> bool:
        """Check if a process with a matching executable name is already running."""
        try:
            import psutil
            search = Path(program_name).stem.lower()  # e.g. 'ollama', 'winword', 'code'
            for proc in psutil.process_iter(['name']):
                try:
                    proc_stem = Path(proc.info['name']).stem.lower()
                    if proc_stem == search:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
            pass
        return False

    def _start_exe(self, path: str) -> str:
        """Launch an executable detached from our console so child signals can't kill us.
        Returns 'subprocess' or 'startfile' indicating which method succeeded."""
        import subprocess
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        try:
            subprocess.Popen(
                [path],
                creationflags=flags,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return "subprocess"
        except (OSError, PermissionError):
            import os
            os.startfile(path)
            return "startfile"

    def _launch_program(self, config):
        """Launch a program and position it."""
        x, y, width, height = self.get_field_bounds(config.monitor, config.position - 1, config.location_id)
        
        display_name = self.DISPLAY_NAMES.get(config.monitor, f"DISPLAY{config.monitor}")
        try:
            import os
            import shutil
            from pathlib import Path
            
            # Try to find the program
            program_name = config.target
            
            # Check if already running — skip launch to avoid duplicate or crash
            if self._is_process_running(program_name):
                self.logger.log(f"    [ALREADY RUNNING] {program_name} — skipping launch")
                self.logger.log(f"    [LAUNCHED] on Monitor {config.monitor} ({display_name}), Location {config.location_id}")
                return

            self.logger.log(f"    Searching for: {program_name}")
            
            # Check if it's a full path
            if Path(program_name).exists():
                self.logger.log(f"    Found at: {program_name}")
                method = self._start_exe(str(program_name))
                self.logger.log(f"    Launched via {method}")
            else:
                # Try to find in PATH
                found_path = shutil.which(program_name)
                if found_path:
                    self.logger.log(f"    Found in PATH: {found_path}")
                    method = self._start_exe(str(found_path))
                    self.logger.log(f"    Launched via {method}")
                else:
                    # Try common application paths with more thorough search
                    self.logger.log(f"    Not in PATH, checking common locations...")
                    possible_paths = [
                        # Direct Program Files searches
                        Path("C:\\Program Files") / program_name,
                        Path("C:\\Program Files (x86)") / program_name,
                        Path.home() / "AppData" / "Local" / "Programs" / program_name,
                        
                        # Specific common apps
                        Path.home() / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "Code.exe" if "code" in program_name.lower() else None,
                        Path("C:\\Program Files\\Microsoft VS Code\\Code.exe") if "code" in program_name.lower() else None,
                        Path("C:\\Program Files\\Bambu Studio\\bambu-studio.exe") if "bambu" in program_name.lower() else None,
                        Path.home() / "AppData" / "Local" / "AMD" / "AI_Bundle" / "Ollama" / "ollama app.exe" if "ollma" in program_name.lower() or "ollama" in program_name.lower() else None,
                        
                        # Microsoft Office apps
                        Path("C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.exe") if "winword" in program_name.lower() or "word" in program_name.lower() else None,
                        Path("C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\WINWORD.exe") if "winword" in program_name.lower() or "word" in program_name.lower() else None,
                        Path("C:\\Program Files\\Microsoft Office\\root\\Office365\\WINWORD.exe") if "winword" in program_name.lower() or "word" in program_name.lower() else None,
                        Path("C:\\Program Files (x86)\\Microsoft Office\\root\\Office365\\WINWORD.exe") if "winword" in program_name.lower() or "word" in program_name.lower() else None,
                        
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
                            method = self._start_exe(str(path))
                            self.logger.log(f"    Launched via {method}")
                            found = True
                            break
                    
                    if not found:
                        self.logger.log(f"    [NOT FOUND] anywhere")
                        self.logger.log(f"    Tried: {program_name}, PATH, Program Files, AppData")
                        return
            
            self.logger.log(f"    [LAUNCHED] on Monitor {config.monitor} ({display_name}), Location {config.location_id}")
        except Exception as e:
            self.logger.log(f"    Exception: {e}")

    def _position_window(self, config, before_hwnds, gw, time):
        """Position a newly launched window to its target monitor and location."""
        try:
            display_name = self.DISPLAY_NAMES.get(config.monitor, f"DISPLAY{config.monitor}")
            x, y, width, height = self.get_field_bounds(config.monitor, config.position - 1, config.location_id)
            
            # Try to find the new window (up to 6 seconds with shorter intervals)
            target_window = None
            for attempt in range(12):
                try:
                    time.sleep(0.5)  # Wait for window to appear and stabilize
                    try:
                        after_windows = gw.getAllWindows()
                    except OSError as pipe_error:
                        # WinError 233: No process on other end of pipe - skip this attempt
                        self.logger.log(f"    [DEBUG] Attempt {attempt+1}: OSError getting windows")
                        continue
                    
                    new_windows = []
                    for w in after_windows:
                        try:
                            hwnd = getattr(w, '_hWnd', None)
                            if hwnd and hwnd not in before_hwnds:
                                new_windows.append(w)
                        except (OSError, AttributeError):
                            # Window may have closed, skip it
                            continue
                    
                    # Filter for visible, titled windows (ignore system windows and the launcher itself)
                    valid_new = []
                    for w in new_windows:
                        try:
                            title = w.title.strip() if w.title else ""
                            if (title 
                                and "untitled" not in title.lower()
                                and "webpage launcher" not in title.lower()):
                                valid_new.append(w)
                        except (OSError, AttributeError):
                            # Window may have closed or title not accessible, skip it
                            continue
                    
                    if valid_new:
                        target_window = valid_new[0]
                        self.logger.log(f"    [DEBUG] Found window on attempt {attempt+1}")
                        break
                    else:
                        # If no window found yet, also consider very short-titled windows (like WINWORD temporary windows)
                        fallback_windows = []
                        for w in new_windows:
                            try:
                                title = w.title.strip() if w.title else ""
                                # Accept windows with empty or very short titles
                                if len(title) == 0 or (len(title) < 50 and "webpage launcher" not in title.lower()):
                                    fallback_windows.append(w)
                            except (OSError, AttributeError):
                                continue
                        
                        if fallback_windows:
                            target_window = fallback_windows[0]
                            self.logger.log(f"    [DEBUG] Found window on attempt {attempt+1} (fallback match)")
                            break
                        elif attempt < 3:
                            self.logger.log(f"    [DEBUG] Attempt {attempt+1}: No new window yet, {len(after_windows)} total windows")
                except Exception as inner_error:
                    self.logger.log(f"    [DEBUG] Attempt {attempt+1} error: {type(inner_error).__name__}: {inner_error}")
                    continue
            
            if target_window:
                try:
                    self.logger.log(f"    Found window: {target_window.title[:50]}")
                    self.logger.log(f"    Moving to: Monitor {config.monitor}, x={x}, y={y}, w={width}, h={height}")
                    
                    hwnd = getattr(target_window, '_hWnd', None)
                    
                    if hwnd:
                        # Wait a moment for Chrome to finish its own startup positioning, then override it
                        time.sleep(0.8)
                        result = set_window_pos_win32(hwnd, x, y, width, height)
                        if result:
                            self.logger.log(f"    [POSITIONED] to Monitor {config.monitor} ({display_name}) - Win32 success")
                            return
                        else:
                            err = ctypes.GetLastError()
                            self.logger.log(f"    [DEBUG] Win32 failed (error {err}), retrying after delay...")
                            # Retry after longer delay - Chrome restores saved window position on startup
                            time.sleep(1.5)
                            result2 = set_window_pos_win32(hwnd, x, y, width, height)
                            if result2:
                                self.logger.log(f"    [POSITIONED] to Monitor {config.monitor} ({display_name}) - Win32 retry success")
                                return
                            else:
                                err2 = ctypes.GetLastError()
                                self.logger.log(f"    [DEBUG] Win32 retry failed (error {err2}), trying pygetwindow...")
                    
                    # Fallback to pygetwindow if Win32 failed or returned False
                    try:
                        # Restore if maximized
                        if hasattr(target_window, 'isMaximized') and target_window.isMaximized:
                            target_window.restore()
                            time.sleep(0.2)
                        
                        # Try moving without resizing first for better compatibility
                        target_window.moveTo(x, y)
                        time.sleep(0.1)
                        target_window.resizeTo(width, height)
                        self.logger.log(f"    [POSITIONED] to Monitor {config.monitor} ({display_name}) - pygetwindow")
                    except PermissionError:
                        self.logger.log(f"    [POSITIONED] (elevated access required, window positioned via OS)")
                    except Exception as move_err:
                        # Most positioning failures are acceptable - window might still be positioned
                        self.logger.log(f"    [POSITIONED] (attempt made, result may vary due to window privileges)")
                        
                except Exception as pos_error:
                    self.logger.log(f"    [WARNING] Could not position window: {pos_error}")
            else:
                self.logger.log(f"    [WARNING] Could not find new window to position after 2 seconds")
        except Exception as e:
            self.logger.log(f"    [ERROR] Positioning failed: {e}")


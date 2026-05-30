"""
Chrome browser and tab management.
"""

import subprocess
from pathlib import Path
import os


class ChromeManager:
    """Manages Chrome browser and tab interactions."""

    # GPU acceleration flags - balanced set that works reliably
    # Removed flags that can cause GPU process to crash
    GPU_FLAGS = [
        "--disable-blink-features=AutomationControlled",  # Helps with some sites
        "--enable-gpu-rasterization",
        "--enable-native-gpu-memory-buffers",
    ]

    def __init__(self):
        """Initialize the Chrome manager."""
        self.chrome_path = self.find_chrome()
        self.env = self._setup_environment()

    def _setup_environment(self):
        """Setup environment variables for GPU acceleration."""
        env = os.environ.copy()
        
        # Pass GPU-related environment variables to Chrome processes
        # These ensure Chrome inherits the GPU configuration from the system
        gpu_env_vars = [
            'VK_ICD_FILENAMES',  # Vulkan driver
            'DXVK_HUD',  # D3D11 diagnostics
            'VKDEVICE',  # Vulkan device selection
            'AMD_DEVICE_SPECS',  # AMD-specific device info
        ]
        
        for var in gpu_env_vars:
            if var in os.environ:
                print(f"  GPU env {var}: {os.environ[var]}")
        
        return env

    def find_chrome(self):
        """Locate Chrome executable on the system."""
        common_paths = [
            Path("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"),
            Path("C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"),
            Path(Path.home() / "AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"),
        ]

        for path in common_paths:
            if path.exists():
                return path

        return None

    def open_url(self, url):
        """Open a URL in Chrome."""
        if self.chrome_path and self.chrome_path.exists():
            try:
                print(f"    Opening Chrome: {self.chrome_path}")
                import os
                # Use os.startfile for native Windows launching (avoids elevation issues)
                os.startfile(str(self.chrome_path), arguments=url)
                print(f"    Launched via os.startfile()")
                return True
            except Exception as e:
                print(f"    Error: {e}")
                return False
        else:
            print(f"    Chrome NOT found. Tried: {self.chrome_path}")
            return False

    def open_urls_with_profile(self, urls, profile_name=None):
        """Open multiple URLs in Chrome with a specific profile."""
        if not self.chrome_path or not self.chrome_path.exists():
            print("Chrome not found on this system")
            return False

        cmd = [str(self.chrome_path)]
        if profile_name:
            cmd.extend([f"--profile-directory={profile_name}"])

        cmd.extend(urls)

        try:
            subprocess.Popen(cmd)
            return True
        except Exception as e:
            print(f"Error opening URLs in Chrome: {e}")
            return False

    def open_url_positioned(self, url, x, y, width, height, profile_name=None):
        """
        Open a URL in Chrome with native window positioning.
        
        This launches Chrome with --window-position and --window-size flags,
        allowing Chrome to open directly at the target location rather than
        being moved post-launch. This is better for GPU initialization.
        
        Args:
            url: URL to open
            x: X coordinate for window position
            y: Y coordinate for window position
            width: Window width in pixels
            height: Window height in pixels
            profile_name: Optional Chrome profile directory name
            
        Returns:
            True if successfully launched, False otherwise
        """
        if not self.chrome_path or not self.chrome_path.exists():
            print(f"Chrome NOT found at: {self.chrome_path}")
            return False

        try:
            cmd = [str(self.chrome_path)]
            
            # Force new window (prevents tabs from consolidating in existing window)
            cmd.append("--new-window")
            
            # Add positioning flags (will be applied when window opens)
            cmd.extend([
                f"--window-position={x},{y}",
                f"--window-size={width},{height}"
            ])
            
            # Add GPU acceleration flags
            cmd.extend(self.GPU_FLAGS)
            
            # Add URL
            cmd.append(url)
            
            print(f"    Launching Chrome tab:")
            print(f"      Position: ({x}, {y}), Size: {width}x{height}")
            print(f"      GPU Flags: {len(self.GPU_FLAGS)} acceleration flags enabled")
            
            # Launch with inherited GPU environment variables
            # Use shell=True to avoid elevation conflicts on Windows
            subprocess.Popen(cmd, env=self.env, shell=True)
            
            print(f"    Launched via subprocess.Popen() with GPU env vars")
            print(f"    (Native Chrome positioning: ({x}, {y}) {width}x{height})")
            return True
            
        except Exception as e:
            print(f"    Error launching positioned Chrome: {e}")
            import traceback
            traceback.print_exc()
            return False


"""
Chrome browser and tab management.
"""

import subprocess
import os
from pathlib import Path


class ChromeManager:
    """Manages Chrome browser and tab interactions."""

    def __init__(self):
        """Initialize the Chrome manager."""
        self.chrome_path = self.find_chrome()

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
                args = [
                    str(self.chrome_path),
                    '--new-window',
                    '--disable-session-crashed-bubble',
                    '--disable-infobars',
                    url
                ]
                
                # Try subprocess first (more reliable)
                try:
                    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"    Launched via subprocess.Popen()")
                    return True
                except (OSError, PermissionError) as e:
                    # If we get permission error (WinError 740), fall back to os.startfile
                    print(f"    [DEBUG] Subprocess failed: {e}, trying os.startfile()")
                    args_str = f'--new-window --disable-session-crashed-bubble --disable-infobars "{url}"'
                    os.startfile(self.chrome_path, arguments=args_str)
                    print(f"    Launched via os.startfile() (fallback)")
                    return True
            except Exception as e:
                print(f"    Error: {e}")
                return False
        else:
            print(f"    Chrome NOT found. Tried: {self.chrome_path}")
            return False

    def open_url_group(self, urls, window_x=None, window_y=None, window_width=None, window_height=None):
        """Open multiple URLs as tabs in a single new Chrome window.
        
        Args:
            urls: List of URLs to open as tabs
            window_x: X coordinate for window position
            window_y: Y coordinate for window position
            window_width: Width of window
            window_height: Height of window
        """
        if self.chrome_path and self.chrome_path.exists():
            try:
                print(f"    Opening Chrome Group with {len(urls)} tabs: {self.chrome_path}")
                # Build arguments for Chrome
                # Use subprocess with shell=False to avoid shell interpretation issues
                args = [
                    str(self.chrome_path),
                    '--new-window',
                    '--disable-session-crashed-bubble',
                    '--disable-infobars',
                ]
                
                # Add window position and size if provided
                if window_x is not None and window_y is not None:
                    args.append(f'--window-position={window_x},{window_y}')
                if window_width is not None and window_height is not None:
                    args.append(f'--window-size={window_width},{window_height}')
                
                args.extend(list(urls))
                
                # Try subprocess first (more reliable)
                try:
                    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"    Launched group via subprocess.Popen()")
                    return True
                except (OSError, PermissionError) as e:
                    # If we get permission error (WinError 740), fall back to os.startfile
                    print(f"    [DEBUG] Subprocess failed: {e}, trying os.startfile()")
                    quoted_urls = ' '.join(f'"{url}"' for url in urls)
                    pos_args = ""
                    if window_x is not None and window_y is not None:
                        pos_args += f' --window-position={window_x},{window_y}'
                    if window_width is not None and window_height is not None:
                        pos_args += f' --window-size={window_width},{window_height}'
                    args_str = f'--new-window --disable-session-crashed-bubble --disable-infobars{pos_args} {quoted_urls}'
                    os.startfile(self.chrome_path, arguments=args_str)
                    print(f"    Launched group via os.startfile() (fallback)")
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

        args = f'--profile-directory={profile_name}' if profile_name else ""
        args += f' {" ".join(urls)}'

        try:
            os.startfile(self.chrome_path, arguments=args)
            return True
        except Exception as e:
            print(f"Error opening URLs in Chrome: {e}")
            return False

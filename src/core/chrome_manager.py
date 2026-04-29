"""
Chrome browser and tab management.
"""

import subprocess
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

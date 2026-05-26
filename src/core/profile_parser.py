"""
Configuration file parser for profiles.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class AppConfig:
    """Represents a single app/tab configuration."""
    monitor: int
    position: int
    location_id: str  # e.g., 'top-left', 'center', 'bottom-right'
    app_type: str    # 'chrome' or 'program'
    target: str      # URL or executable path
    skip_positioning: bool = False  # Skip window positioning for this app (6th field, optional)


class ProfileParser:
    """Parses the profile configuration text file."""

    def __init__(self, config_file: Path):
        """Initialize the parser with a config file path."""
        self.config_file = config_file

    def parse(self) -> List[AppConfig]:
        """Parse the configuration file and return list of AppConfig objects."""
        apps = []

        if not self.config_file.exists():
            print(f"Config file not found: {self.config_file}")
            return apps

        try:
            with open(self.config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        parts = line.split(',')
                        if len(parts) < 5:
                            continue
                        
                        monitor = int(parts[0].strip())
                        position = int(parts[1].strip())
                        location_id = parts[2].strip()
                        app_type = parts[3].strip().lower()
                        target = parts[4].strip()
                        
                        # Optional 6th field: skip_positioning flag
                        skip_positioning = False
                        if len(parts) >= 6:
                            skip_flag = parts[5].strip().lower()
                            skip_positioning = skip_flag in ('true', '1', 'yes', 'skip')
                        
                        app = AppConfig(
                            monitor=monitor,
                            position=position,
                            location_id=location_id,
                            app_type=app_type,
                            target=target,
                            skip_positioning=skip_positioning
                        )
                        apps.append(app)
                    
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing line: {line} - {e}")
                        continue

        except Exception as e:
            print(f"Error reading config file: {e}")

        return apps

    def validate_config(self, apps: List[AppConfig]) -> bool:
        """Validate that the configuration meets requirements."""
        # Validate monitor numbers are within 1-5
        for app in apps:
            if not 1 <= app.monitor <= 5:
                print(f"Invalid monitor number: {app.monitor}. Must be 1-5")
                return False
        
        # No limit on number of tabs/programs per monitor
        # Users can have unlimited entries per monitor
        return True

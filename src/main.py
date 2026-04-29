#!/usr/bin/env python3
"""
Main entry point for Webpage Launcher application.
"""

import sys
from pathlib import Path

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app import WebpageLauncherApp


def main():
    """Launch the application."""
    app = WebpageLauncherApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()

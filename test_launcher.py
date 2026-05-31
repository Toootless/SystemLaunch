#!/usr/bin/env python3
"""Direct test of launcher."""

import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.displayfusion_manager import DisplayFusionManager
from src.core.profile_parser import ProfileParser

# Use full config
config_file = Path(__file__).parent / "config" / "profiles.txt"
parser = ProfileParser(config_file)
configs = parser.parse()

print(f"Loaded {len(configs)} app configs")
print("Starting launcher...")

try:
    mgr = DisplayFusionManager()
    mgr.launch_apps(configs)
    print("\n\nLauncher complete - ALL APPS LAUNCHED!")
except KeyboardInterrupt:
    print("CAUGHT KeyboardInterrupt (Ctrl+C/Break signal from child process)", flush=True)
    traceback.print_exc()
    sys.exit(1)
except BaseException as e:
    print(f"ERROR during launcher ({type(e).__name__}): {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

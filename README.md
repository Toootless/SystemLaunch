# Webpage Launcher - Multi-Monitor Layout Manager

A highly customized desktop application designed to launch and precisely position applications and Chrome tabs across a complex multi-monitor setup.

## Features
- **Chrome Tab Grouping**: Intelligently groups multiple Chrome URLs that share the same monitor and screen location into a single window with multiple tabs.
- **Precise Grid Positioning**: Automatically maps windows to exact screen quadrants (e.g., `top-left`, `bottom-right`, `center`) without relying on rigid sequential math.
- **Robust Application Finding**: Automatically hunts for common executables (Ollama, Bambu Studio, VS Code) in `Program Files`, `AppData`, and custom AI bundle paths if they aren't in the system PATH.
- **Asynchronous GUI Handling**: Implements generous timeouts (up to 15 seconds) to allow heavy programs (like Bambu Studio) and heavy webpages (like Google Gemini) time to spawn before positioning them.
- **Self-Elevating Administrator Execution**: The included `WebpageLauncher.bat` file automatically prompts for Admin privileges, which is strictly required for Python to move external process windows.

## Configuration Guide (`config/profiles.txt`)

All screen mapping is controlled entirely via `config/profiles.txt`.

### Format
`monitor,position,location_id,app_type,target`

1. **`monitor`**: `1` through `5` (Matches to `DISPLAY6`, `DISPLAY7`, `DISPLAY1`, `DISPLAY2`, `DISPLAY3`).
2. **`position`**: A sequential list number (e.g., `1`, `2`, `3`). This is mostly for visual ordering and is safely ignored by the grid layout engine.
3. **`location_id`**: The exact physical location on the monitor to snap the window. 
   - Acceptable values: `left`, `right`, `center`, `top-left`, `top-center`, `top-right`, `bottom-left`, `bottom-center`, `bottom-right`.
4. **`app_type`**: `chrome` or `program`.
5. **`target`**: The URL (for Chrome) or the executable name/path (for Programs).

### Modifying Chrome Groups
To add a new Chrome tab to an existing group, simply add a new line in `profiles.txt` with the **same monitor** and **same location_id**. The launcher will automatically bundle them together into a single Chrome window.

Example:
```text
# This will spawn a single Chrome window on Monitor 3 (center) containing two tabs.
3,1,center,chrome,https://www.youtube.com
3,2,center,chrome,https://www.github.com
```

### Known Application Paths
If you need to update where a program is launched from, open `src/core/displayfusion_manager.py` and search for the `possible_paths` array. You can hardcode exact paths there (for example, the AMD AI Bundle path for Ollama).

## How it Works Under the Hood
1. **Launch**: You run `WebpageLauncher.bat` -> Elevates to Admin -> Launches `src/main.py` -> Spawns PyQt5 Interface.
2. **Read Config**: Reads `profiles.txt`.
3. **Group**: Combines all `chrome` configurations that share a `(monitor, location_id)` into arrays.
4. **Spawn & Poll**: 
   - Launches the process (via `os.startfile` or `subprocess.Popen`).
   - Uses `pygetwindow` to snapshot existing windows, then polls the system every 0.5s (up to 15s) until a *new* valid window handle appears.
5. **Position**: Calculates the grid coordinates based on the `location_id` string and uses `pygetwindow.resizeTo` and `moveTo` to perfectly snap the window into place.

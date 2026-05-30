# Webpage Launcher - Multi-Monitor Layout Manager

A desktop application that manages Chrome tabs and programs across multiple monitors with predefined layouts. Supports GPU-accelerated Chrome launches, silent auto-launch mode, and detailed launch logging.

## Features
- Configure multiple monitors with custom layouts
- Open Chrome tabs or programs on specific monitors with native window positioning
- GPU acceleration flags and environment variable inheritance for Chrome and programs
- Auto-launch mode (`--auto-launch`) for silent, GUI-free batch launching via desktop shortcut
- Separate Chrome window per URL (no tab consolidation) using `--new-window` flag
- Window positioning via pygetwindow after launch
- Detailed timestamped launch log (`launch_log.txt`) with UTF-8 encoding
- Predefined layout: 6 fields on monitor 2, 5 fields on monitor 3, 2 fields each on monitors 4-5
- Save and manage multiple profiles
- Desktop shortcut launcher with admin elevation check (`WebpageLauncher.bat`)

## Quick Start

### GUI Mode
```
python src/main.py
```

### Auto-Launch Mode (no GUI, runs all apps immediately)
```
python src/main.py --auto-launch
```

### Desktop Shortcut
Double-click `WebpageLauncher.bat` — handles admin elevation automatically and runs in auto-launch mode.

## GPU Acceleration

Chrome is launched with the following GPU acceleration flags:
- `--disable-blink-features=AutomationControlled`
- `--enable-gpu-rasterization`
- `--enable-native-gpu-memory-buffers`

The following environment variables are inherited by child processes when set:
| Variable | Purpose |
|---|---|
| `VK_ICD_FILENAMES` | Vulkan driver path (e.g. AMD RX 7900 XTX) |
| `DXVK_HUD` | D3D11 diagnostics overlay |
| `VKDEVICE` | Vulkan device selection |
| `AMD_DEVICE_SPECS` | AMD-specific device configuration |
| `DISABLE_LAYER_AMD_SWITCHABLE_GRAPHICS` | AMD switchable graphics control |

## Window Positioning

Each Chrome URL is launched as a **separate window** (not a tab) using:
- `--new-window` — forces a new Chrome window per URL
- `--window-position=X,Y` — native Chrome positioning hint
- `--window-size=W,H` — native Chrome sizing hint

After all launches, `_position_windows()` attempts to reposition windows using `pygetwindow`. Windows are tracked by HWND to avoid double-positioning.

> **Note:** Chrome windows on Windows may be protected by the OS sandbox and resist external repositioning (`SetWindowPos` / pygetwindow may return Access Denied for Chrome processes). Non-Chrome programs (e.g. VS Code) are repositioned successfully.

## Project Structure
```
SystemLaunch/
├── src/
│   ├── main.py                        # Application entry point
│   ├── app.py                         # Main app class; --auto-launch support
│   ├── ui/
│   │   ├── main_window.py             # Main window UI
│   │   ├── config_dialog.py           # Configuration dialog
│   │   └── widgets.py                 # Custom UI widgets
│   └── core/
│       ├── chrome_manager.py          # Chrome launch with GPU flags & positioning
│       ├── displayfusion_manager.py   # Orchestrates launches & window positioning
│       └── monitor_manager.py         # Multi-monitor detection
├── config/
│   └── default_layout.json            # Default monitor layout
├── WebpageLauncher.bat                # Windows launcher with admin elevation check
├── debug_windows.py                   # Debug utility: list all visible windows
├── launch_log.txt                     # Runtime log (UTF-8, timestamped)
├── requirements.txt
├── README.md
└── .gitignore
```

## Requirements

See `requirements.txt`. Key dependencies:
- `PyQt5` — GUI framework
- `pygetwindow` — post-launch window positioning
- `screeninfo` — multi-monitor detection
- `pyautogui` — display utilities

## Logging

All launches are recorded in `launch_log.txt` with timestamps. The log includes:
- GPU environment variable detection results
- Each app launch with target monitor, position, and coordinates
- Window positioning results (success / access denied / not found)
- Final summary: `[RESULT] Positioned N/M windows`

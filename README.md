# Webpage Launcher - Multi-Monitor Layout Manager

A desktop application that manages Chrome tabs and programs across multiple monitors with predefined layouts.

## Features
- Configure multiple monitors with custom layouts
- Open Chrome tabs or programs on specific monitors
- Predefined layout: 6 fields on monitor 1, 2 fields each on monitors 2-3, 1 field each on monitors 4-5
- Save and manage multiple profiles
- Launch with a single click

## Project Structure
```
webpage-launcher/
├── src/
│   ├── main.py                 # Application entry point
│   ├── app.py                  # Main application class
│   ├── ui/
│   │   ├── main_window.py      # Main window UI
│   │   ├── config_dialog.py    # Configuration dialog
│   │   └── widgets.py          # Custom UI widgets
│   ├── core/
│   │   ├── window_manager.py   # Window positioning logic
│   │   ├── chrome_manager.py   # Chrome tab management
│   │   └── monitor_manager.py  # Multi-monitor detection
│   └── config/
│       └── profile_manager.py  # Profile save/load
├── config/
│   └── default_layout.json     # Default monitor layout
├── tests/
│   └── test_window_manager.py
├── requirements.txt
├── README.md
└── .gitignore

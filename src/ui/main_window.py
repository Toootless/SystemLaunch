"""
Main application window.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QListWidget, QListWidgetItem, QSplitter,
    QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt
from pathlib import Path
import json
from src.core.profile_parser import ProfileParser
from src.core.displayfusion_manager import DisplayFusionManager


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("Webpage Launcher - Multi-Monitor Layout Manager")
        self.setGeometry(100, 100, 1200, 700)
        
        self.profiles_dir = Path(__file__).parent.parent.parent / "config"
        self.profile_parser = ProfileParser(self.profiles_dir / "profiles.txt")
        self.displayfusion = DisplayFusionManager()
        self.app_configs = []
        self.load_profiles()
        self.init_ui()

    def load_profiles(self):
        """Load profiles from the configuration file."""
        self.app_configs = self.profile_parser.parse()
        
        if not self.app_configs:
            print("No profiles loaded from configuration file")
        else:
            if self.profile_parser.validate_config(self.app_configs):
                print(f"Loaded {len(self.app_configs)} applications from profile")
            else:
                QMessageBox.warning(self, "Configuration Error", 
                                   "Profile configuration validation failed. Check constraints.")


    def init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layouts
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Multi-Monitor Webpage Launcher")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title)

        # Info section
        info_layout = QHBoxLayout()
        self.info_label = QLabel(f"Loaded: {len(self.app_configs)} applications")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)

        # Horizontal layout for main content
        content_layout = QHBoxLayout()

        # Left panel - App List
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Applications to Launch:"))
        
        self.app_list = QListWidget()
        self.populate_app_list()
        left_layout.addWidget(self.app_list)

        # Right panel - Control buttons
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Actions:"))
        
        self.launch_btn = QPushButton("🚀 Launch All")
        self.launch_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-size: 14px; font-weight: bold;")
        self.launch_btn.clicked.connect(self.launch_all)
        right_layout.addWidget(self.launch_btn)

        self.edit_config_btn = QPushButton("📝 Edit Config")
        self.edit_config_btn.clicked.connect(self.edit_config)
        right_layout.addWidget(self.edit_config_btn)

        self.reload_btn = QPushButton("🔄 Reload")
        self.reload_btn.clicked.connect(self.reload_profiles)
        right_layout.addWidget(self.reload_btn)

        self.monitors_btn = QPushButton("🖥️ Monitor Info")
        self.monitors_btn.clicked.connect(self.show_monitor_info)
        right_layout.addWidget(self.monitors_btn)

        self.about_btn = QPushButton("ℹ️ About")
        self.about_btn.clicked.connect(self.show_about)
        right_layout.addWidget(self.about_btn)

        right_layout.addStretch()

        # Add panels to content layout
        content_layout.addWidget(left_panel, 2)
        content_layout.addWidget(right_panel, 1)
        main_layout.addLayout(content_layout)

        # Status bar
        self.statusBar().showMessage("Ready")


    def populate_app_list(self):
        """Populate the app list widget with loaded applications."""
        self.app_list.clear()
        
        for config in self.app_configs:
            display_name = config.target
            if config.app_type.lower() == "chrome":
                display_name = f"🌐 {config.target[:50]}"
            else:
                display_name = f"📦 {Path(config.target).name}"
            
            location = f"Monitor {config.monitor} • {config.location_id.upper()}"
            full_text = f"{display_name} → {location}"
            
            item = QListWidgetItem(full_text)
            self.app_list.addItem(item)

    def launch_all(self):
        """Launch all configured applications."""
        if not self.app_configs:
            QMessageBox.warning(self, "No Configuration", 
                               "No applications configured. Please edit the config file.")
            return

        try:
            self.statusBar().showMessage("Launching applications...")
            self.displayfusion.launch_apps(self.app_configs)
            self.statusBar().showMessage(f"Launched {len(self.app_configs)} applications")
            QMessageBox.information(self, "Success", 
                                   f"Launched {len(self.app_configs)} applications across {len(set(c.monitor for c in self.app_configs))} monitors")
        except Exception as e:
            self.statusBar().showMessage("Error launching applications")
            QMessageBox.critical(self, "Error", f"Error launching applications: {str(e)}")

    def edit_config(self):
        """Open the configuration file in the default editor."""
        try:
            config_file = self.profiles_dir / "profiles.txt"
            import subprocess
            subprocess.Popen(['notepad', str(config_file)])
            self.statusBar().showMessage(f"Opening {config_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening config file: {str(e)}")

    def reload_profiles(self):
        """Reload profiles from the configuration file."""
        try:
            self.load_profiles()
            self.populate_app_list()
            self.info_label.setText(f"Loaded: {len(self.app_configs)} applications")
            self.statusBar().showMessage(f"Reloaded {len(self.app_configs)} applications")
            QMessageBox.information(self, "Success", f"Reloaded {len(self.app_configs)} applications")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error reloading profiles: {str(e)}")

    def show_monitor_info(self):
        """Display information about detected monitors."""
        try:
            # Map monitor numbers to display names
            display_map = {
                1: "DISPLAY6",
                2: "DISPLAY7",
                3: "DISPLAY1",
                4: "DISPLAY2",
                5: "DISPLAY3"
            }
            
            layout_map = {
                1: "Split Left-Right (2 sections)",
                2: "Grid 2x3 (6 sections)",
                3: "Full Screen (unlimited tabs)",
                4: "Full Screen (unlimited tabs)",
                5: "Chrome Groups Left-Right (2 sections)",
            }
            
            info = "Detected Monitors:\n\n"
            for mon_id, mon_info in self.displayfusion.monitor_info.items():
                display_name = display_map.get(mon_id, f"DISPLAY{mon_id}")
                layout = layout_map.get(mon_id, "Unknown")
                info += f"Monitor {mon_id} → {display_name}\n"
                info += f"  Layout: {layout}\n"
                info += f"  Position: ({mon_info['x']}, {mon_info['y']})\n"
                info += f"  Resolution: {mon_info['width']}x{mon_info['height']}\n\n"
            
            QMessageBox.information(self, "Monitor Information", info)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error retrieving monitor info: {str(e)}")

    def show_about(self):
        """Show about dialog."""
        about_text = """Webpage Launcher v0.2.0

Multi-Monitor Webpage & Application Launcher

Features:
• Unlimited tabs/programs per monitor
• Split and grid layouts for flexible window positioning
• DisplayFusion integration for advanced window management
• Simple text-based configuration

Monitor Layouts:
Monitor 1 (DISPLAY6) → Split Left-Right
Monitor 2 (DISPLAY7) → Grid 2x3 (6 sections)
Monitor 3 (DISPLAY1) → Full Screen
Monitor 4 (DISPLAY2) → Full Screen  
Monitor 5 (DISPLAY3) → Chrome Groups Left-Right

Physical Layout:
    Mon1       Mon3
  Mon5  Mon2   Mon4

Edit config: config/profiles.txt"""
        QMessageBox.information(self, "About", about_text)

    def new_profile(self):
        """Create a new profile (placeholder)."""
        self.statusBar().showMessage("New profile functionality coming soon...")

    def edit_profile(self):
        """Edit the selected profile (placeholder)."""
        self.statusBar().showMessage("Profile editing - use 'Edit Config' button instead")

    def delete_profile(self):
        """Delete the selected profile (placeholder)."""
        self.statusBar().showMessage("Profile deletion functionality coming soon...")

    def launch_profile(self):
        """Launch the selected profile (placeholder)."""
        self.statusBar().showMessage("Use 'Launch All' button instead")

    def configure_layout(self):
        """Open layout configuration dialog (placeholder)."""
        self.statusBar().showMessage("Configuration dialog coming soon...")

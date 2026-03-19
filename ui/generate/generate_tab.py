"""
Generate Tab

Simplified file generation tab with two output files: right_gcode and left_gcode.
Sync status highlighting and controlled generation.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
import os

from ..widgets.themed_widgets import (ThemedSplitter, ThemedLabel, ThemedLineEdit, ThemedGroupBox,
                                    PurpleButton, GreenButton, OrangeButton)
from .widgets.generated_file_item import GeneratedFileItem


class GenerateTab(QWidget):
    """Generate tab with two output files: right and left door G-code"""
    back_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.output_dir = os.path.expanduser("~/CNC/Output")
        self.first_time_opened = True

        # File items: right_gcode and left_gcode
        self.file_items = {
            'right': None,
            'left': None,
        }

        # MARK: - UI Setup
        self.setup_ui()
        self.apply_styling()
        self.connect_signals()

        # MARK: - Event Subscriptions
        if self.main_window:
            self.main_window.events.subscribe('profiles', self.on_profiles_updated)
            self.main_window.events.subscribe('processed', self.on_variables_updated)
            self.main_window.events.subscribe('generated', self.on_generated_updated)

    # MARK: - UI Setup

    def apply_styling(self):
        """Apply dark theme styling"""
        self.setStyleSheet("""
            GenerateTab {
                background-color: #282a36;
                color: #ffffff;
            }
        """)

    def setup_ui(self):
        """Initialize user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Top toolbar
        toolbar_layout = QHBoxLayout()
        main_layout.addLayout(toolbar_layout)

        title_label = ThemedLabel("Generated G-Code Files")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        toolbar_layout.addWidget(title_label)

        toolbar_layout.addStretch()

        self.generate_button = GreenButton("Generate Files")
        toolbar_layout.addWidget(self.generate_button)

        # Main content - two side-by-side file cards
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(20)
        main_layout.addWidget(content_widget, 1)

        # Right door file
        right_item = GeneratedFileItem("Right Door", "right", "right", self.main_window)
        right_item.content_changed.connect(
            lambda content: self.on_file_content_changed("right", content)
        )
        self.file_items['right'] = right_item
        content_layout.addWidget(right_item)

        # Left door file
        left_item = GeneratedFileItem("Left Door", "left", "left", self.main_window)
        left_item.content_changed.connect(
            lambda content: self.on_file_content_changed("left", content)
        )
        self.file_items['left'] = left_item
        content_layout.addWidget(left_item)

        # Output directory section with export button
        output_layout = QHBoxLayout()
        main_layout.addLayout(output_layout)

        output_layout.addWidget(ThemedLabel("Output Directory:"))
        self.output_path = ThemedLineEdit(self.output_dir)
        self.output_path.setReadOnly(True)
        output_layout.addWidget(self.output_path)

        browse_button = PurpleButton("Browse")
        browse_button.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(browse_button)

        self.export_button = OrangeButton("Export Files")
        self.export_button.clicked.connect(self.export_files)
        output_layout.addWidget(self.export_button)

        # Bottom navigation
        nav_layout = QHBoxLayout()
        main_layout.addLayout(nav_layout)

        nav_layout.addStretch()

        back_button = PurpleButton("← Back")
        back_button.clicked.connect(self.back_clicked)
        nav_layout.addWidget(back_button)

    def connect_signals(self):
        """Connect widget signals"""
        self.generate_button.clicked.connect(self.generate_files)

    def showEvent(self, event):
        """Handle tab being shown - generate files only on first time"""
        super().showEvent(event)

        if self.first_time_opened:
            self.first_time_opened = False
            self.generate_files()

    # MARK: - Event Handlers

    def on_profiles_updated(self):
        """Handle profiles updated - check sync status only"""
        self.check_and_update_sync_status()

    def on_variables_updated(self):
        """Handle variables updated - check sync status only"""
        self.check_and_update_sync_status()

    def on_generated_updated(self):
        """Handle generated updated - update file items and check sync"""
        self.update_file_items_from_main_window()
        self.check_and_update_sync_status()

    def check_and_update_sync_status(self):
        """Check if generated gcodes match processed gcodes and update highlighting"""
        if not self.main_window:
            return

        sync_status = self.main_window.check_processed_vs_generated()

        for side in ['right', 'left']:
            gcode_key = f"{side}_gcode"
            is_synced = sync_status.get(gcode_key, True)
            if self.file_items[side]:
                self.file_items[side].set_sync_status(is_synced)

    def update_file_items_from_main_window(self):
        """Update file items with content from main_window generated gcodes"""
        if not self.main_window:
            return

        for side in ['right', 'left']:
            gcode_key = f"{side}_gcode"
            content = self.main_window.get_generated_gcode(gcode_key)
            if self.file_items[side]:
                self.file_items[side].update_content(content)

    def on_file_content_changed(self, side, new_content):
        """Handle manual file content changes"""
        if not self.main_window:
            return

        gcode_key = f"{side}_gcode"
        self.main_window.update_generated_gcode(gcode_key, new_content)

    # MARK: - File Generation

    def generate_files(self):
        """Generate files - only when explicitly called"""
        if not self.main_window:
            return

        print("Generating files...")
        self.main_window.process_gcodes()
        self.main_window.copy_to_generated()
        print("Files generated successfully!")

    # MARK: - File Export

    def export_files(self):
        """Export right and left gcode files to the output directory"""
        if not self.main_window:
            QMessageBox.warning(self, "No Data", "No main window data available.")
            return

        has_files = any(
            self.file_items[side] and self.file_items[side].has_content()
            for side in ['right', 'left']
        )

        if not has_files:
            QMessageBox.warning(self, "No Files",
                              "No files available to export. Please generate files first.")
            return

        try:
            os.makedirs(self.output_dir, exist_ok=True)

            cnc_dir = os.path.join(self.output_dir, "cnc")
            if os.path.exists(cnc_dir):
                import shutil
                shutil.rmtree(cnc_dir)
            os.makedirs(cnc_dir, exist_ok=True)

            exported_files = []

            for side_en, side_fr in [('right', 'droite'), ('left', 'gauche')]:
                item = self.file_items[side_en]
                if item:
                    content = item.get_content()
                    if content:
                        content_windows = content.replace('\n', '\r\n').replace('\r\r\n', '\r\n')
                        filename = f"{side_fr}.txt"
                        filepath = os.path.join(cnc_dir, filename)
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content_windows)
                        exported_files.append(filepath)

            file_count = len(exported_files)
            QMessageBox.information(self, "Export Successful",
                                  f"Exported {file_count} files to:\n{cnc_dir}")

        except Exception as e:
            QMessageBox.critical(self, "Export Failed",
                               f"Failed to export files:\n{str(e)}")

    def browse_output_dir(self):
        """Browse for output directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.output_dir
        )
        if dir_path:
            self.output_dir = dir_path
            self.output_path.setText(dir_path)

    # MARK: - Configuration

    def get_app_config(self):
        """Get tab configuration for saving"""
        return {
            "output_dir": self.output_dir
        }

    def set_app_config(self, config):
        """Set tab configuration from loading"""
        self.output_dir = config.get("output_dir", self.output_dir)
        self.output_path.setText(self.output_dir)

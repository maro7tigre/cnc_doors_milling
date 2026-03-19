"""
Profile Tab

Profile selection tab with proper event subscriptions and no recursion loops.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Signal, Qt

from ..widgets.themed_widgets import ThemedSplitter, ThemedLabel, BlueButton, PurpleButton, GreenButton
from .widgets.profile_grid import ProfileGrid
from ..dialogs.profile_editor import ProfileEditor


class ProfileTab(QWidget):
    """Profile selection tab with proper event handling"""

    # MARK: - Signals
    next_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # MARK: - Properties
        self.main_window = parent
        self.selected_hinge = None
        self.selected_lock = None
        self.selected_barrel = None

        # MARK: - Recursion Protection
        self._updating_from_main_window = False

        # MARK: - UI Setup
        self.setup_ui()
        self.connect_signals()

        # MARK: - Event Subscriptions
        if self.main_window:
            self.main_window.events.subscribe('profiles', self.on_profiles_updated)
            self.main_window.events.subscribe('variables', self.on_variables_updated)

    # MARK: - UI Setup
    def setup_ui(self):
        """Setup the tab UI with three sections"""
        self.setStyleSheet("""
            ProfileTab {
                background-color: #282a36;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        top_layout = self.create_top_section()
        layout.addLayout(top_layout)

        middle_widget = self.create_middle_section()
        layout.addWidget(middle_widget, 1)

        bottom_layout = self.create_bottom_section()
        layout.addLayout(bottom_layout)

    def create_top_section(self):
        """Create top toolbar with buttons"""
        toolbar_layout = QHBoxLayout()

        self.save_project_button = BlueButton("Save Project")
        toolbar_layout.addWidget(self.save_project_button)

        self.load_project_button = BlueButton("Load Project")
        toolbar_layout.addWidget(self.load_project_button)

        toolbar_layout.addStretch()

        self.save_set_button = PurpleButton("Save Set")
        toolbar_layout.addWidget(self.save_set_button)

        self.load_set_button = PurpleButton("Load Set")
        toolbar_layout.addWidget(self.load_set_button)

        return toolbar_layout

    def create_middle_section(self):
        """Create middle section with three profile grids"""
        splitter = ThemedSplitter(Qt.Horizontal)

        # Left side - Hinge Profiles
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.hinge_grid = ProfileGrid("hinge", ProfileEditor)
        left_layout.addWidget(self.hinge_grid)

        # Center - Lock Profiles
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.lock_grid = ProfileGrid("lock", ProfileEditor)
        center_layout.addWidget(self.lock_grid)

        # Right side - Barrel Profiles
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.barrel_grid = ProfileGrid("barrel", ProfileEditor)
        right_layout.addWidget(self.barrel_grid)

        splitter.addWidget(left_widget)
        splitter.addWidget(center_widget)
        splitter.addWidget(right_widget)

        splitter.setSizes([400, 400, 400])

        return splitter

    def create_bottom_section(self):
        """Create bottom section with selection label and next button"""
        bottom_layout = QHBoxLayout()

        self.selection_label = ThemedLabel("Selected: [Hinge: None] [Lock: None] [Barrel: None]")
        self.selection_label.setStyleSheet("QLabel { font-weight: bold; padding: 5px; }")
        bottom_layout.addWidget(self.selection_label)

        bottom_layout.addStretch()

        self.next_button = GreenButton("Next →")
        self.next_button.setEnabled(False)
        bottom_layout.addWidget(self.next_button)

        return bottom_layout

    def connect_signals(self):
        """Connect UI signals"""
        self.hinge_grid.profile_selected.connect(self.on_profile_selected)
        self.hinge_grid.profile_deleted.connect(self.on_profile_deleted)
        self.lock_grid.profile_selected.connect(self.on_profile_selected)
        self.lock_grid.profile_deleted.connect(self.on_profile_deleted)
        self.barrel_grid.profile_selected.connect(self.on_profile_selected)
        self.barrel_grid.profile_deleted.connect(self.on_profile_deleted)

        self.next_button.clicked.connect(self.next_clicked)

    # MARK: - Event Handlers

    def on_profile_selected(self, profile_type, profile_name):
        """Handle profile selection from grids"""
        if profile_type == "hinge":
            self.selected_hinge = profile_name
            if self.main_window:
                self.main_window.update_dollar_variable("selected_hinge", profile_name)
        elif profile_type == "lock":
            self.selected_lock = profile_name
            if self.main_window:
                self.main_window.update_dollar_variable("selected_lock", profile_name)
        elif profile_type == "barrel":
            self.selected_barrel = profile_name
            if self.main_window:
                self.main_window.update_dollar_variable("selected_barrel", profile_name)

        # Update main window if all three selected
        if self.selected_hinge and self.selected_lock and self.selected_barrel and self.main_window:
            self.main_window.select_profiles(self.selected_hinge, self.selected_lock, self.selected_barrel)

        self.update_selection_display()

    def on_profile_deleted(self, profile_type, profile_name):
        """Handle profile deletion from grids"""
        if not self.main_window:
            return

        if profile_type == "hinge":
            self.main_window.update_hinge_profile(profile_name, None)
        elif profile_type == "lock":
            self.main_window.update_lock_profile(profile_name, None)
        elif profile_type == "barrel":
            self.main_window.update_barrel_profile(profile_name, None)

        # Clear selection if deleted profile was selected
        if profile_type == "hinge" and self.selected_hinge == profile_name:
            self.selected_hinge = None
            self.main_window.update_dollar_variable("selected_hinge", None)
        elif profile_type == "lock" and self.selected_lock == profile_name:
            self.selected_lock = None
            self.main_window.update_dollar_variable("selected_lock", None)
        elif profile_type == "barrel" and self.selected_barrel == profile_name:
            self.selected_barrel = None
            self.main_window.update_dollar_variable("selected_barrel", None)

        self.update_selection_display()

    # MARK: - Subscription Handlers

    def on_profiles_updated(self):
        """Handle profiles updated from main_window - UPDATE GRIDS ONLY"""
        if not self.main_window or self._updating_from_main_window:
            return

        hinge_profiles = self.main_window.hinges_profiles
        lock_profiles = self.main_window.locks_profiles
        barrel_profiles = self.main_window.barrels_profiles

        self.hinge_grid.update_profiles(hinge_profiles, self.selected_hinge)
        self.lock_grid.update_profiles(lock_profiles, self.selected_lock)
        self.barrel_grid.update_profiles(barrel_profiles, self.selected_barrel)

    def on_variables_updated(self):
        """Handle variables updated - SYNC SELECTION STATE ONLY"""
        if self._updating_from_main_window:
            return

        self._updating_from_main_window = True
        try:
            if not self.main_window:
                return

            dollar_vars = self.main_window.get_dollar_variable()
            new_selected_hinge = dollar_vars.get("selected_hinge")
            new_selected_lock = dollar_vars.get("selected_lock")
            new_selected_barrel = dollar_vars.get("selected_barrel")

            selection_changed = False

            if new_selected_hinge != self.selected_hinge:
                self.selected_hinge = new_selected_hinge
                selection_changed = True

            if new_selected_lock != self.selected_lock:
                self.selected_lock = new_selected_lock
                selection_changed = True

            if new_selected_barrel != self.selected_barrel:
                self.selected_barrel = new_selected_barrel
                selection_changed = True

            if selection_changed:
                self.hinge_grid.update_profiles(self.main_window.hinges_profiles, self.selected_hinge)
                self.lock_grid.update_profiles(self.main_window.locks_profiles, self.selected_lock)
                self.barrel_grid.update_profiles(self.main_window.barrels_profiles, self.selected_barrel)
                self.update_selection_display()

        finally:
            self._updating_from_main_window = False

    # MARK: - UI Updates
    def update_selection_display(self):
        """Update selection label and next button state"""
        hinge_text = self.selected_hinge or "None"
        lock_text = self.selected_lock or "None"
        barrel_text = self.selected_barrel or "None"
        self.selection_label.setText(
            f"Selected: [Hinge: {hinge_text}] [Lock: {lock_text}] [Barrel: {barrel_text}]"
        )

        all_selected = bool(self.selected_hinge and self.selected_lock and self.selected_barrel)
        self.next_button.setEnabled(all_selected)

from PySide6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QInputDialog, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QSettings, QObject, Signal
from .profile.profile_tab import ProfileTab
from .door.setup_tab import SetupTab
from .generate.generate_tab import GenerateTab
import json
import os
import re
import shutil
from datetime import datetime
from typing import Dict, Any, Callable, List


class EventManager(QObject):
    """Simple event manager for the 3 main update types"""

    # Event signals
    profiles_updated = Signal()  # Profile set, types, or profiles changed
    variables_updated = Signal()  # $variables changed
    generated_updated = Signal()  # Generated gcodes changed
    processed_updated = Signal()  # Processed gcodes changed

    def __init__(self):
        super().__init__()
        self._subscribers = {
            'profiles': [],
            'variables': [],
            'generated': [],
            'processed': []
        }

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to an event type"""
        if event_type in self._subscribers:
            self._subscribers[event_type].append(callback)

            # Connect Qt signal to callback
            if event_type == 'profiles':
                self.profiles_updated.connect(callback)
            elif event_type == 'variables':
                self.variables_updated.connect(callback)
            elif event_type == 'generated':
                self.generated_updated.connect(callback)
            elif event_type == 'processed':
                self.processed_updated.connect(callback)

    def emit_profiles_updated(self):
        """Emit profiles updated event"""
        self.profiles_updated.emit()

    def emit_variables_updated(self):
        """Emit variables updated event"""
        self.variables_updated.emit()

    def emit_generated_updated(self):
        """Emit generated updated event"""
        self.generated_updated.emit()

    def emit_processed_updated(self):
        """Emit processed updated event"""
        self.processed_updated.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CNC Door Wizard")

        # Event manager
        self.events = EventManager()

        # MARK: - Variables Initiation
        # Profile set dictionaries
        self.hinges_types = {}      # {type_name: {name, gcode, image, preview, variables}}
        self.locks_types = {}       # {type_name: {name, gcode, image, preview, variables}}
        self.barrels_types = {}     # {type_name: {name, gcode, image, preview, variables}}
        self.hinges_profiles = {}   # {profile_name: {name, type, l_variables, custom_variables, image}}
        self.locks_profiles = {}    # {profile_name: {name, type, l_variables, custom_variables, image}}
        self.barrels_profiles = {}  # {profile_name: {name, type, l_variables, custom_variables, image}}

        # Gcode dictionaries
        # current_gcodes: raw templates (hinge/lock/barrel from profiles, right/left user-editable)
        self.current_gcodes = {
            "hinge_gcode": None,
            "lock_gcode": None,
            "barrel_gcode": None,
            "right_gcode": None,
            "left_gcode": None
        }
        # processed/generated only track the user-facing output files
        self.processed_gcodes = {"right_gcode": None, "left_gcode": None}
        self.generated_gcodes = {"right_gcode": None, "left_gcode": None}

        # $variables dictionary - ordered as desired for the help dialog
        self.dollar_variables = {
            # Door dimensions
            "door_height": 2100,
            "door_width": 900,
            "door_depth": 40,

            # Machine offsets
            "machine_x_offset": 0,
            "machine_y_offset": 0,
            "machine_z_offset": 0,

            # Hinge configuration - shared Z position and X auto
            "hinge_z_position": 0,
            "hinge_z_auto": 0,
            "hinge_x_auto": 1,

            # Hinges 1-10 - individual X positions along door height
            "hinge1_active": 1,
            "hinge1_x_position": 150,
            "hinge1_x_auto": 1,
            "hinge2_active": 1,
            "hinge2_x_position": 0,
            "hinge2_x_auto": 1,
            "hinge3_active": 1,
            "hinge3_x_position": 0,
            "hinge3_x_auto": 1,
            "hinge4_active": 0,
            "hinge4_x_position": 0,
            "hinge4_x_auto": 1,
            "hinge5_active": 0,
            "hinge5_x_position": 0,
            "hinge5_x_auto": 1,
            "hinge6_active": 0,
            "hinge6_x_position": 0,
            "hinge6_x_auto": 1,
            "hinge7_active": 0,
            "hinge7_x_position": 0,
            "hinge7_x_auto": 1,
            "hinge8_active": 0,
            "hinge8_x_position": 0,
            "hinge8_x_auto": 1,
            "hinge9_active": 0,
            "hinge9_x_position": 0,
            "hinge9_x_auto": 1,
            "hinge10_active": 0,
            "hinge10_x_position": 0,
            "hinge10_x_auto": 1,

            # Lock configuration
            "lock_active": 1,
            "lock_x_position": 1050,
            "lock_x_auto": 1,
            "lock_z_position": 0,
            "lock_z_auto": 1,

            # Barrel configuration
            "barrel_active": 1,
            "barrel_x_position": 1050,
            "barrel_x_auto": 1,
            "barrel_y_position": 50,
            "barrel_y_auto": 1,

            # Door orientation
            "orientation": "right",

            # Processed gcode dollar variables (set by process_gcodes - two-pass pipeline)
            "hinges_gcode": "",
            "lock_gcode": "",
            "barrel_gcode": "",

            # Selected profiles
            "selected_hinge": None,
            "selected_lock": None,
            "selected_barrel": None,
        }

        # Hidden UI-layer active state — remembers user's checkbox preferences
        # independently of whether the matching profile is currently selected.
        # NOT exposed in the $ variable dialog.
        self.ui_state = {
            **{f"hinge{i+1}_active_ui": bool(self.dollar_variables.get(f"hinge{i+1}_active", 0))
               for i in range(10)},
            "lock_active_ui": bool(self.dollar_variables.get("lock_active", 0)),
            "barrel_active_ui": bool(self.dollar_variables.get("barrel_active", 0)),
        }

        # Initialize settings
        self.settings = QSettings("CNCDoorWizard", "AppConfig")

        self.default_config_init()

        # Setup UI
        self.setup_ui()

        # Load configurations
        self.load_app_config()
        self.load_profile_set(current=True)

        # Setup event subscriptions
        self.setup_event_subscriptions()

    def default_config_init(self):
        """Initialize default configurations if not set"""
        self.profiles_dir = "profiles"
        self.current_file = os.path.join(self.profiles_dir, "current.json")
        self.saved_dir = os.path.join(self.profiles_dir, "saved")
        self.projects_dir = "projects"

        # Ensure directories exist
        os.makedirs(self.saved_dir, exist_ok=True)
        os.makedirs(self.projects_dir, exist_ok=True)

    def setup_ui(self):
        """Setup user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create tabs
        self.profile_tab = ProfileTab(self)
        self.frame_tab = SetupTab(self)
        self.generate_tab = GenerateTab(self)

        # Add tabs
        self.tabs.addTab(self.profile_tab, "Profile Selection")
        self.tabs.addTab(self.frame_tab, "Door Setup")
        self.tabs.addTab(self.generate_tab, "Generate Files")

        # Initially disable tabs 2 and 3
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)

        # Connect basic UI signals
        self.connect_ui_signals()

        # Show window
        if not self.settings.contains("geometry"):
            self.showMaximized()
        else:
            self.show()

    def setup_event_subscriptions(self):
        """Setup event subscriptions for automatic updates"""

        # Subscribe to profile updates
        self.events.subscribe('profiles', self.on_profiles_updated)
        self.events.subscribe('profiles', self.update_tab_states)

        # Subscribe to variable updates
        self.events.subscribe('variables', self.on_variables_updated)

        # Subscribe to generated updates
        self.events.subscribe('generated', self.on_generated_updated)

        # Let tabs subscribe to events they care about
        if hasattr(self.profile_tab, 'setup_subscriptions'):
            self.profile_tab.setup_subscriptions(self.events)
        if hasattr(self.frame_tab, 'setup_subscriptions'):
            self.frame_tab.setup_subscriptions(self.events)
        if hasattr(self.generate_tab, 'setup_subscriptions'):
            self.generate_tab.setup_subscriptions(self.events)

    def connect_ui_signals(self):
        """Connect basic UI signals (not event-based)"""

        # Profile tab UI signals
        self.profile_tab.next_clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        self.profile_tab.save_project_button.clicked.connect(self.save_project)
        self.profile_tab.load_project_button.clicked.connect(self.load_project)
        self.profile_tab.save_set_button.clicked.connect(lambda: self.save_profile_set(current=False))
        self.profile_tab.load_set_button.clicked.connect(lambda: self.load_profile_set(current=False))

        # Frame tab UI signals
        self.frame_tab.back_clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        self.frame_tab.next_clicked.connect(lambda: self.tabs.setCurrentIndex(2))

        # Generate tab UI signals
        self.generate_tab.back_clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        self.generate_tab.generate_button.clicked.connect(self.generate_files)

    def closeEvent(self, event):
        """Save app configuration before closing"""
        self.save_app_config()
        event.accept()

    # MARK: - Path Conversion Helpers

    def _path_to_relative(self, path):
        """Convert absolute path to relative path if within profiles directory"""
        if not path:
            return path

        try:
            abs_path = os.path.abspath(path)
            profiles_abs = os.path.abspath(self.profiles_dir)

            if abs_path.startswith(profiles_abs + os.sep) or abs_path == profiles_abs:
                rel_path = os.path.relpath(abs_path, profiles_abs)
                return "./" + rel_path.replace("\\", "/")
            else:
                return abs_path

        except (ValueError, OSError):
            return path

    def _path_to_absolute(self, path):
        """Convert relative path to absolute path if it starts with ./"""
        if not path:
            return path

        try:
            if path.startswith("./"):
                rel_path = path[2:].replace("/", os.sep)
                abs_path = os.path.join(self.profiles_dir, rel_path)
                return os.path.abspath(abs_path)
            else:
                return path

        except (ValueError, OSError):
            return path

    def _convert_data_paths_to_relative(self, data):
        """Recursively convert image paths to relative in data structure"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key in ['image', 'preview'] and isinstance(value, str):
                    result[key] = self._path_to_relative(value)
                elif isinstance(value, (dict, list)):
                    result[key] = self._convert_data_paths_to_relative(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [self._convert_data_paths_to_relative(item) for item in data]
        else:
            return data

    def _convert_data_paths_to_absolute(self, data):
        """Recursively convert relative paths to absolute in data structure"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key in ['image', 'preview'] and isinstance(value, str):
                    result[key] = self._path_to_absolute(value)
                elif isinstance(value, (dict, list)):
                    result[key] = self._convert_data_paths_to_absolute(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [self._convert_data_paths_to_absolute(item) for item in data]
        else:
            return data

    # MARK: - Event Handlers (The 3 main update types)

    def on_profiles_updated(self):
        """Handle profiles updated event - triggered when profiles/types/sets change"""

        # Re-extract gcodes from selected profiles in case they changed
        selected_hinge = self.dollar_variables.get("selected_hinge")
        selected_lock = self.dollar_variables.get("selected_lock")
        selected_barrel = self.dollar_variables.get("selected_barrel")

        if selected_hinge:
            hinge_gcode = self.get_hinge_profile_gcode(selected_hinge)
            self.current_gcodes["hinge_gcode"] = hinge_gcode

        if selected_lock:
            lock_gcode = self.get_lock_profile_gcode(selected_lock)
            self.current_gcodes["lock_gcode"] = lock_gcode

        if selected_barrel:
            barrel_gcode = self.get_barrel_profile_gcode(selected_barrel)
            self.current_gcodes["barrel_gcode"] = barrel_gcode

        # Process gcodes with current variables
        self.process_gcodes()

        # Auto-save current profile set
        self.save_profile_set(current=True)

    def on_variables_updated(self):
        """Handle variables updated event - triggered when $variables change"""

        # Re-extract gcodes from selected profiles if they exist
        selected_hinge = self.dollar_variables.get("selected_hinge")
        selected_lock = self.dollar_variables.get("selected_lock")
        selected_barrel = self.dollar_variables.get("selected_barrel")

        if selected_hinge:
            hinge_gcode = self.get_hinge_profile_gcode(selected_hinge)
            if self.current_gcodes["hinge_gcode"] != hinge_gcode:
                self.current_gcodes["hinge_gcode"] = hinge_gcode

        if selected_lock:
            lock_gcode = self.get_lock_profile_gcode(selected_lock)
            if self.current_gcodes["lock_gcode"] != lock_gcode:
                self.current_gcodes["lock_gcode"] = lock_gcode

        if selected_barrel:
            barrel_gcode = self.get_barrel_profile_gcode(selected_barrel)
            if self.current_gcodes["barrel_gcode"] != barrel_gcode:
                self.current_gcodes["barrel_gcode"] = barrel_gcode

        # Always reprocess gcodes with current variables
        self.process_gcodes()

    def on_generated_updated(self):
        """Handle generated updated event - triggered when generated gcodes change"""
        print("Generated gcodes updated")

    def update_tab_states(self):
        """Update tab enabled states based on current data"""
        hinge_selected = self.dollar_variables.get("selected_hinge")
        lock_selected = self.dollar_variables.get("selected_lock")
        barrel_selected = self.dollar_variables.get("selected_barrel")

        # At least one profile must be selected to proceed
        any_selected = bool(hinge_selected or lock_selected or barrel_selected)

        if any_selected:
            self.tabs.setTabEnabled(1, True)

            door_configured = (
                self.dollar_variables.get("door_height") and
                self.dollar_variables.get("door_width")
            )
            if door_configured:
                self.tabs.setTabEnabled(2, True)
        else:
            self.tabs.setTabEnabled(1, False)
            self.tabs.setTabEnabled(2, False)

    # MARK: - Profile Updates

    def update_hinge_type(self, name: str, data: Dict[str, Any] = None):
        """Update hinge type (delete if data is None)"""
        if data is None:
            self.hinges_types.pop(name, None)
        else:
            self.hinges_types[name] = data
        self.events.emit_profiles_updated()

    def update_lock_type(self, name: str, data: Dict[str, Any] = None):
        """Update lock type (delete if data is None)"""
        if data is None:
            self.locks_types.pop(name, None)
        else:
            self.locks_types[name] = data
        self.events.emit_profiles_updated()

    def update_barrel_type(self, name: str, data: Dict[str, Any] = None):
        """Update barrel type (delete if data is None)"""
        if data is None:
            self.barrels_types.pop(name, None)
        else:
            self.barrels_types[name] = data
        self.events.emit_profiles_updated()

    def update_hinge_profile(self, name: str, data: Dict[str, Any] = None):
        """Update hinge profile (delete if data is None)"""
        if data is None:
            self.hinges_profiles.pop(name, None)
        else:
            self.hinges_profiles[name] = data
        self.events.emit_profiles_updated()

    def update_lock_profile(self, name: str, data: Dict[str, Any] = None):
        """Update lock profile (delete if data is None)"""
        if data is None:
            self.locks_profiles.pop(name, None)
        else:
            self.locks_profiles[name] = data
        self.events.emit_profiles_updated()

    def update_barrel_profile(self, name: str, data: Dict[str, Any] = None):
        """Update barrel profile (delete if data is None)"""
        if data is None:
            self.barrels_profiles.pop(name, None)
        else:
            self.barrels_profiles[name] = data
        self.events.emit_profiles_updated()

    def update_frame_gcode(self, right_gcode: str = None, left_gcode: str = None):
        """Update frame gcodes"""
        self.update_current_gcodes("right_gcode", right_gcode)
        self.update_current_gcodes("left_gcode", left_gcode)

    def select_profiles(self, hinge_profile: str, lock_profile: str, barrel_profile: str = None):
        """Select hinge, lock, and barrel profiles"""
        # Update variables
        self.dollar_variables["selected_hinge"] = hinge_profile
        self.dollar_variables["selected_lock"] = lock_profile
        if barrel_profile is not None:
            self.dollar_variables["selected_barrel"] = barrel_profile

        # Update current gcodes from selected profiles
        hinge_gcode = self.get_hinge_profile_gcode(hinge_profile)
        lock_gcode = self.get_lock_profile_gcode(lock_profile)

        self.update_current_gcodes("hinge_gcode", hinge_gcode)
        self.update_current_gcodes("lock_gcode", lock_gcode)

        if barrel_profile:
            barrel_gcode = self.get_barrel_profile_gcode(barrel_profile)
            self.update_current_gcodes("barrel_gcode", barrel_gcode)

    # MARK: - UI State (hidden active preferences)

    def update_ui_state(self, name: str, value):
        """Update a hidden UI-state variable."""
        self.ui_state[name] = value

    def get_ui_state(self, name: str = None):
        """Get a hidden UI-state variable (or the full dict if name is None)."""
        if name is None:
            return self.ui_state.copy()
        return self.ui_state.get(name, None)

    def select_profile(self, profile_type: str, profile_name: str):
        """Select one profile type, update its gcode, and restore active states."""
        dv_key = f"selected_{profile_type}"
        self.dollar_variables[dv_key] = profile_name

        if profile_type == "hinge":
            self.current_gcodes["hinge_gcode"] = self.get_hinge_profile_gcode(profile_name)
            count = (self.frame_tab.hinge_count_spin.value()
                     if hasattr(self.frame_tab, 'hinge_count_spin') else 10)
            comps_to_activate = [
                f"hinge{i+1}" for i in range(count)
                if self.ui_state.get(f"hinge{i+1}_active_ui", False)
            ]
        elif profile_type == "lock":
            self.current_gcodes["lock_gcode"] = self.get_lock_profile_gcode(profile_name)
            comps_to_activate = ["lock"] if self.ui_state.get("lock_active_ui", True) else []
        elif profile_type == "barrel":
            self.current_gcodes["barrel_gcode"] = self.get_barrel_profile_gcode(profile_name)
            comps_to_activate = ["barrel"] if self.ui_state.get("barrel_active_ui", True) else []
        else:
            return

        if comps_to_activate and hasattr(self.frame_tab, '_compute_order_and_write'):
            self.frame_tab._compute_order_and_write(force_active_add=comps_to_activate)

        self.events.emit_variables_updated()
        self.events.emit_profiles_updated()

    def deselect_profile(self, profile_type: str):
        """Deselect one profile type: save active-ui memory, zero actives, clear gcode."""
        dv_key = f"selected_{profile_type}"
        if self.dollar_variables.get(dv_key) is None:
            return

        if profile_type == "hinge":
            for i in range(10):
                self.ui_state[f"hinge{i+1}_active_ui"] = bool(
                    self.dollar_variables.get(f"hinge{i+1}_active", 0))
            self.current_gcodes["hinge_gcode"] = ""
            comps_to_deactivate = [f"hinge{i+1}" for i in range(10)]
        elif profile_type == "lock":
            self.ui_state["lock_active_ui"] = bool(self.dollar_variables.get("lock_active", 0))
            self.current_gcodes["lock_gcode"] = ""
            comps_to_deactivate = ["lock"]
        elif profile_type == "barrel":
            self.ui_state["barrel_active_ui"] = bool(self.dollar_variables.get("barrel_active", 0))
            self.current_gcodes["barrel_gcode"] = ""
            comps_to_deactivate = ["barrel"]
        else:
            return

        self.dollar_variables[dv_key] = None

        if hasattr(self.frame_tab, '_compute_order_and_write'):
            self.frame_tab._compute_order_and_write(force_inactive=comps_to_deactivate)

        self.events.emit_variables_updated()
        self.events.emit_profiles_updated()

    # MARK: - Variable Updates

    def update_dollar_variable(self, name: str, value: Any):
        """Update single $variable"""
        if name in self.dollar_variables:
            self.dollar_variables[name] = value
            self.events.emit_variables_updated()

    def update_dollar_variables(self, variables: Dict[str, Any]):
        """Update multiple $variables"""
        for name, value in variables.items():
            if name in self.dollar_variables:
                self.dollar_variables[name] = value
        self.events.emit_variables_updated()

    # MARK: - Profile Set

    def save_profile_set(self, current: bool = False):
        """Save current profile set with relative path support"""
        if current:
            filename = self.current_file
        else:
            default_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.json")
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Profile Set",
                os.path.join(self.saved_dir, default_name),
                "JSON Files (*.json)"
            )

        if filename:
            try:
                os.makedirs(os.path.dirname(filename), exist_ok=True)

                data = {
                    "hinges": {
                        "types": self.hinges_types,
                        "profiles": self.hinges_profiles
                    },
                    "locks": {
                        "types": self.locks_types,
                        "profiles": self.locks_profiles
                    },
                    "barrels": {
                        "types": self.barrels_types,
                        "profiles": self.barrels_profiles
                    },
                    "door_gcode": {
                        "right_gcode": self.current_gcodes["right_gcode"],
                        "left_gcode": self.current_gcodes["left_gcode"]
                    }
                }

                # Convert paths to relative for portability
                data = self._convert_data_paths_to_relative(data)

                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)

                if not current:
                    QMessageBox.information(self, "Success", "Profile set saved successfully!")
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save profile set: {str(e)}")
                return False
        return False

    def load_profile_set(self, current: bool = False):
        """Load profile set with relative path support"""
        if current:
            filename = self.current_file
            if not os.path.exists(filename):
                return False
        else:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Load Profile Set",
                self.saved_dir,
                "JSON Files (*.json)"
            )

        if filename and os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)

                # Convert relative paths back to absolute paths
                data = self._convert_data_paths_to_absolute(data)

                # Load types and profiles
                if "hinges" in data:
                    self.hinges_types = data["hinges"].get("types", {})
                    self.hinges_profiles = data["hinges"].get("profiles", {})
                if "locks" in data:
                    self.locks_types = data["locks"].get("types", {})
                    self.locks_profiles = data["locks"].get("profiles", {})
                if "barrels" in data:
                    self.barrels_types = data["barrels"].get("types", {})
                    self.barrels_profiles = data["barrels"].get("profiles", {})

                # Load door gcodes (support old "frame_gcode" key for backward compat)
                gcode_section = data.get("door_gcode") or data.get("frame_gcode", {})
                if gcode_section:
                    self.current_gcodes["right_gcode"] = gcode_section.get("right_gcode")
                    self.current_gcodes["left_gcode"] = gcode_section.get("left_gcode")

                if not current:
                    QMessageBox.information(self, "Success", "Profile set loaded successfully!")

                self.events.emit_profiles_updated()
                return True

            except Exception as e:
                if not current:
                    QMessageBox.critical(self, "Error", f"Failed to load profile set: {str(e)}")
                print(f"Error loading profile set: {str(e)}")
                return False
        return False

    # MARK: - Project Management
    def save_project(self):
        """Save project as a single JSON file with file dialog"""
        default_name = datetime.now().strftime("project_%Y-%m-%d_%H-%M-%S.json")

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            os.path.join(self.projects_dir, default_name),
            "JSON Files (*.json)"
        )

        if not filename:
            return False

        if not filename.lower().endswith('.json'):
            filename += '.json'

        try:
            os.makedirs(self.projects_dir, exist_ok=True)

            data = {
                "dollar_variables": self.dollar_variables,
                "generated_gcodes": self.generated_gcodes,
                "timestamp": datetime.now().isoformat()
            }

            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)

            QMessageBox.information(self, "Success", f"Project saved successfully to:\n{filename}")
            return True

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project: {str(e)}")
            return False

    def load_project(self):
        """Load complete project"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Project",
            self.projects_dir,
            "JSON Files (*.json)"
        )

        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)

                # CRITICAL: Update variables WITHOUT triggering auto-calculations
                if "dollar_variables" in data:
                    # Temporarily disable auto-calculations in frame tab
                    if hasattr(self.frame_tab, '_auto_calculation_running'):
                        old_auto_calc = self.frame_tab._auto_calculation_running
                        self.frame_tab._auto_calculation_running = True

                    # Update dollar variables
                    self.dollar_variables.update(data["dollar_variables"])

                    # Sync hidden ui_state from loaded active values
                    for i in range(10):
                        self.ui_state[f"hinge{i+1}_active_ui"] = bool(
                            self.dollar_variables.get(f"hinge{i+1}_active", 0))
                    self.ui_state["lock_active_ui"] = bool(self.dollar_variables.get("lock_active", 0))
                    self.ui_state["barrel_active_ui"] = bool(self.dollar_variables.get("barrel_active", 0))

                    # Force frame tab to rebuild hinge UI based on loaded data
                    if hasattr(self.frame_tab, 'rebuild_door_widgets_from_variables'):
                        self.frame_tab.rebuild_door_widgets_from_variables()

                    # Re-enable auto-calculations
                    if hasattr(self.frame_tab, '_auto_calculation_running'):
                        self.frame_tab._auto_calculation_running = old_auto_calc

                    # Now trigger the variable update events
                    self.events.emit_variables_updated()
                    self.update_tab_states()

                if "generated_gcodes" in data:
                    self.generated_gcodes = data["generated_gcodes"]
                    self.events.emit_generated_updated()

                QMessageBox.information(self, "Success", "Project loaded successfully!")
                return True

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load project: {str(e)}")
            return False

    # MARK: - Gcode Processing

    def update_current_gcodes(self, name: str, gcode: str):
        """Update current gcode by name"""
        if name in self.current_gcodes:
            self.current_gcodes[name] = gcode
            self.events.emit_profiles_updated()

    def process_gcodes(self):
        """Two-pass gcode processing pipeline.

        Pass 1: Process profile gcodes (hinge, lock, barrel) → store as dollar variables.
        Pass 2: Process right/left gcodes using complete dollar_variables (inc. sub-gcodes).
        """
        try:
            # Pass 1: Process profile sub-gcodes and inject into dollar_variables directly
            # (no event emission to avoid recursion)
            hinge_raw = self.current_gcodes.get("hinge_gcode")
            lock_raw = self.current_gcodes.get("lock_gcode")
            barrel_raw = self.current_gcodes.get("barrel_gcode")

            self.dollar_variables["hinges_gcode"] = (
                self.replace_dollar_variables(hinge_raw) if hinge_raw else ""
            )
            self.dollar_variables["lock_gcode"] = (
                self.replace_dollar_variables(lock_raw) if lock_raw else ""
            )
            self.dollar_variables["barrel_gcode"] = (
                self.replace_dollar_variables(barrel_raw) if barrel_raw else ""
            )

            # Pass 2: Process right/left gcodes with now-complete dollar_variables
            for name in ["right_gcode", "left_gcode"]:
                gcode = self.current_gcodes.get(name)
                if gcode:
                    self.processed_gcodes[name] = self.replace_dollar_variables(gcode)
                else:
                    self.processed_gcodes[name] = None

            self.events.emit_processed_updated()
        except Exception as e:
            print(f"Error processing gcodes: {e}")

    def update_generated_gcode(self, name: str, gcode: str):
        """Update single generated gcode"""
        if name in self.generated_gcodes:
            self.generated_gcodes[name] = gcode
            self.events.emit_generated_updated()

    def copy_to_generated(self):
        """Copy processed gcodes to generated"""
        self.generated_gcodes = self.processed_gcodes.copy()
        self.events.emit_generated_updated()


    def check_processed_vs_generated(self) -> Dict[str, bool]:
        """Check if processed gcodes match generated gcodes"""
        comparison = {}

        for gcode_name in ["right_gcode", "left_gcode"]:
            processed = self.processed_gcodes.get(gcode_name, "")
            generated = self.generated_gcodes.get(gcode_name, "")

            processed = processed or ""
            generated = generated or ""

            comparison[gcode_name] = (processed == generated)

        return comparison

    def replace_dollar_variables(self, gcode: str) -> str:
        """Replace $variables in gcode with actual values"""
        if not gcode:
            return gcode

        result = gcode
        for var_name, value in self.dollar_variables.items():
            pattern = f"{{\\${var_name}}}"
            if value is not None:
                result = re.sub(pattern, str(value), result)
        return result

    def replace_profile_variables(self, gcode: str, l_variables: Dict[str, Any], custom_variables: Dict[str, Any]) -> str:
        """Replace L and custom variables in profile gcode"""
        if not gcode:
            return gcode

        result = gcode

        # Replace L variables - handle both {L1} and {L1:default} formats
        if l_variables:
            for var_name, value in l_variables.items():
                if value is not None and str(value).strip():
                    pattern = rf'\{{{re.escape(var_name)}(?::[^}}]+)?\}}'
                    result = re.sub(pattern, str(value), result)

        # Replace custom variables - handle both {var} and {var:default} formats
        if custom_variables:
            for var_name, value in custom_variables.items():
                if value is not None and str(value).strip():
                    pattern = rf'\{{{re.escape(var_name)}(?::[^}}]+)?\}}'
                    result = re.sub(pattern, str(value), result)

        return result

    # MARK: - Getters

    def get_hinge_type(self, name: str) -> Dict[str, Any]:
        """Get hinge type data"""
        return self.hinges_types.get(name, {})

    def get_lock_type(self, name: str) -> Dict[str, Any]:
        """Get lock type data"""
        return self.locks_types.get(name, {})

    def get_barrel_type(self, name: str) -> Dict[str, Any]:
        """Get barrel type data"""
        return self.barrels_types.get(name, {})

    def get_hinge_profile(self, name: str) -> Dict[str, Any]:
        """Get hinge profile data"""
        return self.hinges_profiles.get(name, {})

    def get_lock_profile(self, name: str) -> Dict[str, Any]:
        """Get lock profile data"""
        return self.locks_profiles.get(name, {})

    def get_barrel_profile(self, name: str) -> Dict[str, Any]:
        """Get barrel profile data"""
        return self.barrels_profiles.get(name, {})

    def get_hinge_profile_gcode(self, name: str) -> str:
        """Get hinge profile gcode with variables replaced"""
        profile = self.get_hinge_profile(name)
        if not profile or not profile.get("type"):
            return ""

        hinge_type = self.get_hinge_type(profile["type"])
        if not hinge_type or not hinge_type.get("gcode"):
            return ""

        gcode = hinge_type["gcode"]
        l_variables = profile.get("l_variables", {})
        custom_variables = profile.get("custom_variables", {})

        return self.replace_profile_variables(gcode, l_variables, custom_variables)

    def get_lock_profile_gcode(self, name: str) -> str:
        """Get lock profile gcode with variables replaced"""
        profile = self.get_lock_profile(name)
        if not profile or not profile.get("type"):
            return ""

        lock_type = self.get_lock_type(profile["type"])
        if not lock_type or not lock_type.get("gcode"):
            return ""

        gcode = lock_type["gcode"]
        l_variables = profile.get("l_variables", {})
        custom_variables = profile.get("custom_variables", {})

        return self.replace_profile_variables(gcode, l_variables, custom_variables)

    def get_barrel_profile_gcode(self, name: str) -> str:
        """Get barrel profile gcode with variables replaced"""
        profile = self.get_barrel_profile(name)
        if not profile or not profile.get("type"):
            return ""

        barrel_type = self.get_barrel_type(profile["type"])
        if not barrel_type or not barrel_type.get("gcode"):
            return ""

        gcode = barrel_type["gcode"]
        l_variables = profile.get("l_variables", {})
        custom_variables = profile.get("custom_variables", {})

        return self.replace_profile_variables(gcode, l_variables, custom_variables)

    def get_current_gcode(self, name: str) -> str:
        """Get current gcode"""
        return self.current_gcodes.get(name, "")

    def get_processed_gcode(self, name: str) -> str:
        """Get processed gcode"""
        return self.processed_gcodes.get(name, "")

    def get_generated_gcode(self, name: str) -> str:
        """Get generated gcode"""
        return self.generated_gcodes.get(name, "")

    def get_dollar_variable(self, name: str = None):
        """Get $variable or all $variables if name is None"""
        if name is None:
            return self.dollar_variables.copy()
        return self.dollar_variables.get(name, "")

    # MARK: - App Config

    def save_app_config(self):
        """Save application configuration"""
        try:
            config = {
                "geometry": self.saveGeometry().data().hex(),
                "windowState": self.saveState().data().hex()
            }

            if hasattr(self.profile_tab, 'get_app_config'):
                config["profile_tab"] = self.profile_tab.get_app_config()
            if hasattr(self.frame_tab, 'get_app_config'):
                config["frame_tab"] = self.frame_tab.get_app_config()
            if hasattr(self.generate_tab, 'get_app_config'):
                config["generate_tab"] = self.generate_tab.get_app_config()

            self.settings.setValue("app_config", json.dumps(config))
            self.settings.sync()
        except Exception as e:
            print(f"Error saving app config: {str(e)}")

    def load_app_config(self):
        """Load application configuration"""
        try:
            config_str = self.settings.value("app_config")
            if not config_str:
                return

            config = json.loads(config_str)

            if "geometry" in config:
                self.restoreGeometry(bytes.fromhex(config["geometry"]))
            if "windowState" in config:
                self.restoreState(bytes.fromhex(config["windowState"]))

            if hasattr(self.profile_tab, 'set_app_config') and "profile_tab" in config:
                self.profile_tab.set_app_config(config["profile_tab"])
            if hasattr(self.frame_tab, 'set_app_config') and "frame_tab" in config:
                self.frame_tab.set_app_config(config["frame_tab"])
            if hasattr(self.generate_tab, 'set_app_config') and "generate_tab" in config:
                self.generate_tab.set_app_config(config["generate_tab"])
        except Exception as e:
            print(f"Error loading app config: {str(e)}")

    def generate_files(self):
        """Generate final gcode files"""
        # Copy processed to generated
        self.copy_to_generated()
        print("Files generated successfully!")

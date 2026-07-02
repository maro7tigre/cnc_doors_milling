"""
Frame Tab (Door Setup)

Door milling configuration: hinges (up to 10), lock, and barrel.
No PM group. Clean architecture with predictable update flow.
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
                               QButtonGroup, QSizePolicy, QScrollArea,
                               QFileDialog, QMessageBox)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDoubleValidator, QPixmap, QFont
import os

from ..widgets.themed_widgets import (ThemedSplitter, ThemedLabel, ThemedRadioButton,
                                    ThemedGroupBox, PurpleButton, GreenButton,
                                    ThemedCheckBox, ThemedSpinBox, ThemedLineEdit)
from ..widgets.simple_widgets import ClickableLabel, ErrorLineEdit, ScaledPreviewLabel
from .widgets.frame_preview import FramePreview
from .widgets.order_widget import OrderWidget
from ..dialogs.spreadsheet_picker_dialog import SpreadsheetPickerDialog


class SetupTab(QWidget):
    """Door configuration tab"""
    back_clicked = Signal()
    next_clicked = Signal()

    MAX_DOOR_HEIGHT = 3000
    MIN_DOOR_HEIGHT = 840

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # MARK: - Auto-calculation control
        self._auto_calculation_running = False
        self._updating_order = False

        # MARK: - Spreadsheet import state
        self._spreadsheet_file: str | None = None
        self._spreadsheet_last_row: int | None = None  # 0-based index into data rows
        self._ss_is_temp: bool = False          # True when file was auto-created (not yet bundled)
        self._ss_picked_info: dict | None = None  # display data for the last picked row

        # MARK: - UI Setup
        self.setup_ui()
        self.apply_styling()
        self.connect_signals()

        # MARK: - Event Subscriptions
        if self.main_window:
            self.main_window.events.subscribe('variables', self.on_variables_updated)

        # MARK: - Initial Setup
        self.setup_initial_values()

    # MARK: - UI Setup

    def apply_styling(self):
        """Apply dark theme styling"""
        self.setStyleSheet("""
            FrameTab {
                background-color: #282a36;
                color: #ffffff;
            }
        """)

    def setup_ui(self):
        """Initialize user interface with three-panel layout"""
        main_layout = QVBoxLayout(self)

        # Content area with splitter
        content_splitter = ThemedSplitter(Qt.Horizontal)
        main_layout.addWidget(content_splitter)

        left_widget = self.create_left_panel()
        content_splitter.addWidget(left_widget)

        middle_widget = self.create_middle_panel()
        content_splitter.addWidget(middle_widget)

        right_widget = self.create_right_panel()
        content_splitter.addWidget(right_widget)

        content_splitter.setSizes([300, 400, 300])

        nav_layout = self.create_navigation()
        main_layout.addLayout(nav_layout)

    def create_left_panel(self):
        """Create left panel with door dimensions and parameter preview"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Door dimensions group
        door_group = ThemedGroupBox("Door Configuration")
        door_layout = QFormLayout()
        door_group.setLayout(door_layout)

        self.height_input = SimpleDollarLineEdit("door_height", self)
        self.height_input.setValidator(QDoubleValidator(self.MIN_DOOR_HEIGHT, self.MAX_DOOR_HEIGHT, 2))
        door_layout.addRow("Door Height (mm):", self.height_input)

        self.width_input = SimpleDollarLineEdit("door_width", self)
        self.width_input.setValidator(QDoubleValidator(100, 2000, 2))
        door_layout.addRow("Door Width (mm):", self.width_input)

        self.depth_input = SimpleDollarLineEdit("door_depth", self)
        self.depth_input.setValidator(QDoubleValidator(10, 200, 2))
        door_layout.addRow("Door Depth (mm):", self.depth_input)

        # Machine offsets (hidden but available as $ variables)
        self.x_offset_input = SimpleDollarLineEdit("machine_x_offset", self)
        self.y_offset_input = SimpleDollarLineEdit("machine_y_offset", self)
        self.z_offset_input = SimpleDollarLineEdit("machine_z_offset", self)

        layout.addWidget(door_group)

        # --- Lock Configuration ---
        lock_group = ThemedGroupBox("Lock Configuration")
        lock_layout = QVBoxLayout()
        lock_group.setLayout(lock_layout)

        self.lock_active_check = SimpleDollarCheckBox("lock_active", "Active", self)
        lock_layout.addWidget(self.lock_active_check)

        lock_x_layout = QHBoxLayout()
        self.lock_x_auto_check = SimpleDollarCheckBox("lock_x_auto", "Auto", self)
        lock_x_layout.addWidget(self.lock_x_auto_check)
        lock_x_layout.addWidget(ThemedLabel("X:"))
        self.lock_x_input = SimpleDollarLineEdit("lock_x_position", self)
        self.lock_x_input.setValidator(QDoubleValidator(0, self.MAX_DOOR_HEIGHT, 2))
        lock_x_layout.addWidget(self.lock_x_input)
        lock_layout.addLayout(lock_x_layout)

        lock_z_layout = QHBoxLayout()
        self.lock_z_auto_check = SimpleDollarCheckBox("lock_z_auto", "Auto", self)
        lock_z_layout.addWidget(self.lock_z_auto_check)
        lock_z_layout.addWidget(ThemedLabel("Z:"))
        self.lock_z_input = SimpleDollarLineEdit("lock_z_position", self)
        self.lock_z_input.setValidator(QDoubleValidator(-500, 500, 2))
        lock_z_layout.addWidget(self.lock_z_input)
        lock_layout.addLayout(lock_z_layout)

        layout.addWidget(lock_group)

        # --- Barrel Configuration ---
        barrel_group = ThemedGroupBox("Barrel Configuration")
        barrel_layout = QVBoxLayout()
        barrel_group.setLayout(barrel_layout)

        self.barrel_active_check = SimpleDollarCheckBox("barrel_active", "Active", self)
        barrel_layout.addWidget(self.barrel_active_check)

        barrel_x_layout = QHBoxLayout()
        self.barrel_x_auto_check = SimpleDollarCheckBox("barrel_x_auto", "Auto", self)
        barrel_x_layout.addWidget(self.barrel_x_auto_check)
        barrel_x_layout.addWidget(ThemedLabel("X:"))
        self.barrel_x_input = SimpleDollarLineEdit("barrel_x_position", self)
        self.barrel_x_input.setValidator(QDoubleValidator(0, self.MAX_DOOR_HEIGHT, 2))
        barrel_x_layout.addWidget(self.barrel_x_input)
        barrel_layout.addLayout(barrel_x_layout)

        barrel_y_layout = QHBoxLayout()
        self.barrel_y_auto_check = SimpleDollarCheckBox("barrel_y_auto", "Auto", self)
        barrel_y_layout.addWidget(self.barrel_y_auto_check)
        barrel_y_layout.addWidget(ThemedLabel("Y:"))
        self.barrel_y_input = SimpleDollarLineEdit("barrel_y_position", self)
        self.barrel_y_input.setValidator(QDoubleValidator(0, 500, 2))
        barrel_y_layout.addWidget(self.barrel_y_input)
        barrel_layout.addLayout(barrel_y_layout)

        layout.addWidget(barrel_group)

        # Parameter preview
        preview_group = ThemedGroupBox("Parameter Preview")
        preview_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)

        self.param_preview = ScaledPreviewLabel()
        self.param_preview.setText("No preview")
        preview_layout.addWidget(self.param_preview, 1)

        layout.addWidget(preview_group, 1)

        return widget

    def create_middle_panel(self):
        """Create middle panel with preview and orientation switch"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Orientation switch with G-code edit links
        orientation_group = ThemedGroupBox("Door Orientation")
        orientation_layout = QVBoxLayout()
        orientation_group.setLayout(orientation_layout)

        radio_layout = QHBoxLayout()

        self.orientation_group = SimpleDollarRadioGroup("orientation", self)

        self.right_radio = ThemedRadioButton("Right (droite)")
        self.left_radio = ThemedRadioButton("Left (gauche)")

        self.orientation_group.add_button(self.right_radio, "right")
        self.orientation_group.add_button(self.left_radio, "left")

        radio_layout.addWidget(self.right_radio)
        self.right_gcode_link = ClickableLabel("Edit")
        self.right_gcode_link.clicked.connect(self.edit_right_gcode)
        radio_layout.addWidget(self.right_gcode_link)

        radio_layout.addStretch()

        radio_layout.addWidget(self.left_radio)
        self.left_gcode_link = ClickableLabel("Edit")
        self.left_gcode_link.clicked.connect(self.edit_left_gcode)
        radio_layout.addWidget(self.left_gcode_link)

        orientation_layout.addLayout(radio_layout)

        layout.addWidget(orientation_group)

        # Preview area
        self.preview = FramePreview()
        layout.addWidget(self.preview, 1)

        # Spreadsheet import section
        layout.addWidget(self._create_spreadsheet_section())

        return widget

    def create_right_panel(self):
        """Create right panel with hinge configuration"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # --- Hinge Configuration ---
        hinge_group = ThemedGroupBox("Hinge Configuration")
        hinge_layout = QVBoxLayout()
        hinge_group.setLayout(hinge_layout)

        # Hinge count
        count_layout = QHBoxLayout()
        count_layout.addWidget(ThemedLabel("Number of Hinges:"))
        self.hinge_count_spin = ThemedSpinBox()
        self.hinge_count_spin.setRange(0, 10)
        self.hinge_count_spin.setValue(3)
        self.hinge_count_spin.valueChanged.connect(self.update_hinge_count)
        count_layout.addWidget(self.hinge_count_spin)
        count_layout.addStretch()
        hinge_layout.addLayout(count_layout)

        # Shared Z position (no auto — defaults to 0, user sets manually)
        hinge_z_layout = QHBoxLayout()
        hinge_z_layout.addWidget(ThemedLabel("Z (all):"))
        self.hinge_z_input = SimpleDollarLineEdit("hinge_z_position", self)
        self.hinge_z_input.setValidator(QDoubleValidator(-500, 500, 2))
        hinge_z_layout.addWidget(self.hinge_z_input)
        hinge_layout.addLayout(hinge_z_layout)

        # Shared X auto position
        hinge_x_auto_layout = QHBoxLayout()
        self.hinge_x_auto_check = SimpleDollarCheckBox("hinge_x_auto", "Auto X (all)", self)
        hinge_x_auto_layout.addWidget(self.hinge_x_auto_check)
        hinge_x_auto_layout.addStretch()
        hinge_layout.addLayout(hinge_x_auto_layout)

        # Hinge positions container (scrollable for up to 10 hinges)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMaximumHeight(280)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.hinge_positions_widget = QWidget()
        self.hinge_positions_layout = QVBoxLayout(self.hinge_positions_widget)
        self.hinge_positions_layout.setContentsMargins(0, 0, 0, 0)
        self.hinge_positions_layout.setSpacing(2)
        scroll.setWidget(self.hinge_positions_widget)
        hinge_layout.addWidget(scroll)

        # Tracked arrays (rebuilt by update_hinge_count)
        self.hinge_inputs = []
        self.hinge_active_checks = []

        layout.addWidget(hinge_group, 1)

        # --- Milling Order ---
        order_group = ThemedGroupBox("Milling Order")
        order_group_layout = QVBoxLayout()
        order_group.setLayout(order_group_layout)

        self.order_widget = OrderWidget()
        self.order_widget.order_changed.connect(self._on_order_widget_changed)
        order_group_layout.addWidget(self.order_widget)

        layout.addWidget(order_group, 1)

        return widget

    def create_navigation(self):
        """Create bottom navigation buttons"""
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        self.back_button = PurpleButton("← Back")
        self.next_button = GreenButton("Next →")

        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.next_button)

        return nav_layout

    def connect_signals(self):
        """Connect widget signals"""
        self.back_button.clicked.connect(self.back_clicked)
        self.next_button.clicked.connect(self.next_clicked)
        self.height_input.editingFinished.connect(self.enforce_height_limits)

    def setup_initial_values(self):
        """Setup initial values"""
        self.update_hinge_count(3)
        self.update_ui_from_main_window()
        self.run_auto_calculations()

    # MARK: - Widget Rebuilding for Project Loading

    def rebuild_door_widgets_from_variables(self):
        """Rebuild hinge widgets based on current dollar variables - called during project loading"""
        if not self.main_window:
            return

        # Count active hinges from dollar variables (highest active index)
        active_count = 0
        for i in range(10):
            if self.main_window.get_dollar_variable(f"hinge{i+1}_active"):
                active_count = i + 1

        self.hinge_count_spin.blockSignals(True)
        self.hinge_count_spin.setValue(active_count)
        self.hinge_count_spin.blockSignals(False)

        self.rebuild_hinge_inputs(active_count)
        self._rebuild_order_widget_items()
        self.update_enabled_states()

    def rebuild_hinge_inputs(self, count):
        """Rebuild hinge position inputs to match the specified count"""
        # Clear existing inputs
        while self.hinge_positions_layout.count():
            item = self.hinge_positions_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        self.hinge_inputs = []
        self.hinge_active_checks = []

        for i in range(count):
            row_widget = QWidget()
            hinge_layout = QHBoxLayout(row_widget)
            hinge_layout.setContentsMargins(0, 0, 0, 0)

            hinge_layout.addWidget(ThemedLabel(f"H{i+1}:"))

            # X position input
            position_input = SimpleDollarLineEdit(f"hinge{i+1}_x_position", self)
            position_input.setValidator(QDoubleValidator(0, self.MAX_DOOR_HEIGHT, 2))
            hinge_layout.addWidget(position_input)
            self.hinge_inputs.append(position_input)

            # Active checkbox
            active_check = SimpleDollarCheckBox(f"hinge{i+1}_active", "On", self)
            hinge_layout.addWidget(active_check)
            self.hinge_active_checks.append(active_check)

            self.hinge_positions_layout.addWidget(row_widget)

        # Sync values from main_window
        for w in self.hinge_inputs:
            w.update_from_main_window()
        for w in self.hinge_active_checks:
            w.update_from_main_window()

    # MARK: - Auto-Calculation System

    def run_auto_calculations(self):
        """Unified auto-calculation system"""
        if self._auto_calculation_running or not self.main_window:
            return

        self._auto_calculation_running = True
        try:
            changes = {}
            dv = self.main_window.get_dollar_variable

            door_height = dv("door_height") or self.MIN_DOOR_HEIGHT
            door_depth = dv("door_depth") or 40
            count = self.hinge_count_spin.value()

            # 1. Individual hinge X positions
            if count > 0 and bool(dv("hinge_x_auto")):
                auto_positions = self._calculate_hinge_x_positions(count, door_height)
                for i in range(count):
                    if i < len(auto_positions):
                        changes[f"hinge{i+1}_x_position"] = round(auto_positions[i], 1)

            # 2. Lock X position
            if bool(dv("lock_x_auto")):
                changes["lock_x_position"] = round(door_height / 2, 1)

            # 3. Lock Z position
            if bool(dv("lock_z_auto")):
                changes["lock_z_position"] = round(door_depth / 2, 1)

            # 4. Barrel X position (follows lock X by default)
            if bool(dv("barrel_x_auto")):
                lock_x = changes.get("lock_x_position", dv("lock_x_position") or door_height / 2)
                changes["barrel_x_position"] = round(lock_x, 1)

            # 5. Barrel Y position
            if bool(dv("barrel_y_auto")):
                changes["barrel_y_position"] = dv("barrel_y_position") or 50

            if changes:
                self.main_window.update_dollar_variables(changes)

        finally:
            self._auto_calculation_running = False

    def _calculate_hinge_x_positions(self, count, door_height):
        """Calculate hinge X positions distributed over door height"""
        if count <= 0 or not door_height or door_height <= 0:
            return []

        first = 150.0
        last = 1800.0 if door_height >= 2000 else door_height - 200.0

        if count == 1:
            return [door_height / 2]
        elif count == 2:
            return [first, last]
        elif count == 3:
            middle = first + (last - first) / 2.5
            return [first, middle, last]
        elif count == 4:
            total = last - first
            d1 = total / 4.75
            return [first, first + d1, first + d1 + 1.5 * d1, last]
        else:
            # Equal spacing for 5-10 hinges
            step = (last - first) / (count - 1)
            return [first + i * step for i in range(count)]

    # MARK: - Event Handlers

    def on_variables_updated(self):
        """Handle variables updated from main_window"""
        self.update_ui_from_main_window()
        self.run_auto_calculations()
        self.update_preview()
        self.update_enabled_states()

    # MARK: - Milling Order System

    def _compute_order_and_write(self, force_inactive=None, force_active_add=None):
        """Recompute sequential order numbers and write them to dollar variables.

        force_inactive : list of component IDs to mark as 0 (regardless of current value)
        force_active_add : list of component IDs to append to the end of the order
                           (only if not already active)
        Active value 0  → component not milled.
        Active value N  → component is N-th in the milling sequence.
        """
        if self._updating_order or not self.main_window:
            return

        force_inactive = set(force_inactive or [])
        force_active_add = list(force_active_add or [])

        dv = self.main_window.get_dollar_variable
        count = self.hinge_count_spin.value()
        all_components = ["lock"] + [f"hinge{i+1}" for i in range(10)] + ["barrel"]

        # Components whose profile type is not selected must be inactive — this is
        # the authoritative sync point so the checkbox, dollar_variable, and preview
        # never diverge (catches the startup case where defaults are non-zero).
        for comp in all_components:
            if comp not in force_inactive and not self._is_profile_active_for(comp):
                force_inactive.add(comp)
        # Don't force-activate a component for an unselected profile type
        force_active_add = [c for c in force_active_add if c not in force_inactive]

        # Build current ordered list from existing numeric values (skip force_inactive)
        active_with_order = []
        for comp in all_components:
            if comp in force_inactive:
                continue
            val = dv(f"{comp}_active")
            try:
                n = int(val)
            except (TypeError, ValueError):
                n = 0
            if n > 0:
                active_with_order.append((comp, n))

        active_with_order.sort(key=lambda x: x[1])
        current_order = [c for c, _ in active_with_order]

        # Append newly active components at the end
        for comp in force_active_add:
            if comp not in current_order:
                current_order.append(comp)

        # Build changes dict: sequential numbers for active, 0 for everything else
        changes = {}
        for idx, comp in enumerate(current_order):
            changes[f"{comp}_active"] = idx + 1
        for comp in all_components:
            if comp not in current_order:
                changes[f"{comp}_active"] = 0
        # Hinges beyond current count must always be 0
        for i in range(count, 10):
            changes[f"hinge{i+1}_active"] = 0

        self._updating_order = True
        try:
            self.main_window.update_dollar_variables(changes)
            self.order_widget.set_order(current_order)
            # Refresh active checkboxes so they show checked/unchecked correctly
            for w in [self.lock_active_check] + self.hinge_active_checks + [self.barrel_active_check]:
                w.update_from_main_window()
        finally:
            self._updating_order = False

    def _on_order_widget_changed(self, order_list):
        """Handle drag-reorder in the OrderWidget → rewrite numeric active values."""
        if self._updating_order or not self.main_window:
            return

        changes = {}
        for idx, comp in enumerate(order_list):
            changes[f"{comp}_active"] = idx + 1
        # Components not in the new order become 0
        for i in range(10):
            comp = f"hinge{i+1}"
            if comp not in order_list:
                changes[f"{comp}_active"] = 0
        if "lock" not in order_list:
            changes["lock_active"] = 0
        if "barrel" not in order_list:
            changes["barrel_active"] = 0

        self._updating_order = True
        try:
            self.main_window.update_dollar_variables(changes)
            for w in [self.lock_active_check] + self.hinge_active_checks + [self.barrel_active_check]:
                w.update_from_main_window()
        finally:
            self._updating_order = False

    def _rebuild_order_widget_items(self):
        """Restore order widget from numeric active values (used when loading a project)."""
        if not self.main_window:
            return

        dv = self.main_window.get_dollar_variable
        count = self.hinge_count_spin.value()

        active = []
        val = dv("lock_active")
        try:
            n = int(val)
        except (TypeError, ValueError):
            n = 0
        if n > 0:
            active.append(("lock", n))

        for i in range(count):
            val = dv(f"hinge{i+1}_active")
            try:
                n = int(val)
            except (TypeError, ValueError):
                n = 0
            if n > 0:
                active.append((f"hinge{i+1}", n))

        val = dv("barrel_active")
        try:
            n = int(val)
        except (TypeError, ValueError):
            n = 0
        if n > 0:
            active.append(("barrel", n))

        active.sort(key=lambda x: x[1])
        order_list = [c for c, _ in active]

        self._updating_order = True
        try:
            self.order_widget.set_order(order_list)
        finally:
            self._updating_order = False

    def on_auto_state_changed(self):
        """Handle auto checkbox state changes"""
        self.update_enabled_states()

    def _is_profile_active_for(self, comp: str) -> bool:
        """Return True if the profile for this component is currently selected."""
        if not self.main_window:
            return True
        dv = self.main_window.get_dollar_variable
        if comp.startswith("hinge"):
            return bool(dv("selected_hinge"))
        if comp == "lock":
            return bool(dv("selected_lock"))
        if comp == "barrel":
            return bool(dv("selected_barrel"))
        return True

    def on_variable_changed(self, var_name, value):
        """Handle variable changes from simple dollar widgets"""
        if self.main_window and not self._auto_calculation_running:
            if var_name.endswith("_active"):
                comp = var_name.replace("_active", "")
                # Persist the user's intention regardless of profile state
                self.main_window.update_ui_state(f"{var_name}_ui", bool(value))
                # Only feed into the order system if the profile is selected
                if self._is_profile_active_for(comp):
                    if bool(value):
                        self._compute_order_and_write(force_active_add=[comp])
                    else:
                        self._compute_order_and_write(force_inactive=[comp])
            else:
                self.main_window.update_dollar_variable(var_name, value)
                if var_name.endswith("_auto"):
                    self.update_enabled_states()

    # MARK: - Parameter Image Preview

    def on_parameter_field_focused(self, variable_name: str):
        """When a parameter input gets focus, show its preview image."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        images_dir = os.path.join(project_root, "parameter_images")

        exts = [".png", ".jpg", ".jpeg"]
        image_path = None

        for ext in exts:
            candidate = os.path.join(images_dir, f"{variable_name}{ext}")
            if os.path.exists(candidate):
                image_path = candidate
                break

        if image_path:
            pix = QPixmap(image_path)
            if not pix.isNull():
                self.param_preview.setPixmap(pix)
                return

        if hasattr(self, 'param_preview') and self.param_preview is not None:
            self.param_preview.setText("No preview")

    def update_hinge_count(self, count):
        """Update hinge position inputs based on count"""
        # Clear existing
        while self.hinge_positions_layout.count():
            item = self.hinge_positions_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        self.hinge_inputs = []
        self.hinge_active_checks = []

        changes = {}

        for i in range(count):
            row_widget = QWidget()
            hinge_layout = QHBoxLayout(row_widget)
            hinge_layout.setContentsMargins(0, 0, 0, 0)

            hinge_layout.addWidget(ThemedLabel(f"H{i+1}:"))

            position_input = SimpleDollarLineEdit(f"hinge{i+1}_x_position", self)
            position_input.setValidator(QDoubleValidator(0, self.MAX_DOOR_HEIGHT, 2))
            hinge_layout.addWidget(position_input)
            self.hinge_inputs.append(position_input)

            active_check = SimpleDollarCheckBox(f"hinge{i+1}_active", "On", self)
            hinge_layout.addWidget(active_check)
            self.hinge_active_checks.append(active_check)

            self.hinge_positions_layout.addWidget(row_widget)

        # Compute which hinges are newly added vs. removed, then sync order
        if self.main_window:
            new_hinges = []
            inactive_hinges = []
            for i in range(count):
                val = self.main_window.get_dollar_variable(f"hinge{i+1}_active") or 0
                if int(val) == 0:
                    new_hinges.append(f"hinge{i+1}")
            for i in range(count, 10):
                val = self.main_window.get_dollar_variable(f"hinge{i+1}_active") or 0
                if int(val) > 0:
                    inactive_hinges.append(f"hinge{i+1}")
            # Also zero out X positions for removed hinges
            pos_changes = {f"hinge{i+1}_x_position": 0 for i in range(count, 10)}
            if pos_changes:
                self.main_window.update_dollar_variables(pos_changes)

            self._compute_order_and_write(
                force_inactive=inactive_hinges,
                force_active_add=new_hinges
            )

        self.update_enabled_states()
        self.run_auto_calculations()

    def update_enabled_states(self):
        """Update enabled/disabled states based on auto checkboxes and profile selection."""
        if not self.main_window:
            return

        dv = self.main_window.get_dollar_variable

        hinge_profile = bool(dv("selected_hinge"))
        lock_profile = bool(dv("selected_lock"))
        barrel_profile = bool(dv("selected_barrel"))

        # Lock inputs
        self.lock_x_input.setEnabled(not bool(dv("lock_x_auto")))
        self.lock_z_input.setEnabled(not bool(dv("lock_z_auto")))

        # Barrel inputs
        self.barrel_x_input.setEnabled(not bool(dv("barrel_x_auto")))
        self.barrel_y_input.setEnabled(not bool(dv("barrel_y_auto")))

        # Hinge shared Z — always enabled (no auto)
        # (hinge_z_input is never auto-disabled)

        # Individual hinge X inputs
        hinge_x_auto = bool(dv("hinge_x_auto"))
        for input_field in self.hinge_inputs:
            input_field.setEnabled(not hinge_x_auto)

        # Active checkboxes: disable (and visually uncheck) when profile not selected
        for check in self.hinge_active_checks:
            if not hinge_profile:
                check.blockSignals(True)
                check.setChecked(False)
                check.blockSignals(False)
            check.setEnabled(hinge_profile)

        if not lock_profile:
            self.lock_active_check.blockSignals(True)
            self.lock_active_check.setChecked(False)
            self.lock_active_check.blockSignals(False)
        self.lock_active_check.setEnabled(lock_profile)

        if not barrel_profile:
            self.barrel_active_check.blockSignals(True)
            self.barrel_active_check.setChecked(False)
            self.barrel_active_check.blockSignals(False)
        self.barrel_active_check.setEnabled(barrel_profile)

    def update_ui_from_main_window(self):
        """Update all UI elements from main_window values"""
        if not self.main_window:
            return

        # Update door dimension inputs
        for widget in [self.height_input, self.width_input, self.depth_input,
                       self.x_offset_input, self.y_offset_input, self.z_offset_input,
                       self.lock_x_input, self.lock_z_input,
                       self.barrel_x_input, self.barrel_y_input,
                       self.hinge_z_input]:
            widget.update_from_main_window()

        # Update checkboxes
        for widget in [self.lock_active_check, self.lock_x_auto_check, self.lock_z_auto_check,
                       self.barrel_active_check, self.barrel_x_auto_check, self.barrel_y_auto_check,
                       self.hinge_x_auto_check]:
            widget.update_from_main_window()

        # Update hinge rows
        for widget in self.hinge_inputs + self.hinge_active_checks:
            widget.update_from_main_window()

        # Update radio buttons
        self.orientation_group.update_from_main_window()

    def update_preview(self):
        """Update preview with current configuration"""
        if not self.main_window:
            return

        config = self.get_current_config()
        self.preview.update_config(config)

    def get_current_config(self):
        """Get current configuration from main_window for the preview"""
        if not self.main_window:
            return {}

        dv = self.main_window.get_dollar_variable

        hinge_x_positions = []
        hinge_active = []
        for i in range(10):
            pos = dv(f"hinge{i+1}_x_position") or 0
            active = bool(dv(f"hinge{i+1}_active"))
            hinge_x_positions.append(pos)
            hinge_active.append(active)

        return {
            'door_height': dv("door_height") or 2100,
            'door_width': dv("door_width") or 900,
            'door_depth': dv("door_depth") or 40,
            'hinge_z_position': float(dv("hinge_z_position")) if dv("hinge_z_position") not in (None, '') else 0,
            'hinge_x_positions': hinge_x_positions,
            'hinge_active': hinge_active,
            'lock_x_position': dv("lock_x_position") or 1050,
            'lock_z_position': float(dv("lock_z_position")) if dv("lock_z_position") not in (None, '') else 0,
            'lock_active': bool(dv("lock_active")),
            'barrel_x_position': dv("barrel_x_position") or 1050,
            'barrel_y_position': dv("barrel_y_position") or 20,
            'barrel_active': bool(dv("barrel_active")),
            'orientation': dv("orientation") or "right",
        }

    def enforce_height_limits(self):
        """Enforce min/max height limits"""
        if not self.main_window:
            return

        try:
            current_height = self.main_window.get_dollar_variable("door_height") or 0
            if current_height < self.MIN_DOOR_HEIGHT:
                self.main_window.update_dollar_variable("door_height", self.MIN_DOOR_HEIGHT)
            elif current_height > self.MAX_DOOR_HEIGHT:
                self.main_window.update_dollar_variable("door_height", self.MAX_DOOR_HEIGHT)
        except (ValueError, TypeError):
            self.main_window.update_dollar_variable("door_height", self.MIN_DOOR_HEIGHT)

    # MARK: - G-code Editing

    def edit_right_gcode(self):
        """Edit right door G-code"""
        from ..dialogs.gcode_dialog import ProfileGCodeDialog
        from PySide6.QtWidgets import QDialog

        current_gcode = self.main_window.get_current_gcode("right_gcode")

        dialog = ProfileGCodeDialog("Right Door G-Code", current_gcode, self)
        if dialog.exec_() == QDialog.Accepted:
            new_gcode = dialog.get_gcode()
            self.main_window.update_current_gcodes("right_gcode", new_gcode)

    def edit_left_gcode(self):
        """Edit left door G-code"""
        from ..dialogs.gcode_dialog import ProfileGCodeDialog
        from PySide6.QtWidgets import QDialog

        current_gcode = self.main_window.get_current_gcode("left_gcode")

        dialog = ProfileGCodeDialog("Left Door G-Code", current_gcode, self)
        if dialog.exec_() == QDialog.Accepted:
            new_gcode = dialog.get_gcode()
            self.main_window.update_current_gcodes("left_gcode", new_gcode)

    # MARK: - Spreadsheet Import

    _SPREADSHEET_FILTER = "Spreadsheet Files (*.xlsx *.ods *.csv *.xls *.xlsm);;All Files (*)"

    def _create_spreadsheet_section(self):
        group = ThemedGroupBox("Import from Spreadsheet")
        layout = QVBoxLayout()
        group.setLayout(layout)

        # Row 1: file label + Browse + Create on the same line
        file_row = QHBoxLayout()
        file_row.setSpacing(6)

        self._ss_file_label = ThemedLabel("None")
        self._ss_file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._ss_file_label.setStyleSheet("color: #6f779a; font-style: italic; font-family: Consolas; font-size: 10px;")
        self._ss_file_label.setMinimumWidth(0)
        file_row.addWidget(self._ss_file_label, 1)

        browse_btn = PurpleButton("Browse")
        browse_btn.setFixedWidth(72)
        browse_btn.clicked.connect(self._on_browse_spreadsheet)
        file_row.addWidget(browse_btn)

        create_btn = PurpleButton("Create")
        create_btn.setFixedWidth(72)
        create_btn.clicked.connect(self._on_create_spreadsheet)
        file_row.addWidget(create_btn)
        layout.addLayout(file_row)

        # Row 2: picked-row info chips (hidden until a row is picked)
        info_row = QHBoxLayout()
        info_row.setSpacing(6)
        info_row.setContentsMargins(0, 0, 0, 0)

        def _chip(color: str) -> ThemedLabel:
            lbl = ThemedLabel()
            lbl.setFont(QFont("Consolas", 10))
            lbl.setStyleSheet(
                f"color: {color}; background: #1d1f28; border-radius: 3px; padding: 2px 6px;"
            )
            lbl.setVisible(False)
            return lbl

        self._ss_count_lbl  = _chip("#23c87b")
        self._ss_height_lbl = _chip("#BB86FC")
        self._ss_side_lbl   = _chip("#ffffff")
        self._ss_width_lbl  = _chip("#BB86FC")
        self._ss_depth_lbl  = _chip("#8be9fd")

        for lbl in [self._ss_count_lbl, self._ss_height_lbl,
                    self._ss_side_lbl, self._ss_width_lbl, self._ss_depth_lbl]:
            info_row.addWidget(lbl)
        info_row.addStretch()
        layout.addLayout(info_row)

        # Row 3: Pick button
        self._ss_pick_btn = GreenButton("Pick Row")
        self._ss_pick_btn.setEnabled(bool(self._spreadsheet_file))
        self._ss_pick_btn.clicked.connect(self._on_pick_spreadsheet)
        layout.addWidget(self._ss_pick_btn)

        # Initialise label from loaded state
        self._update_ss_file_label()

        return group

    def _update_ss_file_label(self):
        if not hasattr(self, '_ss_file_label'):
            return
        path = self._spreadsheet_file
        if not path:
            self._ss_file_label.setText("None")
            self._ss_file_label.setToolTip("")
            self._ss_file_label.setStyleSheet(
                "color: #6f779a; font-style: italic; font-family: Consolas; font-size: 10px;"
            )
            return
        # Show .../parent_folder/filename — truncate with ellipsis at start if long
        parts = path.replace("\\", "/").split("/")
        display = "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]
        if len(display) > 42:
            display = "..." + display[-39:]
        elif path != display:
            display = "..." + display
        self._ss_file_label.setText(display)
        self._ss_file_label.setToolTip(path)
        self._ss_file_label.setStyleSheet(
            "color: #ffffff; font-style: normal; font-family: Consolas; font-size: 10px;"
        )

    def _update_ss_info_labels(self):
        info = self._ss_picked_info or {}
        if not info:
            for lbl in [self._ss_count_lbl, self._ss_height_lbl,
                        self._ss_side_lbl, self._ss_width_lbl, self._ss_depth_lbl]:
                lbl.setVisible(False)
            return

        def _show(lbl, text):
            lbl.setText(text)
            lbl.setVisible(bool(text))

        count  = info.get("count", 1)
        height = info.get("door_height", "")
        side   = info.get("side", "")
        width  = info.get("door_width", "")
        depth  = info.get("door_depth", "")

        _show(self._ss_count_lbl,  f"×{count}")
        _show(self._ss_height_lbl, f"H: {height}" if height else "")
        _show(self._ss_side_lbl,   side)
        _show(self._ss_width_lbl,  f"W: {width}" if width else "")
        _show(self._ss_depth_lbl,  f"D: {depth}" if depth else "")

    def _on_browse_spreadsheet(self):
        start_dir = os.path.dirname(self._spreadsheet_file) if self._spreadsheet_file else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Spreadsheet File", start_dir, self._SPREADSHEET_FILTER
        )
        if not path:
            return
        self._spreadsheet_file = path
        self._ss_is_temp = False
        self._update_ss_file_label()
        self._ss_pick_btn.setEnabled(True)

    # Variables that are overridden by an auto-calculation flag.
    # Key = variable name, Value = the auto flag that controls it.
    _AUTO_GUARDS = {
        "lock_x_position":   "lock_x_auto",
        "lock_z_position":   "lock_z_auto",
        "barrel_x_position": "barrel_x_auto",
        "barrel_y_position": "barrel_y_auto",
        **{f"hinge{i+1}_x_position": "hinge_x_auto" for i in range(10)},
    }

    # Default columns created by the "Create" button (display-focused, not all variables)
    _SPREADSHEET_DEFAULT_HEADERS = ["door_height", "door_width", "door_depth", "side"]

    def _on_create_spreadsheet(self):
        """Create a temp spreadsheet with default columns (no Save-As dialog).
        The file is bundled into the project folder when the project is saved."""
        from ..dialogs.spreadsheet_picker_dialog import write_spreadsheet

        profiles_dir = "profiles"
        os.makedirs(profiles_dir, exist_ok=True)

        # Remove any leftover temp files (both formats) so only one ever exists
        for _name in ("temp_spreadsheet.xlsx", "temp_spreadsheet.csv"):
            _p = os.path.join(profiles_dir, _name)
            try:
                if os.path.exists(_p):
                    os.remove(_p)
            except Exception:
                pass

        # Try xlsx first; fall back to csv if openpyxl is missing
        path = os.path.join(profiles_dir, "temp_spreadsheet.xlsx")
        try:
            write_spreadsheet(path, self._SPREADSHEET_DEFAULT_HEADERS, [])
        except ImportError:
            path = os.path.join(profiles_dir, "temp_spreadsheet.csv")
            try:
                write_spreadsheet(path, self._SPREADSHEET_DEFAULT_HEADERS, [])
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Could not create spreadsheet:\n{exc}")
                return
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not create spreadsheet:\n{exc}")
            return

        self._spreadsheet_file = path
        self._ss_is_temp = True
        self._update_ss_file_label()
        self._ss_pick_btn.setEnabled(True)

        # Open immediately in edit mode
        self._on_pick_spreadsheet(start_in_edit_mode=True)

    def _on_pick_spreadsheet(self, start_in_edit_mode: bool = False):
        if not self._spreadsheet_file:
            return
        if not self.main_window:
            return

        known_vars = self.main_window.dollar_variables

        dialog = SpreadsheetPickerDialog(
            file_path=self._spreadsheet_file,
            known_variables=known_vars,
            last_row_index=self._spreadsheet_last_row,
            parent=self,
            start_in_edit_mode=start_in_edit_mode,
        )

        if dialog.exec() != SpreadsheetPickerDialog.Accepted:
            return

        if not dialog.values_to_apply:
            QMessageBox.information(self, "No Values", "No recognised variable columns found in the selected row.")
            return

        # Coerce string values to the correct type
        coerced = {}
        for var_name, raw_val in dialog.values_to_apply.items():
            current = known_vars.get(var_name)
            coerced[var_name] = self._coerce_spreadsheet_value(raw_val, current)

        # For any auto-controlled variable we are about to import, disable the
        # corresponding auto flag in the same batch so auto-calc won't overwrite it.
        auto_flags_to_clear = set()
        for var_name in coerced:
            flag = self._AUTO_GUARDS.get(var_name)
            if flag and known_vars.get(flag):
                auto_flags_to_clear.add(flag)
        for flag in auto_flags_to_clear:
            coerced[flag] = 0

        self.main_window.update_dollar_variables(coerced)

        # Keep last-row index in memory (project-only, not persisted to disk)
        self._spreadsheet_last_row = dialog.picked_row_index

        # Update info chips in the tab
        self._ss_picked_info = getattr(dialog, 'picked_display_data', {})
        if hasattr(self, '_ss_count_lbl'):
            self._update_ss_info_labels()

    def on_project_saved(self, project_filename: str) -> str | None:
        """Copy temp spreadsheet into the project folder when the project is saved.
        Returns the final spreadsheet path (updated if moved), or None if no spreadsheet."""
        if not self._spreadsheet_file:
            return None

        if not self._ss_is_temp:
            return self._spreadsheet_file

        # Copy temp → project folder
        import shutil
        project_dir  = os.path.dirname(project_filename)
        project_stem = os.path.splitext(os.path.basename(project_filename))[0]
        ss_ext       = os.path.splitext(self._spreadsheet_file)[1]
        ss_dest      = os.path.join(project_dir, f"{project_stem}_spreadsheet{ss_ext}")
        try:
            shutil.copy2(self._spreadsheet_file, ss_dest)
            try:
                os.remove(self._spreadsheet_file)
            except Exception:
                pass
            self._spreadsheet_file = ss_dest
            self._ss_is_temp = False
            self._update_ss_file_label()
            return ss_dest
        except Exception:
            return self._spreadsheet_file

    def on_project_loaded(self, data: dict):
        """Restore spreadsheet state from a loaded project dict."""
        ss_path = data.get("spreadsheet_file")
        if ss_path and os.path.isfile(ss_path):
            self._spreadsheet_file    = ss_path
            self._spreadsheet_last_row = data.get("spreadsheet_last_row")
            self._ss_is_temp          = False
        else:
            self._spreadsheet_file    = None
            self._spreadsheet_last_row = None
            self._ss_is_temp          = False

        self._ss_picked_info = None
        self._update_ss_file_label()
        if hasattr(self, '_ss_pick_btn'):
            self._ss_pick_btn.setEnabled(bool(self._spreadsheet_file))
        if hasattr(self, '_ss_count_lbl'):
            self._update_ss_info_labels()

    @staticmethod
    def _coerce_spreadsheet_value(raw: str, current):
        """Convert a string cell value to match the type of the existing variable."""
        if isinstance(current, bool):
            return raw.strip().lower() in ("1", "true", "yes")
        if isinstance(current, int):
            try:
                return int(float(raw.strip()))
            except ValueError:
                return current
        if isinstance(current, float):
            try:
                return float(raw.strip())
            except ValueError:
                return current
        return raw  # str


# MARK: - Simplified Dollar Variable Widgets

class SimpleDollarLineEdit(ThemedLineEdit):
    """Simplified line edit that sends changes to frame_tab without auto-syncing"""

    def __init__(self, variable_name, frame_tab, parent=None):
        super().__init__(parent=parent)
        self.variable_name = variable_name
        self.frame_tab = frame_tab
        self._updating = False
        self._has_error = False

        self.update_from_main_window()
        self.editingFinished.connect(self._on_editing_finished)

    def focusInEvent(self, event):
        """When focused, ask frame_tab to update the parameter preview for this variable."""
        super().focusInEvent(event)
        if hasattr(self.frame_tab, 'on_parameter_field_focused'):
            self.frame_tab.on_parameter_field_focused(self.variable_name)

    def _format_value(self, value):
        """Format value for display"""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def _on_editing_finished(self):
        """Send change to frame_tab"""
        if self._updating or not self.frame_tab.main_window:
            return

        text = self.text().strip()

        try:
            if not text:
                new_value = 0
            elif '.' in text:
                new_value = float(text)
                if new_value.is_integer():
                    new_value = int(new_value)
            else:
                new_value = int(text)
        except ValueError:
            self.update_from_main_window()
            return

        self.frame_tab.on_variable_changed(self.variable_name, new_value)

    def update_from_main_window(self):
        """Update value from main_window"""
        if not self.frame_tab.main_window:
            return

        self._updating = True
        try:
            value = self.frame_tab.main_window.get_dollar_variable(self.variable_name)
            if value is not None:
                self.setText(self._format_value(value))
        finally:
            self._updating = False

    def set_error(self, has_error):
        """Set error state and update styling"""
        self._has_error = has_error
        if has_error:
            self.setStyleSheet("""
                QLineEdit {
                    background-color: #1d1f28;
                    color: #ffffff;
                    border: 2px solid #ff4444;
                    border-radius: 4px;
                    padding: 4px;
                }
                QLineEdit:focus {
                    border: 2px solid #ff4444;
                }
            """)
        else:
            self.setStyleSheet("""
                QLineEdit {
                    background-color: #1d1f28;
                    color: #ffffff;
                    border: 1px solid #6f779a;
                    border-radius: 4px;
                    padding: 4px;
                }
                QLineEdit:focus {
                    border: 1px solid #BB86FC;
                }
                QLineEdit:disabled {
                    background-color: #0d0f18;
                    color: #6f779a;
                }
            """)

    def has_error(self):
        return self._has_error


class SimpleDollarCheckBox(ThemedCheckBox):
    """Simplified checkbox that sends changes to frame_tab"""

    def __init__(self, variable_name, text, frame_tab, parent=None):
        super().__init__(text, parent=parent)
        self.variable_name = variable_name
        self.frame_tab = frame_tab
        self._updating = False

        self.update_from_main_window()
        self.stateChanged.connect(self._on_state_changed)

    def _on_state_changed(self):
        """Send change to frame_tab"""
        if self._updating:
            return

        new_value = 1 if self.isChecked() else 0
        self.frame_tab.on_variable_changed(self.variable_name, new_value)

    def update_from_main_window(self):
        """Update value from main_window"""
        if not self.frame_tab.main_window:
            return

        self._updating = True
        try:
            value = self.frame_tab.main_window.get_dollar_variable(self.variable_name)
            if value is not None:
                self.setChecked(bool(value))
        finally:
            self._updating = False


class SimpleDollarRadioGroup:
    """Simplified radio group that sends changes to frame_tab"""

    def __init__(self, variable_name, frame_tab):
        self.variable_name = variable_name
        self.frame_tab = frame_tab
        self.button_group = QButtonGroup()
        self.value_map = {}
        self._updating = False

        self.button_group.buttonClicked.connect(self._on_button_clicked)

    def add_button(self, button, value):
        """Add button with value"""
        self.button_group.addButton(button)
        self.value_map[button] = value
        self.update_from_main_window()

    def _on_button_clicked(self, button):
        """Send change to frame_tab"""
        if self._updating:
            return

        value = self.value_map.get(button)
        if value is not None:
            self.frame_tab.on_variable_changed(self.variable_name, value)

    def update_from_main_window(self):
        """Update selection from main_window"""
        if not self.frame_tab.main_window:
            return

        self._updating = True
        try:
            current_value = self.frame_tab.main_window.get_dollar_variable(self.variable_name)
            for button, value in self.value_map.items():
                if value == current_value:
                    button.setChecked(True)
                    break
        finally:
            self._updating = False

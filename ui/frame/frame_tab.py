"""
Frame Tab (Door Setup)

Door milling configuration: hinges (up to 10), lock, and barrel.
No PM group. Clean architecture with predictable update flow.
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
                               QButtonGroup, QSizePolicy, QScrollArea)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDoubleValidator, QPixmap
import os

from ..widgets.themed_widgets import (ThemedSplitter, ThemedLabel, ThemedRadioButton,
                                    ThemedGroupBox, PurpleButton, GreenButton,
                                    ThemedCheckBox, ThemedSpinBox, ThemedLineEdit)
from ..widgets.simple_widgets import ClickableLabel, ErrorLineEdit, ScaledPreviewLabel
from .widgets.frame_preview import FramePreview
from .widgets.order_widget import OrderWidget


class FrameTab(QWidget):
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

        return widget

    def create_right_panel(self):
        """Create right panel with lock, barrel, and hinge configuration"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # --- Lock Configuration ---
        lock_group = ThemedGroupBox("Lock Configuration")
        lock_layout = QVBoxLayout()
        lock_group.setLayout(lock_layout)

        # Active checkbox
        self.lock_active_check = SimpleDollarCheckBox("lock_active", "Active", self)
        lock_layout.addWidget(self.lock_active_check)

        # X position row
        lock_x_layout = QHBoxLayout()
        self.lock_x_auto_check = SimpleDollarCheckBox("lock_x_auto", "Auto", self)
        lock_x_layout.addWidget(self.lock_x_auto_check)
        lock_x_layout.addWidget(ThemedLabel("X:"))
        self.lock_x_input = SimpleDollarLineEdit("lock_x_position", self)
        self.lock_x_input.setValidator(QDoubleValidator(0, self.MAX_DOOR_HEIGHT, 2))
        lock_x_layout.addWidget(self.lock_x_input)
        lock_layout.addLayout(lock_x_layout)

        # Z position row
        lock_z_layout = QHBoxLayout()
        self.lock_z_auto_check = SimpleDollarCheckBox("lock_z_auto", "Auto", self)
        lock_z_layout.addWidget(self.lock_z_auto_check)
        lock_z_layout.addWidget(ThemedLabel("Z:"))
        self.lock_z_input = SimpleDollarLineEdit("lock_z_position", self)
        self.lock_z_input.setValidator(QDoubleValidator(0, 500, 2))
        lock_z_layout.addWidget(self.lock_z_input)
        lock_layout.addLayout(lock_z_layout)

        layout.addWidget(lock_group)

        # --- Barrel Configuration ---
        barrel_group = ThemedGroupBox("Barrel Configuration")
        barrel_layout = QVBoxLayout()
        barrel_group.setLayout(barrel_layout)

        self.barrel_active_check = SimpleDollarCheckBox("barrel_active", "Active", self)
        barrel_layout.addWidget(self.barrel_active_check)

        # X position row
        barrel_x_layout = QHBoxLayout()
        self.barrel_x_auto_check = SimpleDollarCheckBox("barrel_x_auto", "Auto", self)
        barrel_x_layout.addWidget(self.barrel_x_auto_check)
        barrel_x_layout.addWidget(ThemedLabel("X:"))
        self.barrel_x_input = SimpleDollarLineEdit("barrel_x_position", self)
        self.barrel_x_input.setValidator(QDoubleValidator(0, self.MAX_DOOR_HEIGHT, 2))
        barrel_x_layout.addWidget(self.barrel_x_input)
        barrel_layout.addLayout(barrel_x_layout)

        # Y position row
        barrel_y_layout = QHBoxLayout()
        self.barrel_y_auto_check = SimpleDollarCheckBox("barrel_y_auto", "Auto", self)
        barrel_y_layout.addWidget(self.barrel_y_auto_check)
        barrel_y_layout.addWidget(ThemedLabel("Y:"))
        self.barrel_y_input = SimpleDollarLineEdit("barrel_y_position", self)
        self.barrel_y_input.setValidator(QDoubleValidator(0, 500, 2))
        barrel_y_layout.addWidget(self.barrel_y_input)
        barrel_layout.addLayout(barrel_y_layout)

        layout.addWidget(barrel_group)

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

        # Shared Z position
        hinge_z_layout = QHBoxLayout()
        self.hinge_z_auto_check = SimpleDollarCheckBox("hinge_z_auto", "Auto", self)
        hinge_z_layout.addWidget(self.hinge_z_auto_check)
        hinge_z_layout.addWidget(ThemedLabel("Z (all):"))
        self.hinge_z_input = SimpleDollarLineEdit("hinge_z_position", self)
        self.hinge_z_input.setValidator(QDoubleValidator(0, 500, 2))
        hinge_z_layout.addWidget(self.hinge_z_input)
        hinge_layout.addLayout(hinge_z_layout)

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
        self.hinge_x_auto_checks = []
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
        self.hinge_x_auto_checks = []
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

            # X auto checkbox
            x_auto_check = SimpleDollarCheckBox(f"hinge{i+1}_x_auto", "Auto", self)
            hinge_layout.addWidget(x_auto_check)
            self.hinge_x_auto_checks.append(x_auto_check)

            # Active checkbox
            active_check = SimpleDollarCheckBox(f"hinge{i+1}_active", "On", self)
            hinge_layout.addWidget(active_check)
            self.hinge_active_checks.append(active_check)

            self.hinge_positions_layout.addWidget(row_widget)

        # Sync values from main_window
        for w in self.hinge_inputs:
            w.update_from_main_window()
        for w in self.hinge_x_auto_checks:
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

            # 1. Hinge shared Z position
            if bool(dv("hinge_z_auto")):
                changes["hinge_z_position"] = round(door_depth / 2, 1)

            # 2. Individual hinge X positions
            if count > 0:
                auto_positions = self._calculate_hinge_x_positions(count, door_height)
                for i in range(count):
                    if bool(dv(f"hinge{i+1}_x_auto")):
                        if i < len(auto_positions):
                            changes[f"hinge{i+1}_x_position"] = round(auto_positions[i], 1)

            # 3. Lock X position
            if bool(dv("lock_x_auto")):
                changes["lock_x_position"] = round(door_height / 2, 1)

            # 4. Lock Z position
            if bool(dv("lock_z_auto")):
                changes["lock_z_position"] = round(door_depth / 2, 1)

            # 5. Barrel X position (follows lock X by default)
            if bool(dv("barrel_x_auto")):
                lock_x = changes.get("lock_x_position", dv("lock_x_position") or door_height / 2)
                changes["barrel_x_position"] = round(lock_x, 1)

            # 6. Barrel Y position
            if bool(dv("barrel_y_auto")):
                changes["barrel_y_position"] = round(door_depth / 2, 1)

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
        all_components = ["lock"] + [f"hinge{i+1}" for i in range(10)]

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
            for w in [self.lock_active_check] + self.hinge_active_checks:
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

        self._updating_order = True
        try:
            self.main_window.update_dollar_variables(changes)
            for w in [self.lock_active_check] + self.hinge_active_checks:
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

    def on_variable_changed(self, var_name, value):
        """Handle variable changes from simple dollar widgets"""
        if self.main_window and not self._auto_calculation_running:
            # Active vars (except barrel) feed into the milling order system
            if var_name.endswith("_active") and var_name != "barrel_active":
                comp = var_name.replace("_active", "")
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
        self.hinge_x_auto_checks = []
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

            x_auto_check = SimpleDollarCheckBox(f"hinge{i+1}_x_auto", "Auto", self)
            hinge_layout.addWidget(x_auto_check)
            self.hinge_x_auto_checks.append(x_auto_check)

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
        """Update enabled/disabled states based on auto checkboxes"""
        if not self.main_window:
            return

        dv = self.main_window.get_dollar_variable

        # Lock inputs
        self.lock_x_input.setEnabled(not bool(dv("lock_x_auto")))
        self.lock_z_input.setEnabled(not bool(dv("lock_z_auto")))

        # Barrel inputs
        self.barrel_x_input.setEnabled(not bool(dv("barrel_x_auto")))
        self.barrel_y_input.setEnabled(not bool(dv("barrel_y_auto")))

        # Hinge shared Z
        self.hinge_z_input.setEnabled(not bool(dv("hinge_z_auto")))

        # Individual hinge X inputs
        for i, input_field in enumerate(self.hinge_inputs):
            x_auto = bool(dv(f"hinge{i+1}_x_auto"))
            input_field.setEnabled(not x_auto)

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
                       self.hinge_z_auto_check]:
            widget.update_from_main_window()

        # Update hinge rows
        for widget in self.hinge_inputs + self.hinge_x_auto_checks + self.hinge_active_checks:
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
            'hinge_z_position': dv("hinge_z_position") or 20,
            'hinge_x_positions': hinge_x_positions,
            'hinge_active': hinge_active,
            'lock_x_position': dv("lock_x_position") or 1050,
            'lock_z_position': dv("lock_z_position") or 20,
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

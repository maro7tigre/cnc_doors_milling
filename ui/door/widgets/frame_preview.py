"""
Frame Preview Widget (Door View)

3-panel visual preview: [hinge-side depth] | [door face] | [lock-side depth]
All panels share the same height, separated by a small gap.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont


class FramePreview(QWidget):
    """Visual preview of a door with hinge, lock, and barrel positions - 3-view layout"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Default configuration values
        self.door_height = 2100
        self.door_width = 900
        self.door_depth = 40
        self.hinge_z_position = 20
        self.hinge_x_positions = []
        self.hinge_active = []
        self.lock_x_position = 1050
        self.lock_z_position = 20
        self.lock_active = True
        self.barrel_x_position = 1050
        self.barrel_y_position = 20
        self.barrel_active = True
        self.orientation = "right"    # "right" or "left"

        self.setMinimumSize(200, 400)
        self.setStyleSheet("background-color: #1d1f28;")

    def update_config(self, config):
        """Update preview with new configuration"""
        self.door_height = config.get('door_height', 2100)
        self.door_width = config.get('door_width', 900)
        self.door_depth = config.get('door_depth', 40)
        self.hinge_z_position = config.get('hinge_z_position', 20)
        self.hinge_x_positions = config.get('hinge_x_positions', [])
        self.hinge_active = config.get('hinge_active', [])
        self.lock_x_position = config.get('lock_x_position', 1050)
        self.lock_z_position = config.get('lock_z_position', 20)
        self.lock_active = config.get('lock_active', True)
        self.barrel_x_position = config.get('barrel_x_position', 1050)
        self.barrel_y_position = config.get('barrel_y_position', 20)
        self.barrel_active = config.get('barrel_active', True)
        self.orientation = config.get('orientation', 'right')
        self.update()

    def paintEvent(self, event):
        """Draw the 3-panel door preview"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        widget_w = self.width()
        widget_h = self.height()
        margin = 20
        gap = 12   # gap between the three panels

        if self.door_height <= 0 or self.door_width <= 0 or self.door_depth <= 0:
            return

        avail_w = widget_w - 2 * margin
        avail_h = widget_h - 2 * margin

        # Compute a unified scale so all three views share the same height:
        #   total_mm_width = depth + face_width + depth
        #   scale * total_mm_width + 2*gap = avail_w
        #   scale * door_height = avail_h
        total_mm_w = self.door_depth + self.door_width + self.door_depth
        scale_w = (avail_w - 2 * gap) / total_mm_w
        scale_h = avail_h / self.door_height
        scale = min(scale_w, scale_h)

        door_h_px = self.door_height * scale
        face_w_px = self.door_width * scale
        depth_px = self.door_depth * scale

        # Center the whole composition
        total_w = depth_px + gap + face_w_px + gap + depth_px
        start_x = margin + (avail_w - total_w) / 2
        start_y = margin + (avail_h - door_h_px) / 2

        # Panel X positions
        left_x = start_x
        face_x = start_x + depth_px + gap
        right_x = face_x + face_w_px + gap

        # Determine which depth view is hinge side and which is lock side
        # "right" orientation: hinge is on the right edge of the door face
        #   → right depth strip = hinge side, left depth strip = lock side
        # "left" orientation: hinge is on the left edge of the door face
        #   → left depth strip = hinge side, right depth strip = lock side
        if self.orientation == "right":
            hinge_depth_x = right_x
            lock_depth_x = left_x
        else:
            hinge_depth_x = left_x
            lock_depth_x = right_x

        # ── Draw the three panels ──────────────────────────────────────────

        # 1. Hinge-side depth strip
        self._draw_depth_strip_hinge(
            painter, hinge_depth_x, start_y, depth_px, door_h_px, scale
        )

        # 2. Door face (center)
        self._draw_face(
            painter, face_x, start_y, face_w_px, door_h_px, depth_px, scale
        )

        # 3. Lock-side depth strip
        self._draw_depth_strip_lock(
            painter, lock_depth_x, start_y, depth_px, door_h_px, scale
        )


    # ── Panel drawing helpers ─────────────────────────────────────────────

    def _draw_depth_strip_hinge(self, painter, x, y, w, h, scale):
        """Draw the hinge-side depth strip (depth × height)"""
        # Door body
        painter.setBrush(QBrush(QColor(139, 90, 43)))
        painter.setPen(QPen(QColor(80, 50, 20), 1))
        painter.drawRect(int(x), int(y), int(w), int(h))

        # Draw hinges as rectangles at their X (height) position, centered on depth
        painter.setBrush(QBrush(QColor(70, 130, 220)))
        painter.setPen(QPen(QColor(30, 80, 160), 1))

        hinge_h_px = max(6, scale * 60)
        hinge_w_px = max(5, w * 0.6)
        z_clamped = max(0, min(self.hinge_z_position, self.door_depth))
        hinge_x_center = x + z_clamped * scale

        for i, (x_pos, active) in enumerate(zip(self.hinge_x_positions, self.hinge_active)):
            if not active or x_pos <= 0:
                continue

            hy = y + x_pos * scale
            painter.drawRect(
                int(hinge_x_center - hinge_w_px / 2),
                int(hy - hinge_h_px / 2),
                int(hinge_w_px),
                int(hinge_h_px)
            )

            # Label
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", max(5, int(hinge_h_px * 0.3))))
            painter.drawText(int(hinge_x_center - hinge_w_px / 2 + 1),
                             int(hy + hinge_h_px * 0.15), f"H{i+1}")
            painter.setPen(QPen(QColor(30, 80, 160), 1))

    def _draw_depth_strip_lock(self, painter, x, y, w, h, scale):
        """Draw the lock-side depth strip (depth × height) — lock only."""
        # Door body
        painter.setBrush(QBrush(QColor(139, 90, 43)))
        painter.setPen(QPen(QColor(80, 50, 20), 1))
        painter.drawRect(int(x), int(y), int(w), int(h))

        # Draw lock
        if self.lock_active and 0 < self.lock_x_position <= self.door_height:
            painter.setBrush(QBrush(QColor(50, 200, 80)))
            painter.setPen(QPen(QColor(20, 120, 40), 1))

            lock_h_px = max(8, scale * 120)
            lock_w_px = max(5, w * 0.6)
            ly = y + (self.door_height - self.lock_x_position) * scale
            z_clamped = max(0, min(self.lock_z_position, self.door_depth))
            center_x = x + z_clamped * scale

            painter.drawRect(
                int(center_x - lock_w_px / 2),
                int(ly - lock_h_px / 2),
                int(lock_w_px),
                int(lock_h_px)
            )
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", max(5, int(lock_h_px * 0.2))))
            painter.drawText(int(center_x - lock_w_px / 2 + 1),
                             int(ly + lock_h_px * 0.15), "L")
            painter.setPen(QPen(QColor(20, 120, 40), 1))

    def _draw_face(self, painter, x, y, w, h, depth_px, scale):
        """Draw the door front face — barrel only (hinges/lock are on the side strips)."""
        # Door body
        painter.setBrush(QBrush(QColor(139, 90, 43)))
        painter.setPen(QPen(QColor(80, 50, 20), 2))
        painter.drawRect(int(x), int(y), int(w), int(h))

        # Barrel — shown on the front face as a circle
        if self.barrel_active and 0 < self.barrel_x_position < self.door_height:
            painter.setBrush(QBrush(QColor(220, 160, 40)))
            painter.setPen(QPen(QColor(140, 100, 20), 1))

            by = y + (self.door_height - self.barrel_x_position) * scale
            barrel_r = max(5, scale * 18)
            # barrel_y_position = distance from the lock edge across the door width
            if self.orientation == "right":
                bx = x + self.barrel_y_position * scale          # from left (lock side)
            else:
                bx = x + w - self.barrel_y_position * scale      # from right (lock side)

            painter.drawEllipse(
                int(bx - barrel_r),
                int(by - barrel_r),
                int(barrel_r * 2),
                int(barrel_r * 2)
            )

            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", max(6, int(barrel_r * 0.7))))
            painter.drawText(int(bx - barrel_r + 2), int(by + barrel_r * 0.35), "B")

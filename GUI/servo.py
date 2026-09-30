from math import atan2, cos, degrees, hypot, radians, sin

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDial,
    QBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .animated_button import AnimatedButton


class ServoRadar(QWidget):
    range_changed = Signal(int, int)
    angle_changed = Signal(int)
    angle_requested = Signal(int)

    def __init__(self, motor, parent=None):
        super().__init__(parent)
        self.motor = motor
        self.minimum_angle = 20
        self.maximum_angle = 160
        self.servo_angle = 90
        self.sweeping = False
        self.dragging_handle = None
        self.dragging_servo = False
        self.setMinimumHeight(250)
        self.setMinimumWidth(300)
        self.setMouseTracking(True)

    def set_range(self, minimum, maximum):
        self.minimum_angle = minimum
        self.maximum_angle = maximum
        self.update()

    def set_servo_angle(self, angle):
        self.servo_angle = angle
        self.update()

    def set_sweeping(self, sweeping):
        self.sweeping = sweeping
        self.update()

    def _geometry(self):
        bounds = self.rect().adjusted(18, 10, -18, -20)
        center = QPointF(bounds.center().x(), bounds.bottom())
        radius = min(bounds.width() / 2, bounds.height())
        return center, radius

    @staticmethod
    def _point_for_angle(center, radius, angle):
        angle_radians = radians(angle)
        return QPointF(
            center.x() + radius * cos(angle_radians),
            center.y() - radius * sin(angle_radians),
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center, radius = self._geometry()

        painter.setPen(QPen(QColor("#d7dee3"), 1))
        for fraction in (0.35, 0.68, 1.0):
            painter.drawArc(
                int(center.x() - radius * fraction),
                int(center.y() - radius * fraction),
                int(radius * fraction * 2),
                int(radius * fraction * 2),
                0,
                180 * 16,
            )
        painter.drawLine(QPointF(center.x() - radius, center.y()), center)
        painter.drawLine(QPointF(center.x() + radius, center.y()), center)

        painter.setPen(
            QPen(
                QColor("#75a98a"),
                11,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        painter.drawArc(
            int(center.x() - radius),
            int(center.y() - radius),
            int(radius * 2),
            int(radius * 2),
            self.minimum_angle * 16,
            (self.maximum_angle - self.minimum_angle) * 16,
        )

        color = "#176b43" if self.motor == 1 else "#df8b32"
        point = self._point_for_angle(center, radius * 0.82, self.servo_angle)
        painter.setPen(QPen(QColor(color), 2))
        painter.drawLine(center, point)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(point, 5, 5)

        painter.setBrush(QColor("#176b43"))
        painter.setPen(QPen(QColor("white"), 2))
        for angle in (self.minimum_angle, self.maximum_angle):
            painter.drawEllipse(self._point_for_angle(center, radius, angle), 8, 8)

        painter.setPen(QColor("#59656d"))
        painter.drawText(
            int(center.x() - 38),
            int(center.y() - radius - 12),
            f"{self.minimum_angle}°  to  {self.maximum_angle}°",
        )

    def _angle_at(self, point):
        center, _ = self._geometry()
        angle = round(
            degrees(atan2(center.y() - point.y(), point.x() - center.x()))
        )
        if angle < 0:
            return 180 if point.x() < center.x() else 0
        return max(0, min(180, angle))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        center, radius = self._geometry()
        minimum_point = self._point_for_angle(center, radius, self.minimum_angle)
        maximum_point = self._point_for_angle(center, radius, self.maximum_angle)
        servo_point = self._point_for_angle(center, radius * 0.82, self.servo_angle)
        distances = (
            hypot(event.position().x() - minimum_point.x(), event.position().y() - minimum_point.y()),
            hypot(event.position().x() - maximum_point.x(), event.position().y() - maximum_point.y()),
        )
        nearest_handle = 0 if distances[0] <= distances[1] else 1
        if distances[nearest_handle] <= 14:
            self.dragging_handle = nearest_handle
            self._update_drag(event.position())
        else:
            self.dragging_servo = True
            self._update_servo_drag(event.position())

    def mouseMoveEvent(self, event):
        if self.dragging_handle is not None:
            self._update_drag(event.position())
        elif self.dragging_servo:
            self._update_servo_drag(event.position())

    def mouseReleaseEvent(self, event):
        if self.dragging_servo:
            self.angle_requested.emit(self.servo_angle)
        self.dragging_servo = False
        self.dragging_handle = None

    def _update_servo_drag(self, point):
        self.servo_angle = self._angle_at(point)
        self.angle_changed.emit(self.servo_angle)
        self.update()

    def _update_drag(self, point):
        angle = self._angle_at(point)
        if self.dragging_handle == 0:
            self.minimum_angle = min(angle, self.maximum_angle - 5)
        else:
            self.maximum_angle = max(angle, self.minimum_angle + 5)
        self.range_changed.emit(self.minimum_angle, self.maximum_angle)
        self.update()


class ServoPage(QWidget):
    angle_requested = Signal(int, int)
    sweep_config_requested = Signal(int, int, int, int)
    sweep_requested = Signal(int, bool)

    def __init__(self):
        super().__init__()
        self.setObjectName("servo_page")
        self.minimum_angles = {1: 20, 2: 20}
        self.maximum_angles = {1: 160, 2: 160}
        self.sweep_speeds = {1: 45, 2: 45}
        self.setup_ui()

    def resizeEvent(self, event):
        self.motor_layout.setDirection(
            QBoxLayout.Direction.TopToBottom
            if self.width() < 900
            else QBoxLayout.Direction.LeftToRight
        )
        super().resizeEvent(event)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 22)
        layout.setSpacing(12)

        title = QLabel("Servo Control")
        title.setObjectName("page_title")
        subtitle = QLabel("Set each motor angle and sweep range independently")
        subtitle.setObjectName("settings_description")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.motor_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.motor_layout.setSpacing(12)
        self.motor_angle_labels = {}
        self.motor_dials = {}
        self.radars = {}
        self.minimum_inputs = {}
        self.maximum_inputs = {}
        self.speed_values = {}
        self.speed_dials = {}
        self.start_sweep_buttons = {}
        self.stop_sweep_buttons = {}
        for motor in (1, 2):
            panel = QWidget()
            panel.setObjectName("servo_motor_panel")
            panel_layout = QVBoxLayout(panel)
            panel_layout.setContentsMargins(14, 12, 14, 12)
            panel_layout.setSpacing(6)

            heading = QHBoxLayout()
            name = QLabel(f"SERVO {motor}")
            name.setProperty("class", "section_title")
            heading.addWidget(name)
            heading.addStretch()
            panel_layout.addLayout(heading)

            controls = QHBoxLayout()
            angle = QLabel(
                f"{self.maximum_angles[motor] - self.minimum_angles[motor]}°"
            )
            angle.setObjectName("servo_angle_value")
            angle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.motor_angle_labels[motor] = angle
            angle_column = QVBoxLayout()
            angle_column.addWidget(angle)
            caption = QLabel("Total sweep angle")
            caption.setObjectName("settings_description")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            angle_column.addWidget(caption)

            dial = QDial()
            dial.setRange(0, 180)
            dial.setValue(90)
            dial.setNotchesVisible(True)
            dial.setWrapping(False)
            dial.setFixedSize(130, 130)
            dial.setToolTip(f"Set Servo {motor} angle from 0 to 180 degrees")
            dial.sliderReleased.connect(
                lambda motor=motor, dial=dial: self.angle_requested.emit(
                    motor, min(180, max(0, dial.value()))
                )
            )
            self.motor_dials[motor] = dial
            controls.addLayout(angle_column)
            controls.addWidget(dial)

            radar = ServoRadar(motor)
            radar.setMinimumHeight(160)
            radar.setMinimumWidth(240)
            radar.range_changed.connect(
                lambda minimum, maximum, motor=motor: self.set_range_from_radar(
                    motor, minimum, maximum
                )
            )
            radar.angle_changed.connect(
                lambda value, motor=motor: self.set_angle_display(motor, value)
            )
            radar.angle_requested.connect(
                lambda value, motor=motor: self.angle_requested.emit(motor, value)
            )
            self.radars[motor] = radar
            controls.addWidget(radar, 1)
            panel_layout.addLayout(controls)

            range_row = QHBoxLayout()
            range_row.addWidget(QLabel("Sweep from"))
            minimum_input = QSpinBox()
            minimum_input.setRange(0, 175)
            minimum_input.setValue(self.minimum_angles[motor])
            minimum_input.setSuffix("°")
            minimum_input.setToolTip(f"Servo {motor} minimum sweep angle")
            range_row.addWidget(minimum_input)
            range_row.addWidget(QLabel("to"))
            maximum_input = QSpinBox()
            maximum_input.setRange(5, 180)
            maximum_input.setValue(self.maximum_angles[motor])
            maximum_input.setSuffix("°")
            maximum_input.setToolTip(f"Servo {motor} maximum sweep angle")
            range_row.addWidget(maximum_input)
            panel_layout.addLayout(range_row)
            self.minimum_inputs[motor] = minimum_input
            self.maximum_inputs[motor] = maximum_input
            minimum_input.valueChanged.connect(
                lambda _value, motor=motor: self.set_motor_range(motor, "minimum")
            )
            maximum_input.valueChanged.connect(
                lambda _value, motor=motor: self.set_motor_range(motor, "maximum")
            )

            sweep_controls = QHBoxLayout()
            speed_dial = QDial()
            speed_dial.setRange(1, 180)
            speed_dial.setValue(self.sweep_speeds[motor])
            speed_dial.setNotchesVisible(True)
            speed_dial.setFixedSize(68, 68)
            speed_dial.setToolTip(f"Servo {motor} sweep speed in degrees per second")
            self.speed_dials[motor] = speed_dial
            speed_dial.valueChanged.connect(
                lambda speed, motor=motor: self.set_sweep_speed(motor, speed)
            )
            speed_controls = QVBoxLayout()
            speed_title = QLabel("Sweep speed")
            speed_title.setObjectName("settings_description")
            speed_value = QLabel(f"{self.sweep_speeds[motor]}°/s")
            speed_value.setStyleSheet("font-weight: bold;")
            self.speed_values[motor] = speed_value
            speed_controls.addWidget(speed_title)
            speed_controls.addWidget(speed_value)
            sweep_controls.addWidget(speed_dial)
            sweep_controls.addLayout(speed_controls)
            sweep_controls.addStretch()

            start_button = AnimatedButton("START SWEEP")
            start_button.setObjectName("settings_save_button")
            stop_button = AnimatedButton("STOP SWEEP")
            stop_button.setObjectName("settings_reset_button")
            stop_button.setEnabled(False)
            start_button.clicked.connect(
                lambda _checked=False, motor=motor: self.sweep_requested.emit(motor, True)
            )
            stop_button.clicked.connect(
                lambda _checked=False, motor=motor: self.sweep_requested.emit(motor, False)
            )
            self.start_sweep_buttons[motor] = start_button
            self.stop_sweep_buttons[motor] = stop_button
            sweep_controls.addWidget(start_button)
            sweep_controls.addWidget(stop_button)
            panel_layout.addLayout(sweep_controls)
            self.motor_layout.addWidget(panel, 1)
        layout.addLayout(self.motor_layout)

        layout.addStretch()

    def _set_range(self, motor, minimum, maximum):
        self.minimum_angles[motor] = minimum
        self.maximum_angles[motor] = maximum
        self.motor_angle_labels[motor].setText(f"{maximum - minimum}°")
        minimum_input = self.minimum_inputs[motor]
        maximum_input = self.maximum_inputs[motor]
        minimum_input.blockSignals(True)
        maximum_input.blockSignals(True)
        minimum_input.setValue(minimum)
        maximum_input.setValue(maximum)
        minimum_input.blockSignals(False)
        maximum_input.blockSignals(False)
        self.radars[motor].set_range(minimum, maximum)
        self.sweep_config_requested.emit(
            motor, minimum, maximum, self.sweep_speeds[motor]
        )

    def set_range_from_radar(self, motor, minimum, maximum):
        self._set_range(motor, minimum, maximum)

    def set_motor_range(self, motor, changed_bound):
        minimum = self.minimum_inputs[motor].value()
        maximum = self.maximum_inputs[motor].value()
        if maximum - minimum < 5:
            if changed_bound == "minimum":
                maximum = min(180, minimum + 5)
            else:
                minimum = max(0, maximum - 5)
        self._set_range(motor, minimum, maximum)

    def set_sweep_speed(self, motor, speed):
        self.sweep_speeds[motor] = speed
        self.speed_values[motor].setText(f"{speed}°/s")
        self.sweep_config_requested.emit(
            motor,
            self.minimum_angles[motor],
            self.maximum_angles[motor],
            speed,
        )

    def set_motor_status(self, motor, angle):
        clamped_angle = max(0, min(180, int(angle)))
        if motor not in self.motor_dials or not 0 <= clamped_angle <= 180:
            return
        dial = self.motor_dials[motor]
        dial.blockSignals(True)
        dial.setValue(clamped_angle)
        dial.blockSignals(False)
        self.radars[motor].set_servo_angle(clamped_angle)

    def set_angle_display(self, motor, angle):
        clamped_angle = max(0, min(180, int(angle)))
        dial = self.motor_dials[motor]
        dial.blockSignals(True)
        dial.setValue(clamped_angle)
        dial.blockSignals(False)
        self.radars[motor].set_servo_angle(clamped_angle)

    def set_sweep_status(self, motor, sweeping):
        self.start_sweep_buttons[motor].setEnabled(not sweeping)
        self.stop_sweep_buttons[motor].setEnabled(sweeping)
        self.radars[motor].set_sweeping(sweeping)
        self.start_sweep_buttons[motor].setStyleSheet(
            "" if not sweeping else "background-color: #2e7d4f; color: white;"
        )
        self.stop_sweep_buttons[motor].setStyleSheet(
            "" if sweeping else "background-color: #b00020; color: white;"
        )

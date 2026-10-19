# dashboard.py

import cv2

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # The GUI can still run without serial support installed.
    serial = None
    list_ports = None

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QSizePolicy,
    QGridLayout,
    QBoxLayout,
    QComboBox,
    QHeaderView,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtMultimedia import QMediaDevices
from .animated_button import AnimatedButton


class Dashboard(QWidget):

    camera_status_changed = Signal(str)
    system_log_received = Signal(str)
    nir_message_received = Signal(str)
    servo_status_received = Signal(int, int)
    servo_sweep_status_received = Signal(int, bool)
    EMEET_CAMERA_INDEX = 0

    def __init__(self):
        super().__init__()

        self.setObjectName("dashboard")

        self.camera_source = self.EMEET_CAMERA_INDEX
        self.arduino_baud_rate = 115200
        self.nir_scan_delay_ms = 0
        self.camera_capture = None
        self.camera_enabled = False
        self.camera_toggle_button = None
        self.last_frame = None
        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self.update_camera_feed)
        self.arduino_timer = QTimer(self)
        self.arduino_timer.timeout.connect(self.update_arduino_status)
        self.media_devices = QMediaDevices(self)
        self.media_devices.videoInputsChanged.connect(
            self.update_camera_status_indicator
        )
        self.arduino_serial = None
        self.arduino_port = None
        self.serial_buffer = ""
        self.nir_detected = False
        self.nir_scanning = False
        self.servo_minimum_angles = {1: 20, 2: 20}
        self.servo_maximum_angles = {1: 160, 2: 160}
        self.servo_sweep_speeds = {1: 45, 2: 45}
        self.servo_sweeping = {1: False, 2: False}

        self.camera_modes = {
            "Camera": {
                "candidates": [self.EMEET_CAMERA_INDEX],
                "empty_message": "No Camera Detected",
            },
        }

        self.setup_ui()
        self.update_camera_button_style()
        self.update_camera_status("Camera is Off")
        self.update_camera_status_indicator()
        self.update_arduino_status()
        self.arduino_timer.start(100)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        self.update_responsive_layout()
        if self.last_frame is not None:
            self.render_camera_frame(self.last_frame)

    def closeEvent(self, event):
        self.stop_camera()
        self.arduino_timer.stop()
        self.set_nir_scanning(False)
        self.close_arduino_serial()
        super().closeEvent(event)

    def update_arduino_status(self):
        ports = list(list_ports.comports()) if list_ports is not None else []
        arduino_port = next((port for port in ports if self.is_arduino_port(port)), None)
        arduino_connected = arduino_port is not None
        if arduino_connected:
            self.read_arduino_messages(arduino_port)
        else:
            was_connected = self.arduino_serial is not None
            self.close_arduino_serial()
            self.nir_detected = False
            if was_connected:
                self.system_log_received.emit("Arduino serial connection lost.")

        if arduino_connected:
            self.arduino_status_label.setText("CONNECTED")
        else:
            self.arduino_status_label.setText("NOT CONNECTED")
        self._set_status_state(self.arduino_status_label, arduino_connected)
        self.update_nir_status()

    def read_arduino_messages(self, port):
        if serial is None:
            return
        if self.arduino_serial is None or self.arduino_port != port.device:
            self.close_arduino_serial()
            try:
                self.arduino_serial = serial.Serial(
                    port.device,
                    self.arduino_baud_rate,
                    timeout=0.05,
                )
                self.arduino_port = port.device
                self.system_log_received.emit(
                    f"Arduino serial connected on {port.device}."
                )
                QTimer.singleShot(1500, self.initialize_nir_scanner)
            except (serial.SerialException, OSError) as exc:
                self.arduino_serial = None
                self.arduino_port = None
                self.system_log_received.emit(
                    f"Arduino serial connection failed on {port.device}: {exc}"
                )
                return

        try:
            available = self.arduino_serial.in_waiting
            if not available:
                return
            raw_data = self.arduino_serial.read(available)
            self.serial_buffer += raw_data.decode("utf-8", errors="replace")
            lines = self.serial_buffer.split("\n")
            self.serial_buffer = lines.pop()
            for line in lines:
                message = line.strip()
                if message:
                    self.nir_message_received.emit(message)
                    self.handle_servo_status(message)
                if self.is_nir_message(message):
                    self.nir_detected = True
        except (serial.SerialException, OSError) as exc:
            self.system_log_received.emit(f"Arduino serial read failed: {exc}")
            self.close_arduino_serial()

    def set_nir_scanning(self, enabled):
        self.nir_scanning = enabled
        self.send_nir_scan_command()

    def set_nir_scan_delay(self, delay_ms):
        self.nir_scan_delay_ms = max(0, min(int(delay_ms), 60000))
        self.send_nir_scan_delay()

    def initialize_nir_scanner(self):
        self.send_nir_scan_delay()
        self.send_nir_scan_command()
        for motor in (1, 2):
            self.send_servo_sweep_config(motor)
            if self.servo_sweeping[motor]:
                self.write_arduino_command(f"W{motor},1\n")

    def set_servo_angle(self, motor, angle):
        if motor not in (1, 2):
            return
        angle = max(0, min(int(angle), 180))
        self.write_arduino_command(f"A{motor},{angle}\n")

    def set_servo_sweep_config(self, motor, minimum, maximum, speed):
        if motor not in (1, 2):
            return
        minimum = max(0, min(int(minimum), 175))
        maximum = max(minimum + 5, min(int(maximum), 180))
        speed = max(1, min(int(speed), 180))
        self.servo_minimum_angles[motor] = minimum
        self.servo_maximum_angles[motor] = maximum
        self.servo_sweep_speeds[motor] = speed
        self.send_servo_sweep_config(motor)

    def send_servo_sweep_config(self, motor):
        self.write_arduino_command(
            f"R{motor},{self.servo_minimum_angles[motor]},"
            f"{self.servo_maximum_angles[motor]},{self.servo_sweep_speeds[motor]}\n"
        )

    def set_servo_sweeping(self, motor, enabled):
        if motor not in (1, 2):
            return
        self.servo_sweeping[motor] = bool(enabled)
        self.servo_sweep_status_received.emit(motor, enabled)
        if enabled:
            self.send_servo_sweep_config(motor)
        self.write_arduino_command(f"W{motor},{1 if enabled else 0}\n")

    def write_arduino_command(self, command):
        if self.arduino_serial is None or not self.arduino_serial.is_open:
            return
        try:
            self.arduino_serial.write(command.encode("ascii"))
        except (serial.SerialException, OSError) as exc:
            self.system_log_received.emit(f"Arduino serial write failed: {exc}")
            self.close_arduino_serial()

    def handle_servo_status(self, message):
        fields = message.split(",")
        if len(fields) == 2 and fields[0] in ("SV1", "SV2"):
            try:
                angle = int(fields[1])
            except ValueError:
                return
            if 0 <= angle <= 180:
                self.servo_status_received.emit(int(fields[0][-1]), angle)
        elif len(fields) == 2 and fields[0] in ("SW1", "SW2") and fields[1] in ("0", "1"):
            self.servo_sweep_status_received.emit(
                int(fields[0][-1]), fields[1] == "1"
            )

    def send_nir_scan_delay(self):
        if self.arduino_serial is None or not self.arduino_serial.is_open:
            return
        try:
            self.arduino_serial.write(
                f"D{self.nir_scan_delay_ms}\n".encode("ascii")
            )
        except (serial.SerialException, OSError) as exc:
            self.system_log_received.emit(f"NIR scan delay command failed: {exc}")
            self.close_arduino_serial()

    def send_nir_scan_command(self):
        if self.arduino_serial is None or not self.arduino_serial.is_open:
            return
        command = b"S\n" if self.nir_scanning else b"P\n"
        try:
            self.arduino_serial.write(command)
        except (serial.SerialException, OSError) as exc:
            self.system_log_received.emit(f"NIR scan command failed: {exc}")
            self.close_arduino_serial()

    def close_arduino_serial(self):
        if self.arduino_serial is not None:
            try:
                self.arduino_serial.close()
            except (serial.SerialException, OSError) as exc:
                self.system_log_received.emit(
                    f"Arduino serial close failed: {exc}"
                )
        self.arduino_serial = None
        self.arduino_port = None
        self.serial_buffer = ""

    @staticmethod
    def is_nir_message(message):
        normalized = message.upper()
        wavelength_message = any(
            f"{wavelength}NM:" in normalized
            for wavelength in (410, 435, 460, 485, 510, 535, 560, 585, 610, 645, 680, 705, 730, 760, 810, 860, 900, 940)
        )
        return "AS7265X READY" in normalized or wavelength_message

    def update_nir_status(self):
        status = "CONNECTED" if self.nir_detected else "NOT CONNECTED"
        self.nir_status_label.setText(status)
        self._set_status_state(self.nir_status_label, self.nir_detected)

    @staticmethod
    def is_arduino_port(port):
        port_details = " ".join(
            str(value or "")
            for value in (port.description, port.manufacturer, port.product, port.hwid)
        ).lower()
        arduino_keywords = (
            "arduino",
            "esp32",
            "ch340",
            "cp210",
            "silicon labs",
            "ftdi",
            "usb serial",
            "usb-serial",
            "ttyacm",
            "ttyusb",
        )
        return any(keyword in port_details for keyword in arduino_keywords)

    def update_responsive_layout(self):
        if not hasattr(self, "middle_layout") or not hasattr(
            self, "camera_frame"
        ):
            return

        width = self.width()

        if width < 520:
            columns = 1
        elif width < 900:
            columns = 2
        else:
            columns = 4

        if columns != getattr(self, "card_columns", None):
            self.card_columns = columns
            self.reflow_cards(columns)

        is_narrow = width < 760
        self.middle_layout.setDirection(
            QBoxLayout.Direction.TopToBottom
            if is_narrow
            else QBoxLayout.Direction.LeftToRight
        )
        self.camera_frame.setMinimumHeight(180 if is_narrow else 260)

    def reflow_cards(self, columns):
        while self.cards_layout.count():
            self.cards_layout.takeAt(0)

        for index, card in enumerate(self.cards):
            self.cards_layout.addWidget(
                card,
                index // columns,
                index % columns,
            )

    def update_camera_status(self, message):
        if self.camera_frame.pixmap() is not None:
            self.camera_frame.clear()
        self.camera_frame.setText(message)
        self.camera_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def stop_camera(self):
        was_enabled = self.camera_enabled
        self.camera_enabled = False
        self.camera_timer.stop()
        if self.camera_capture is not None:
            self.camera_capture.release()
            self.camera_capture = None
        self.last_frame = None
        self.update_camera_button("Turn Camera On")
        self.update_camera_status("Camera is Off")
        self.update_camera_status_indicator()
        if was_enabled:
            self.system_log_received.emit("Camera stream stopped.")

    def open_camera(self, source):
        logging = getattr(getattr(cv2, "utils", None), "logging", None)
        if logging is None:
            return cv2.VideoCapture(source, cv2.CAP_DSHOW)

        previous_level = logging.getLogLevel()
        logging.setLogLevel(logging.LOG_LEVEL_SILENT)
        try:
            return cv2.VideoCapture(source, cv2.CAP_DSHOW)
        finally:
            logging.setLogLevel(previous_level)

    def start_camera(self):
        if self.camera_enabled and self.camera_capture is not None:
            return

        mode = "Camera"
        config = self.camera_modes.get(
            mode,
            self.camera_modes["Camera"],
        )
        candidates = config["candidates"]
        empty_message = config["empty_message"]

        for source in candidates:
            capture = None
            try:
                capture = self.open_camera(source)
            except (cv2.error, OSError) as exc:
                self.system_log_received.emit(
                    f"Camera could not be opened at source {source}: {exc}"
                )
                continue
            if capture is not None and capture.isOpened():
                try:
                    has_frame, frame = capture.read()
                except (cv2.error, OSError) as exc:
                    self.system_log_received.emit(
                        f"Camera frame read failed at startup: {exc}"
                    )
                    capture.release()
                    continue
                if not has_frame or frame is None:
                    capture.release()
                    continue

                if self.camera_capture is not None:
                    self.camera_capture.release()
                self.camera_capture = capture
                self.camera_source = source
                self.camera_enabled = True
                self.camera_timer.start(30)
                self.update_camera_button("Turn Camera Off")
                self.camera_frame.setText("")
                self.update_camera_status_indicator()
                self.system_log_received.emit("Camera stream started.")
                return

            if capture is not None:
                capture.release()

        self.camera_enabled = False
        self.update_camera_button("Turn Camera On")
        self.update_camera_status(empty_message)
        self.update_camera_status_indicator()
        self.system_log_received.emit("Camera stream could not be started.")

    def toggle_camera(self):
        if self.camera_enabled:
            self.stop_camera()
        else:
            self.start_camera()

    def update_camera_feed(self):
        if not self.camera_enabled or self.camera_capture is None or not self.camera_capture.isOpened():
            mode = "Camera"
            message = self.camera_modes.get(mode, self.camera_modes["Camera"])["empty_message"]
            self.update_camera_status(message)
            self.update_camera_button("Turn Camera On")
            self.camera_enabled = False
            if self.camera_capture is not None:
                self.camera_capture.release()
                self.camera_capture = None
            self.update_camera_status_indicator()
            return

        try:
            ret, frame = self.camera_capture.read()
        except (cv2.error, OSError) as exc:
            self.system_log_received.emit(f"Camera frame read failed: {exc}")
            self.stop_camera()
            return
        if not ret or frame is None:
            self.system_log_received.emit("Camera frame read failed; stream stopped.")
            self.stop_camera()
            return

        self.last_frame = frame.copy()

        self.render_camera_frame(frame)

    def render_camera_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb_frame.shape
        bytes_per_line = channel * width

        q_image = QImage(
            rgb_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )

        pixmap = QPixmap.fromImage(q_image)
        box_size = self.camera_frame.size()
        scaled = pixmap.scaled(
            box_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        crop_x = max((scaled.width() - box_size.width()) // 2, 0)
        crop_y = max((scaled.height() - box_size.height()) // 2, 0)
        filled = scaled.copy(crop_x, crop_y, box_size.width(), box_size.height())
        self.camera_frame.setPixmap(filled)
        self.camera_frame.setText("")

    def update_camera_button_style(self):
        if self.camera_toggle_button is None:
            return
        self.camera_toggle_button.setProperty("camera_running", self.camera_enabled)
        self.camera_toggle_button.style().unpolish(self.camera_toggle_button)
        self.camera_toggle_button.style().polish(self.camera_toggle_button)

    def set_camera_toggle_button(self, button):
        self.camera_toggle_button = button
        self.update_camera_button("Turn Camera Off" if self.camera_enabled else "Turn Camera On")

    def update_camera_button(self, text):
        if self.camera_toggle_button is None:
            return
        self.camera_toggle_button.setText(text)
        self.update_camera_button_style()

    def create_card(self, title, value, unit="", choices=None):
        card = QFrame()
        card.setProperty("class", "card")
        card.setObjectName("dashboard_metric_card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)

        title_label = QLabel(title)
        title_label.setProperty("class", "card_title")
        title_label.setObjectName("card_title")

        if choices:
            value_label = QComboBox()
            value_label.addItems(choices)
            value_label.setCurrentIndex(-1)
            value_label.setPlaceholderText("Select quality")
            value_label.setProperty("class", "card_value")
            value_label.setObjectName("card_value")
        else:
            value_label = QLabel(value)
            value_label.setProperty("class", "card_value")
            value_label.setObjectName("card_value")

        unit_label = QLabel(unit)
        unit_label.setProperty("class", "card_unit")
        unit_label.setObjectName("card_unit")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(unit_label)

        return card

    def setup_ui(self):

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(20)

        # --------------------------------
        # PAGE TITLE
        # --------------------------------

        title = QLabel("Dashboard")
        title.setObjectName("page_title")

        subtitle = QLabel(
            "Real-time cacao seed sorting and grading system"
        )
        subtitle.setObjectName("dashboard_subtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # STATUS CARDS
        # --------------------------------

        self.cards_layout = QGridLayout()
        self.cards_layout.setHorizontalSpacing(15)
        self.cards_layout.setVerticalSpacing(15)

        self.cards = [
            self.create_card("CURRENT SEED", "No data", "Seed number"),
            self.create_card("WEIGHT", "No data", "grams"),
            self.create_card("MOISTURE", "No data", "%"),
            self.create_card("QUALITY", "No data", "Classification"),
        ]
        self.card_columns = 1
        self.reflow_cards(self.card_columns)
        main_layout.addLayout(self.cards_layout)

        # --------------------------------
        # CAMERA + SYSTEM STATUS
        # --------------------------------

        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(20)
        self.middle_layout = middle_layout

        # CAMERA
        camera_container = QFrame()
        camera_container.setProperty("class", "card")
        camera_container.setObjectName("dashboard_camera_panel")

        camera_layout = QVBoxLayout(camera_container)
        camera_layout.setContentsMargins(20, 20, 20, 20)

        camera_title = QLabel("Live Camera")
        camera_title.setProperty("class", "section_title")
        camera_title.setObjectName("section_title")

        self.camera_frame = QLabel("Camera is Off")
        self.camera_frame.setObjectName("camera_frame")
        self.camera_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_frame.setMinimumSize(320, 240)
        self.camera_frame.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored,
        )
        self.camera_frame.setScaledContents(False)

        camera_layout.addWidget(camera_title)
        camera_layout.addWidget(self.camera_frame)

        middle_layout.addWidget(camera_container, 2)

        # SYSTEM STATUS
        status_container = QFrame()
        status_container.setProperty("class", "card")
        status_container.setObjectName("dashboard_status_panel")

        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(20, 20, 20, 20)
        status_layout.setSpacing(15)

        status_title = QLabel("System Status")
        status_title.setProperty("class", "section_title")
        status_title.setObjectName("section_title")

        status_layout.addWidget(status_title)

        self.camera_status_label = self.add_status(status_layout, "Camera", "NOT CONNECTED")
        self.arduino_status_label = self.add_status(status_layout, "Arduino", "NOT CONNECTED")
        self.nir_status_label = self.add_status(status_layout, "NIR Sensor", "NOT CONNECTED")
        self.add_status(status_layout, "Load Cell", "NOT CONNECTED")
        self.add_status(status_layout, "AI Model", "NOT READY")

        status_layout.addStretch()

        middle_layout.addWidget(status_container, 1)

        main_layout.addLayout(middle_layout)

        # --------------------------------
        # CONTROL BUTTONS
        # --------------------------------

        button_layout = QHBoxLayout()

        start_button = AnimatedButton("Start System")
        start_button.setObjectName("start_button")

        stop_button = AnimatedButton("Stop System")
        stop_button.setObjectName("stop_button")
        start_button.setMinimumWidth(150)
        stop_button.setMinimumWidth(150)

        button_layout.addStretch()
        button_layout.addWidget(start_button)
        button_layout.addWidget(stop_button)

        main_layout.addLayout(button_layout)

    def update_camera_status_indicator(self):
        if QMediaDevices.videoInputs():
            self.camera_status_label.setText("CONNECTED")
            self._set_status_state(self.camera_status_label, True)
            self.camera_status_changed.emit("CONNECTED")
        else:
            self.camera_status_label.setText("NOT CONNECTED")
            self._set_status_state(self.camera_status_label, False)
            self.camera_status_changed.emit("NOT CONNECTED")

    def add_status(self, layout, name, status):

        row = QHBoxLayout()
        row.setSpacing(10)

        name_label = QLabel(name)
        name_label.setObjectName("dashboard_status_name")

        status_label = QLabel(status)
        status_label.setObjectName("dashboard_status_value")
        self._set_status_state(status_label, False)

        row.addWidget(name_label)
        row.addStretch()
        row.addWidget(status_label)

        layout.addLayout(row)
        return status_label

    @staticmethod
    def _set_status_state(status_label, connected):
        status_label.setProperty(
            "connection_state",
            "connected" if connected else "disconnected",
        )
        status_label.style().unpolish(status_label)
        status_label.style().polish(status_label)
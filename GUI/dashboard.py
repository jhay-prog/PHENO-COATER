# dashboard.py

import re
from math import isfinite

import cv2

from .ai_model import get_configured_ai_model_path, load_yolo_model

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
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtMultimedia import QMediaDevices
from .animated_button import AnimatedButton


class _InferenceSignals(QObject):
    completed = Signal(int, object, str)


class _InferenceTask(QRunnable):
    def __init__(self, token, model, frame):
        super().__init__()
        self.token = token
        self.model = model
        self.frame = frame
        self.signals = _InferenceSignals()

    def run(self):
        try:
            results = self.model(self.frame, conf=0.5, verbose=False)
            result = results[0] if results else None
            self.signals.completed.emit(
                self.token,
                result,
                "",
            )
        except Exception as exc:
            self.signals.completed.emit(
                self.token,
                None,
                f"AI inference failed: {exc}",
            )


class Dashboard(QWidget):

    camera_status_changed = Signal(str)
    current_weight_changed = Signal(object)
    arduino_status_changed = Signal(str)
    system_log_received = Signal(str)
    nir_message_received = Signal(str)
    servo_status_received = Signal(int, int)
    servo_sweep_status_received = Signal(int, bool)
    EMEET_CAMERA_INDEX = 0
    GRAMS_PER_KILOGRAM = 1000.0

    def __init__(self):
        super().__init__()

        self.setObjectName("dashboard")

        self.camera_source = self.EMEET_CAMERA_INDEX
        self.arduino_baud_rate = 115200
        self.nir_scan_delay_ms = 0
        self.camera_capture = None
        self.camera_enabled = False
        self.camera_usage_enabled = True
        self.camera_usage_button = None
        self.last_frame = None
        self.last_ai_frame = None
        self.last_ai_result = None
        self.ai_model = None
        self.ai_model_path = get_configured_ai_model_path()
        self.ai_model_error = ""
        self.ai_inference_pool = QThreadPool(self)
        self.ai_inference_pool.setMaxThreadCount(1)
        self.ai_inference_busy = False
        self.ai_inference_token = 0
        self.ai_inference_task = None
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
        self.camera_connected = False
        self.arduino_connected = False
        self.arduino_status_message = ""
        self.nir_connected = False
        self.serial_buffer = ""
        self.current_weight_kg = None
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
        if self.ai_model_path:
            self.set_ai_model_path(self.ai_model_path, log_result=False)
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
        if list_ports is None or serial is None:
            self._set_arduino_status(
                "Serial support is unavailable. Install the app requirements."
            )
            return
        ports = list(list_ports.comports()) if list_ports is not None else []
        arduino_port = next((port for port in ports if self.is_arduino_port(port)), None)
        arduino_connected = arduino_port is not None
        if arduino_connected:
            self.read_arduino_messages(arduino_port)
        else:
            was_connected = self.arduino_serial is not None
            self.close_arduino_serial()
            self.nir_detected = False
            self._set_arduino_status(
                "Arduino not detected. Check the USB cable and serial port."
            )
            if was_connected:
                self.system_log_received.emit("Arduino serial connection lost.")

        self.arduino_connected = arduino_connected
        self.update_nir_status()

    def _set_arduino_status(self, message):
        if self.arduino_status_message != message:
            self.arduino_status_message = message
            self.arduino_status_changed.emit(message)

    def read_arduino_messages(self, port):
        if serial is None:
            self._set_arduino_status(
                "Serial support is unavailable. Install the app requirements."
            )
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
                self._set_arduino_status(
                    f"Connected on {port.device}; waiting for HX711 readings. "
                    "Check the sketch baud rate and finish calibration if prompted."
                )
                QTimer.singleShot(1500, self.initialize_nir_scanner)
            except (serial.SerialException, OSError) as exc:
                self.arduino_serial = None
                self.arduino_port = None
                self.system_log_received.emit(
                    f"Arduino serial connection failed on {port.device}: {exc}"
                )
                self._set_arduino_status(
                    f"Could not open {port.device}: {exc}"
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
                    weight_kg = self.parse_load_cell_weight_kg(message)
                    if weight_kg is not None:
                        self.current_weight_kg = weight_kg
                        self.current_weight_changed.emit(weight_kg)
                        self._set_arduino_status(
                            f"Live load-cell reading: {weight_kg:.3f} kg"
                        )
                    elif message.startswith(
                        (
                            "ERROR: HX711 not ready.",
                            "ERROR: One or both HX711 modules are not ready.",
                        )
                    ):
                        self._clear_current_weight()
                        self._set_arduino_status(message)
                    elif message.startswith(
                        (
                            "LOAD CELL 1 CALIBRATION",
                            "LOAD CELL 2 CALIBRATION",
                            "Empty load cell",
                            "Place a known",
                            "Remove the weight",
                            "Send C",
                        )
                    ):
                        self._set_arduino_status(
                            f"Calibration required: {message}"
                        )
                if self.is_nir_message(message):
                    self.nir_detected = True
        except (serial.SerialException, OSError) as exc:
            self.system_log_received.emit(f"Arduino serial read failed: {exc}")
            self._set_arduino_status(f"Arduino serial read failed: {exc}")
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

    def continue_load_cell_calibration(self):
        if self.arduino_serial is None or not self.arduino_serial.is_open:
            self.system_log_received.emit(
                "Cannot continue load-cell calibration: Arduino is not connected."
            )
            return
        self.write_arduino_command("C\n")

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

    @staticmethod
    def parse_load_cell_weight_kg(message):
        match = re.fullmatch(
            r"\s*Load\s+Cell\s+1\s*:\s*(-?(?:\d+(?:\.\d*)?|\.\d+))"
            r"\s*g\s*\|\s*Load\s+Cell\s+2\s*:\s*"
            r"(-?(?:\d+(?:\.\d*)?|\.\d+))\s*g\s*",
            message,
            re.IGNORECASE,
        )
        if match is None:
            return None
        weight1_grams, weight2_grams = (
            float(value) for value in match.groups()
        )
        combined_weight_grams = weight1_grams + weight2_grams
        if not isfinite(combined_weight_grams):
            return None
        return combined_weight_grams / Dashboard.GRAMS_PER_KILOGRAM

    parse_load_cell_weight = parse_load_cell_weight_kg

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
        self._clear_current_weight()

    def _clear_current_weight(self):
        if self.current_weight_kg is not None:
            self.current_weight_kg = None
            self.current_weight_changed.emit(None)

    @staticmethod
    def is_nir_message(message):
        normalized = message.upper()
        wavelength_message = any(
            f"{wavelength}NM:" in normalized
            for wavelength in (410, 435, 460, 485, 510, 535, 560, 585, 610, 645, 680, 705, 730, 760, 810, 860, 900, 940)
        )
        return "AS7265X READY" in normalized or wavelength_message

    def update_nir_status(self):
        self.nir_connected = self.nir_detected

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
        preview_width = min(608, max(320, width - 36))
        preview_height = 180 if is_narrow else 320
        self.camera_frame.setFixedSize(preview_width, preview_height)
        self.dashboard_subtitle.setVisible(True)

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
        self.ai_inference_token += 1
        self.camera_timer.stop()
        if self.camera_capture is not None:
            self.camera_capture.release()
            self.camera_capture = None
        self.last_frame = None
        self.last_ai_frame = None
        self.last_ai_result = None
        self.last_ai_frame = None
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
        if not self.camera_usage_enabled:
            self.system_log_received.emit(
                "Camera use is disabled in system settings."
            )
            self.update_camera_status("Camera use is disabled")
            return
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
                self.camera_frame.setText("")
                self.update_camera_status_indicator()
                self.system_log_received.emit("Camera stream started.")
                return

            if capture is not None:
                capture.release()

        self.camera_enabled = False
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
        if self.ai_model is not None:
            if not self.ai_inference_busy:
                self.ai_inference_busy = True
                task = _InferenceTask(
                    self.ai_inference_token,
                    self.ai_model,
                    frame.copy(),
                )
                task.signals.completed.connect(self._on_ai_inference_completed)
                self.ai_inference_task = task
                self.ai_inference_pool.start(task)
            if self.last_ai_result is not None:
                frame = self.last_ai_result.plot(img=frame)
        else:
            self.last_ai_result = None

        self.last_ai_frame = frame.copy() if self.ai_model is not None else None
        self.render_camera_frame(frame)

    def _on_ai_inference_completed(self, token, result, error):
        self.ai_inference_busy = False
        self.ai_inference_task = None
        if token != self.ai_inference_token:
            return
        if error:
            self.ai_model = None
            self.last_ai_result = None
            self.last_ai_frame = None
            self.ai_model_error = error
            self.system_log_received.emit(error)
            return
        self.last_ai_result = result

    def set_ai_model_path(self, model_path, log_result=True):
        model_path = str(model_path or "").strip()
        self.ai_inference_token += 1
        self.last_ai_result = None
        self.last_ai_frame = None
        if not model_path:
            self.ai_model = None
            self.ai_model_path = ""
            self.ai_model_error = ""
            if log_result:
                self.system_log_received.emit("AI model integration disabled.")
            return True

        try:
            model, model_file = load_yolo_model(model_path)
        except (OSError, ValueError, RuntimeError) as exc:
            self.ai_model_error = str(exc)
            if log_result:
                self.system_log_received.emit(self.ai_model_error)
            return False

        self.ai_model = model
        self.ai_model_path = model_path
        self.ai_model_error = ""
        if log_result:
            self.system_log_received.emit(
                f"AI model loaded from {model_file}."
            )
        return True

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

    def update_camera_usage_button(self):
        if self.camera_usage_button is None:
            return
        self.camera_usage_button.setChecked(self.camera_usage_enabled)
        self.camera_usage_button.setText(
            "Camera Usage: Enabled"
            if self.camera_usage_enabled
            else "Camera Usage: Disabled"
        )
        self.camera_usage_button.setProperty(
            "camera_usage_enabled",
            self.camera_usage_enabled,
        )
        self.camera_usage_button.style().unpolish(self.camera_usage_button)
        self.camera_usage_button.style().polish(self.camera_usage_button)

    def set_camera_usage_button(self, button):
        self.camera_usage_button = button
        self.update_camera_usage_button()

    def set_camera_usage_enabled(self, enabled):
        self.camera_usage_enabled = bool(enabled)
        self.update_camera_usage_button()
        if not self.camera_usage_enabled:
            self.stop_camera()

    def create_card(self, title, value, unit="", choices=None):
        card = QFrame()
        card.setProperty("class", "card")
        card.setObjectName("dashboard_metric_card")
        card.setMinimumHeight(112)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

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
        main_layout.setContentsMargins(14, 12, 14, 14)
        main_layout.setSpacing(20)

        # --------------------------------
        # PAGE TITLE
        # --------------------------------

        title = QLabel("Dashboard")
        title.setObjectName("page_title")
        title.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )

        subtitle = QLabel(
            "Real-time cacao seed sorting and grading system"
        )
        subtitle.setObjectName("dashboard_subtitle")
        subtitle.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )
        self.dashboard_subtitle = subtitle

        heading_layout = QVBoxLayout()
        heading_layout.setContentsMargins(0, 0, 0, 0)
        heading_layout.setSpacing(4)
        heading_layout.addWidget(title)
        heading_layout.addWidget(subtitle)
        main_layout.addLayout(heading_layout)

        # --------------------------------
        # STATUS CARDS
        # --------------------------------

        self.cards_layout = QGridLayout()
        self.cards_layout.setHorizontalSpacing(12)
        self.cards_layout.setVerticalSpacing(12)

        self.cards = [
            self.create_card("CURRENT SEED", "", "Seed number"),
            self.create_card("WEIGHT", "", "grams"),
            self.create_card("MOISTURE", "", "%"),
            self.create_card("QUALITY", "", "Classification"),
        ]
        self.card_columns = 1
        self.reflow_cards(self.card_columns)
        main_layout.addLayout(self.cards_layout)

        # --------------------------------
        # CAMERA
        # --------------------------------

        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(4)
        self.middle_layout = middle_layout

        # CAMERA
        camera_container = QFrame()
        self.camera_container = camera_container
        camera_container.setProperty("class", "card")
        camera_container.setObjectName("dashboard_camera_panel")
        camera_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        camera_layout = QVBoxLayout(camera_container)
        camera_layout.setContentsMargins(8, 8, 8, 8)

        camera_title = QLabel("Live Camera")
        camera_title.setProperty("class", "section_title")
        camera_title.setObjectName("section_title")
        camera_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.camera_frame = QLabel("Camera is Off")
        self.camera_frame.setObjectName("camera_frame")
        self.camera_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_frame.setMinimumSize(320, 180)
        self.camera_frame.setMaximumSize(608, 320)
        self.camera_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.camera_frame.setScaledContents(False)

        camera_layout.addWidget(camera_title)
        camera_preview_layout = QHBoxLayout()
        camera_preview_layout.setContentsMargins(0, 0, 0, 30)
        camera_preview_layout.addStretch()
        camera_preview_layout.addWidget(self.camera_frame)
        camera_preview_layout.addStretch()
        camera_layout.addLayout(camera_preview_layout)

        middle_layout.addWidget(camera_container, 1)

        main_layout.addLayout(middle_layout)

        # --------------------------------
        # CONTROL BUTTONS
        # --------------------------------

        button_layout = QHBoxLayout()

        start_button = AnimatedButton("Start System")
        start_button.setObjectName("start_button")
        self.start_system_button = start_button

        stop_button = AnimatedButton("Stop System")
        stop_button.setObjectName("stop_button")
        self.stop_system_button = stop_button
        start_button.setMinimumWidth(150)
        stop_button.setMinimumWidth(150)

        button_layout.addStretch()
        button_layout.addWidget(start_button)
        button_layout.addWidget(stop_button)

        main_layout.addLayout(button_layout)

    def update_camera_status_indicator(self):
        self.camera_connected = bool(QMediaDevices.videoInputs())
        self.camera_status_changed.emit(
            "CONNECTED" if self.camera_connected else "NOT CONNECTED"
        )
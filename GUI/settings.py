from PySide6.QtCore import Qt, QTimer
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QFrame, QVBoxLayout, QWidget
from .animated_button import AnimatedButton

try:
    from serial.tools import list_ports
except ImportError:
    list_ports = None


class SettingsPage(QWidget):
    def __init__(self, camera_controller=None):
        super().__init__()
        self.setObjectName("settings_page")
        self.camera_controller = camera_controller
        self.saved_nir_scan_delay_ms = getattr(
            camera_controller,
            "nir_scan_delay_ms",
            0,
        )
        self.setup_ui()
        self.port_refresh_timer = QTimer(self)
        self.port_refresh_timer.timeout.connect(self.refresh_live_settings)
        self.refresh_live_settings()
        self.port_refresh_timer.start(1000)
        if camera_controller is not None:
            camera_controller.set_camera_toggle_button(self.camera_toggle_button)
            self.camera_toggle_button.clicked.connect(camera_controller.toggle_camera)

    def refresh_serial_ports(self):
        ports = list(list_ports.comports()) if list_ports is not None else []
        port_names = [port.device for port in ports]
        current_port = self.arduino_port_input.currentData()

        arduino_port = next(
            (
                port.device
                for port in ports
                if self.camera_controller is not None
                and self.camera_controller.is_arduino_port(port)
            ),
            None,
        )
        selected_port = arduino_port or (
            current_port if current_port in port_names else None
        )
        if selected_port is None and port_names:
            selected_port = port_names[0]

        existing_ports = [
            self.arduino_port_input.itemData(index)
            for index in range(1, self.arduino_port_input.count())
        ]
        if (
            self.arduino_port_input.count() == len(port_names) + 1
            and existing_ports == port_names
            and current_port == selected_port
        ):
            return

        self.arduino_port_input.clear()
        self.arduino_port_input.addItem("No serial ports detected", None)
        for port_name in port_names:
            self.arduino_port_input.addItem(port_name, port_name)
        self.arduino_port_input.setCurrentIndex(
            self.arduino_port_input.findData(selected_port)
            if selected_port is not None
            else 0
        )
        self.arduino_port_input.setEnabled(bool(port_names))

    def refresh_live_settings(self):
        self.refresh_serial_ports()

        baud_rate = getattr(self.camera_controller, "arduino_baud_rate", 9600)
        arduino_serial = getattr(self.camera_controller, "arduino_serial", None)
        if arduino_serial is not None:
            baud_rate = arduino_serial.baudrate
        self.baud_rate_input.setText(str(baud_rate))

        camera_source = getattr(self.camera_controller, "camera_source", 0)
        cameras = QMediaDevices.videoInputs()
        if isinstance(camera_source, int) and 0 <= camera_source < len(cameras):
            camera_name = cameras[camera_source].description()
        else:
            camera_name = "No camera detected"
        self.camera_source_input.setText(camera_name)

    def set_nir_scan_delay(self, delay_ms):
        if self.camera_controller is not None:
            self.camera_controller.set_nir_scan_delay(delay_ms)

    def commit_nir_scan_delay(self):
        text = self.scan_delay_input.text()
        if text.isdigit():
            delay_ms = int(text)
            if delay_ms <= 60000:
                self.scan_delay_input.setText(str(delay_ms))
                return
        self.scan_delay_input.setText(str(self.saved_nir_scan_delay_ms))

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 30)
        layout.setSpacing(20)

        header = QHBoxLayout()
        title_column = QVBoxLayout()
        title_label = QLabel("Settings")
        title_label.setObjectName("page_title")
        description_label = QLabel("Configure connections and sensor settings.")
        description_label.setObjectName("settings_description")
        title_column.addWidget(title_label)
        title_column.addWidget(description_label)
        header.addLayout(title_column)
        header.addStretch()
        camera_toggle_button = AnimatedButton("Turn Camera On")
        camera_toggle_button.setObjectName("camera_toggle_button")
        self.camera_toggle_button = camera_toggle_button
        header.addWidget(camera_toggle_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        connection_form = QFormLayout()
        connection_form.setHorizontalSpacing(25)
        connection_form.setVerticalSpacing(15)
        port_input = QComboBox()
        self.arduino_port_input = port_input
        connection_form.addRow("Arduino", port_input)
        baud_input = QLineEdit()
        baud_input.setReadOnly(True)
        self.baud_rate_input = baud_input
        connection_form.addRow("Baud rate", baud_input)
        camera_input = QLineEdit()
        camera_input.setReadOnly(True)
        self.camera_source_input = camera_input
        connection_form.addRow("Camera source", camera_input)
        scan_delay_input = QLineEdit()
        scan_delay_input.setValidator(QIntValidator(0, 60000, scan_delay_input))
        scan_delay_input.setMaxLength(5)
        scan_delay_input.setText(str(self.saved_nir_scan_delay_ms))
        scan_delay_input.editingFinished.connect(self.commit_nir_scan_delay)
        self.scan_delay_input = scan_delay_input
        connection_form.addRow("NIR scan delay (ms)", scan_delay_input)
        model_input = QLineEdit()
        model_input.setPlaceholderText("Path to AI model file")
        connection_form.addRow("AI model path", model_input)
        connection_panel = QFrame()
        connection_panel.setObjectName("settings_panel")
        connection_panel.setLayout(connection_form)
        layout.addWidget(connection_panel)

        sensor_form = QFormLayout()
        sensor_form.setHorizontalSpacing(25)
        sensor_form.setVerticalSpacing(15)
        weight_input = QDoubleSpinBox()
        weight_input.setRange(-1000000, 1000000)
        weight_input.setDecimals(3)
        weight_input.setSuffix(" g")
        sensor_form.addRow("Load cell offset", weight_input)
        moisture_input = QDoubleSpinBox()
        moisture_input.setRange(-1000000, 1000000)
        moisture_input.setDecimals(3)
        sensor_form.addRow("Moisture offset", moisture_input)
        sensor_panel = QFrame()
        sensor_panel.setObjectName("settings_panel")
        sensor_panel.setLayout(sensor_form)
        layout.addWidget(sensor_panel)

        actions = QHBoxLayout()
        actions.addStretch()
        reset_button = AnimatedButton("RESET")
        reset_button.setObjectName("settings_reset_button")
        save_button = AnimatedButton("SAVE SETTINGS")
        save_button.setObjectName("settings_save_button")
        save_state = QLabel()
        save_state.setObjectName("settings_save_state")

        def reset_settings():
            self.refresh_live_settings()
            scan_delay_input.setText("0")
            model_input.clear()
            weight_input.setValue(0)
            moisture_input.setValue(0)
            save_state.setText("Settings reset")

        def save_settings():
            text = scan_delay_input.text()
            if not text.isdigit() or int(text) > 60000:
                save_state.setText("Enter a delay from 0 to 60000 ms")
                return
            delay_ms = int(text)
            self.set_nir_scan_delay(delay_ms)
            self.saved_nir_scan_delay_ms = delay_ms
            scan_delay_input.setText(str(delay_ms))
            save_state.setText("Settings saved")

        reset_button.clicked.connect(reset_settings)
        save_button.clicked.connect(save_settings)
        actions.addWidget(save_state)
        actions.addWidget(reset_button)
        actions.addWidget(save_button)
        layout.addLayout(actions)
        layout.addStretch()

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import date
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QPoint, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from GUI.admin_panel import AdminControlPanel, AdminPasswordResetDialog
from GUI.admin_login import AdminLoginDialog
from GUI.auth import AdminCredentials, AdminSession, SUPER_ADMIN_ROLE
from GUI.bean_data_sheet import BeanDataSheetPage
from GUI.camera import CameraPage
from GUI.dashboard import Dashboard
from GUI.main_window import MainWindow
from GUI.pricing import PricingSettingsPage
from GUI.settings import SettingsPage
from GUI.styles import APP_STYLE
from NIR.as7265x import AS7265XReader, WAVELENGTHS


class FakeDashboard(QWidget):
    camera_status_changed = Signal(str)
    current_weight_changed = Signal(object)
    arduino_status_changed = Signal(str)
    arduino_connection_changed = Signal(bool)
    ir_sensor_status_changed = Signal(bool)
    system_log_received = Signal(str)
    nir_message_received = Signal(str)
    bean_data_updated = Signal(object)
    servo_status_received = Signal(int, int)
    servo_sweep_status_received = Signal(int, bool)

    def __init__(self):
        super().__init__()
        self.camera_enabled = False
        self.camera_usage_enabled = True
        self.camera_start_count = 0
        self.camera_stop_count = 0
        self.start_system_button = QPushButton()
        self.stop_system_button = QPushButton()
        self.camera_capture = None
        self.camera_connected = False
        self.arduino_connected = False
        self.ir_sensor_connected = False
        self.arduino_status_message = "Arduino not detected."
        self.current_weight_kg = None
        self.total_bean_count = 0
        self.arduino_serial = None
        self.arduino_baud_rate = 115200
        self.selected_arduino_port = None
        self.camera_source = 0
        self.nir_scan_delay_ms = 0
        self.nir_detected = False
        self.nir_connected = False
        self.ir_batch_active = False
        self.nir_scanning = False
        self.servo_sweeping = {1: False, 2: False}
        self.camera_button = None
        self.commands = []

    def set_camera_usage_button(self, button):
        self.camera_button = button
        if button is not None:
            button.setChecked(self.camera_usage_enabled)
            button.setText(
                "Camera Usage: Enabled"
                if self.camera_usage_enabled
                else "Camera Usage: Disabled"
            )

    def set_camera_usage_enabled(self, enabled):
        self.camera_usage_enabled = enabled
        if self.camera_button is not None:
            self.camera_button.setText(
                "Camera Usage: Enabled"
                if enabled
                else "Camera Usage: Disabled"
            )
        if not enabled:
            self.stop_camera()

    def toggle_camera(self):
        if self.camera_enabled:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        if not self.camera_usage_enabled:
            return
        self.camera_start_count += 1
        self.camera_enabled = True

    def stop_camera(self):
        self.camera_stop_count += 1
        self.camera_enabled = False

    def update_responsive_layout(self):
        pass

    @staticmethod
    def is_arduino_port(port):
        return Dashboard.is_arduino_port(port)

    def set_arduino_port(self, port):
        self.selected_arduino_port = port

    def set_nir_scanning(self, enabled):
        self.commands.append(("scan", enabled))

    def get_bean_data_snapshot(self):
        return {
            "bean_id": "0" * 12,
            "bean_count": self.total_bean_count,
            "batch_weight_grams": None,
            "moisture": None,
            "quality": "UNDEFINED",
        }

    def start_system(self):
        self.commands.append(("sample", True))
        self.start_camera()

    def stop_system(self):
        self.commands.append(("sample", False))
        self.stop_camera()

    def continue_load_cell_calibration(self):
        self.commands.append(("calibration-continue",))

    def set_servo_angle(self, motor, angle):
        self.commands.append(("angle", motor, angle))

    def set_servo_sweep_config(self, motor, minimum, maximum, speed):
        self.commands.append(("sweep-config", motor, minimum, maximum, speed))

    def set_servo_sweeping(self, motor, enabled):
        self.commands.append(("sweep", motor, enabled))


class HardwareCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_camera_unavailable_message_uses_readable_theme_colors_and_fonts(self):
        previous_style = self.application.styleSheet()
        self.application.setStyleSheet(APP_STYLE)
        self.addCleanup(self.application.setStyleSheet, previous_style)
        warning = QMessageBox()
        warning.setObjectName("camera_unavailable_dialog")
        warning.setStandardButtons(QMessageBox.StandardButton.Ok)
        ok_button = warning.button(QMessageBox.StandardButton.Ok)
        ok_button.setObjectName("camera_unavailable_ok_button")
        warning.style().polish(warning)
        ok_button.style().polish(ok_button)

        preview = QLabel("No camera connected")
        preview.setObjectName("main_camera_frame")
        preview.style().polish(preview)

        self.assertEqual(
            ok_button.palette().color(ok_button.backgroundRole()).name(),
            "#2e7d4f",
        )
        self.assertEqual(
            ok_button.palette().color(ok_button.foregroundRole()).name(),
            "#ffffff",
        )
        self.assertEqual(
            preview.palette().color(preview.backgroundRole()).name(),
            "#f4fbf5",
        )
        self.assertEqual(
            preview.palette().color(preview.foregroundRole()).name(),
            "#173f2a",
        )
        self.assertEqual(ok_button.font().weight(), 700)
        self.assertEqual(preview.font().weight(), 700)
        warning.close()

    def test_arduino_port_detection_uses_existing_usb_serial_heuristic(self):
        arduino = SimpleNamespace(
            device="COM3",
            description="USB Serial Device",
            manufacturer="Arduino",
            product="",
            hwid="USB VID:PID",
        )
        generic = SimpleNamespace(
            device="COM4",
            description="USB Serial Device",
            manufacturer="",
            product="",
            hwid="",
        )
        unrelated = SimpleNamespace(
            device="COM8",
            description="Bluetooth Adapter",
            manufacturer="",
            product="",
            hwid="",
        )
        self.assertTrue(Dashboard.is_arduino_port(arduino))
        self.assertTrue(Dashboard.is_arduino_port(generic))
        self.assertFalse(Dashboard.is_arduino_port(unrelated))

    def test_arduino_is_not_connected_when_serial_port_cannot_be_opened(self):
        dashboard = Dashboard()
        arduino = SimpleNamespace(
            device="COM-test",
            description="Arduino Mega 2560",
            manufacturer="",
            product="",
            hwid="",
        )

        with patch("GUI.dashboard.list_ports.comports", return_value=[arduino]):
            with patch(
                "GUI.dashboard.serial.Serial",
                side_effect=OSError("port is already open"),
            ):
                dashboard.update_arduino_status()

        self.assertFalse(dashboard.arduino_connected)
        self.assertIsNone(dashboard.arduino_serial)

    def test_selected_arduino_port_is_used_instead_of_first_detected_port(self):
        dashboard = Dashboard()
        dashboard.selected_arduino_port = "COM4"
        ports = [
            SimpleNamespace(device="COM3", description="Arduino Mega"),
            SimpleNamespace(device="COM4", description="USB Serial Device"),
        ]
        mock_serial = SimpleNamespace(
            is_open=True,
            in_waiting=0,
            close=lambda: None,
        )

        with patch("GUI.dashboard.list_ports.comports", return_value=ports):
            with patch(
                "GUI.dashboard.serial.Serial",
                return_value=mock_serial,
            ) as serial_factory:
                dashboard.update_arduino_status()

        serial_factory.assert_called_once_with("COM4", 115200, timeout=0.05)
        self.assertEqual(dashboard.arduino_port, "COM4")

    def test_dual_load_cell_readings_are_summed_and_converted_to_kilograms(self):
        self.assertEqual(
            Dashboard.parse_load_cell_weight_kg(
                "Load Cell 1: 1250.00 g | Load Cell 2: 750.00 g"
            ),
            2.0,
        )
        self.assertEqual(
            Dashboard.parse_load_cell_weight_kg(
                "Load Cell 1: -12.50 g | Load Cell 2: 1000.00 g"
            ),
            0.9875,
        )
        self.assertIsNone(
            Dashboard.parse_load_cell_weight_kg(
                "Load Cell 1 reading: 1250.00 g"
            )
        )
        self.assertEqual(
            Dashboard.parse_load_cell_weight_kg(
                "Load Cell 1: 125.00 g | Load Cell 2: 125.00 g"
            ),
            0.25,
        )

    def test_ir_bean_count_messages_update_dashboard_total(self):
        dashboard = Dashboard()
        self.assertEqual(dashboard.total_beans_value.text(), "0")
        commands = []
        serial_data = b"PHENOCOATER_BEAN_COUNTER_READY\n"
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            in_waiting=0,
            write=lambda command: commands.append(command),
        )
        dashboard.arduino_port = "COM-test"
        dashboard.start_camera = lambda: None

        dashboard.start_system()
        self.assertNotIn(b"START_SAMPLE\n", commands)
        dashboard.arduino_serial.in_waiting = len(serial_data)
        dashboard.arduino_serial.read = lambda size: serial_data
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertIn(b"START_SAMPLE\n", commands)
        count_data = b"BEAN_COUNT: 1\nObject Count: 2\nBEAN_COUNT: invalid\n"
        dashboard.arduino_serial.in_waiting = len(count_data)
        dashboard.arduino_serial.read = lambda size: count_data
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))

        self.assertEqual(dashboard.total_bean_count, 2)
        self.assertEqual(dashboard.total_beans_value.text(), "2")
        self.assertEqual(
            dashboard.current_seed_value.text(),
            f"{date.today():%Y%m%d}0002",
        )

        dashboard.set_ir_sample_active(False)
        final_count = b"FINAL_BEAN_COUNT: 2\n"
        dashboard.arduino_serial = SimpleNamespace(
            in_waiting=len(final_count),
            read=lambda size: final_count,
        )
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertEqual(dashboard.total_beans_value.text(), "2")

    def test_ir_detection_event_updates_count_before_arduino_count_line(self):
        dashboard = Dashboard()
        dashboard.set_ir_sample_active(True)
        serial_data = b"IR_SENSOR_DETECTED\nBEAN_COUNT: 1\n"
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            in_waiting=len(serial_data),
            read=lambda size: serial_data,
        )
        dashboard.arduino_port = "COM-test"

        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))

        self.assertEqual(dashboard.total_bean_count, 1)
        self.assertEqual(dashboard.total_beans_value.text(), "1")
        self.assertEqual(
            dashboard.current_seed_value.text(),
            f"{date.today():%Y%m%d}0001",
        )

    def test_ir_detection_event_updates_count_without_count_line(self):
        dashboard = Dashboard()
        dashboard.set_ir_sample_active(True)
        detection = b"IR_SENSOR_DETECTED\n"
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            in_waiting=len(detection),
            read=lambda size: detection,
        )
        dashboard.arduino_port = "COM-test"

        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))

        self.assertEqual(dashboard.total_bean_count, 1)
        self.assertEqual(dashboard.total_beans_value.text(), "1")

    def test_ir_detection_updates_dashboard_after_sample_start_ack(self):
        dashboard = Dashboard()
        commands = []
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            in_waiting=0,
            write=lambda command: commands.append(command),
        )
        dashboard.arduino_port = "COM-test"
        dashboard.start_camera = lambda: None
        dashboard.start_system()

        ready = b"PHENOCOATER_BEAN_COUNTER_READY\n"
        dashboard.arduino_serial.in_waiting = len(ready)
        dashboard.arduino_serial.read = lambda size: ready
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertIn(b"START_SAMPLE\n", commands)

        detection = (
            b"SAMPLE_STARTED\n"
            b"IR_SENSOR_DETECTED\n"
            b"BEAN_COUNT: 1\n"
        )
        dashboard.arduino_serial.in_waiting = len(detection)
        dashboard.arduino_serial.read = lambda size: detection
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))

        self.assertEqual(dashboard.total_beans_value.text(), "1")
        self.assertEqual(dashboard.total_bean_count, 1)

    def test_legacy_object_count_messages_update_total_and_seed_id(self):
        dashboard = Dashboard()
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            in_waiting=len(b"Object Count: 1\n"),
            read=lambda size: b"Object Count: 1\n",
        )
        dashboard.arduino_port = "COM-test"
        dashboard.set_ir_sample_active(True)

        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))

        self.assertEqual(dashboard.total_bean_count, 1)
        self.assertEqual(dashboard.total_beans_value.text(), "1")
        self.assertEqual(
            dashboard.current_seed_value.text(),
            f"{date.today():%Y%m%d}0001",
        )

    def test_ir_sensor_is_not_inferred_from_firmware_ready_message(self):
        dashboard = Dashboard()
        ready_message = b"PHENOCOATER_BEAN_COUNTER_READY\n"
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            in_waiting=len(ready_message),
            read=lambda size: ready_message,
            close=lambda: None,
        )
        dashboard.arduino_port = "COM-test"

        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))

        self.assertFalse(dashboard.ir_sensor_connected)

        detection_message = b"IR_SENSOR_DETECTED\n"
        dashboard.arduino_serial.in_waiting = len(detection_message)
        dashboard.arduino_serial.read = lambda size: detection_message
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))

        self.assertTrue(dashboard.ir_sensor_connected)

        dashboard.close_arduino_serial()
        self.assertFalse(dashboard.ir_sensor_connected)

    def test_ir_object_count_output_marks_sensor_connected_only_after_detection(self):
        dashboard = Dashboard()
        dashboard.arduino_port = "COM-test"
        response = b"Object Count: 0\n"
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            in_waiting=len(response),
            read=lambda size: response,
        )

        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertFalse(dashboard.ir_sensor_connected)

        response = b"Object Count: 1\n"
        dashboard.arduino_serial.in_waiting = len(response)
        dashboard.arduino_serial.read = lambda size: response
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertTrue(dashboard.ir_sensor_connected)

        response = b"Object Count: 0\n"
        dashboard.arduino_serial.in_waiting = len(response)
        dashboard.arduino_serial.read = lambda size: response
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertFalse(dashboard.ir_sensor_connected)

    def test_ir_power_status_updates_and_overrides_latched_detection(self):
        dashboard = Dashboard()
        dashboard.arduino_port = "COM-test"
        connected_status = b"IR_SENSOR_STATUS:CONNECTED\n"
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            in_waiting=len(connected_status),
            read=lambda size: connected_status,
        )

        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertTrue(dashboard.ir_sensor_connected)

        disconnected_status = b"IR_SENSOR_STATUS:DISCONNECTED\n"
        dashboard.arduino_serial.in_waiting = len(disconnected_status)
        dashboard.arduino_serial.read = lambda size: disconnected_status
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertFalse(dashboard.ir_sensor_connected)

        object_count = b"Object Count: 2\n"
        dashboard.arduino_serial.in_waiting = len(object_count)
        dashboard.arduino_serial.read = lambda size: object_count
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertTrue(dashboard.ir_sensor_connected)

    def test_ir_disconnect_status_resets_latched_state(self):
        dashboard = Dashboard()
        dashboard.arduino_port = "COM-test"
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            in_waiting=0,
            read=lambda size: b"",
        )

        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        dashboard._set_ir_sensor_connected(True)
        self.assertTrue(dashboard.ir_sensor_connected)

        disconnected = b"IR_SENSOR_STATUS:DISCONNECTED\n"
        dashboard.arduino_serial.in_waiting = len(disconnected)
        dashboard.arduino_serial.read = lambda size: disconnected
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertFalse(dashboard.ir_sensor_connected)

        reconnected = b"IR_SENSOR_STATUS:CONNECTED\n"
        dashboard.arduino_serial.in_waiting = len(reconnected)
        dashboard.arduino_serial.read = lambda size: reconnected
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertTrue(dashboard.ir_sensor_connected)

    def test_arduino_firmware_baud_matches_dashboard_primary_baud(self):
        firmware_path = (
            Path(__file__).parents[1]
            / "NIR"
            / "as7265x"
            / "as7265x.ino"
        )
        firmware = firmware_path.read_text(encoding="utf-8")

        self.assertIn("Serial.begin(115200);", firmware)
        self.assertEqual(Dashboard().arduino_primary_baud_rate, 115200)

    def test_arduino_protocol_timeout_keeps_115200_and_reports_error(self):
        dashboard = Dashboard()
        dashboard.arduino_port = "COM-test"
        dashboard.arduino_connection_started_at = 0.0
        dashboard.arduino_baud_rate = 115200
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            close=lambda: None,
        )
        messages = []
        dashboard.system_log_received.connect(messages.append)

        with patch("GUI.dashboard.time.monotonic", return_value=6.0):
            dashboard._check_arduino_protocol_timeout()

        self.assertEqual(dashboard.arduino_baud_rate, 115200)
        self.assertIn("No Arduino response at 115200 baud.", messages[0])
        self.assertTrue(dashboard.arduino_protocol_timeout_reported)

    def test_arduino_protocol_timeout_does_not_report_before_timeout(self):
        dashboard = Dashboard()
        dashboard.arduino_port = "COM-test"
        dashboard.arduino_connection_started_at = 0.0
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            close=lambda: None,
        )

        with patch("GUI.dashboard.time.monotonic", return_value=1.5):
            dashboard._check_arduino_protocol_timeout()

        self.assertFalse(dashboard.arduino_protocol_timeout_reported)
        self.assertEqual(dashboard.arduino_baud_rate, 115200)

    def test_late_arduino_ready_message_clears_protocol_timeout(self):
        dashboard = Dashboard()
        dashboard.arduino_port = "COM-test"
        dashboard.arduino_protocol_timeout_reported = True
        ready = b"PHENOCOATER_BEAN_COUNTER_READY\n"
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            in_waiting=len(ready),
            read=lambda size: ready,
            write=lambda command: len(command),
        )

        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))

        self.assertFalse(dashboard.arduino_protocol_timeout_reported)
        self.assertEqual(dashboard.arduino_baud_rate, 115200)
        self.assertIn("ready", dashboard.arduino_status_message.lower())

    def test_ir_sample_start_retries_until_firmware_acknowledges(self):
        dashboard = Dashboard()
        dashboard.ir_sample_requested = True
        dashboard.arduino_initialization_complete = True
        dashboard.ir_sample_command_sent = True
        dashboard.ir_sample_last_command_at = 10.0
        commands = []
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            write=lambda command: commands.append(command),
        )

        with patch("GUI.dashboard.time.monotonic", return_value=11.1):
            dashboard._retry_ir_sample_start()

        self.assertEqual(commands, [b"START_SAMPLE\n"])

        dashboard.ir_sample_acknowledged = True
        dashboard.ir_sample_last_command_at = 10.0
        with patch("GUI.dashboard.time.monotonic", return_value=12.2):
            dashboard._retry_ir_sample_start()

        self.assertEqual(commands, [b"START_SAMPLE\n"])

    def test_nir_status_query_reports_connected_and_disconnected_states(self):
        dashboard = Dashboard()
        dashboard.arduino_port = "COM-test"
        status_data = b"NIR_STATUS:CONNECTED\n"
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            in_waiting=len(status_data),
            read=lambda size: status_data,
            close=lambda: None,
        )

        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        dashboard.update_nir_status()
        self.assertTrue(dashboard.nir_connected)

        status_data = b"NIR_STATUS:NOT_CONNECTED\n"
        dashboard.arduino_serial.in_waiting = len(status_data)
        dashboard.arduino_serial.read = lambda size: status_data
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        dashboard.update_nir_status()
        self.assertFalse(dashboard.nir_connected)

    def test_unsolicited_arduino_counts_are_ignored_outside_a_batch(self):
        dashboard = Dashboard()
        self.assertFalse(dashboard.update_total_bean_count("BEAN_COUNT: 4"))
        self.assertFalse(
            dashboard.update_total_bean_count("FINAL_BEAN_COUNT: 4")
        )
        self.assertEqual(dashboard.total_beans_value.text(), "0")
        self.assertEqual(dashboard.current_seed_value.text(), "0" * 12)

    def test_arduino_connection_does_not_start_ir_sample_automatically(self):
        dashboard = Dashboard()
        commands = []
        dashboard.arduino_serial = SimpleNamespace(
            is_open=True,
            write=lambda command: commands.append(command),
        )

        dashboard.initialize_nir_scanner()

        self.assertNotIn(b"START_SAMPLE\n", commands)
        self.assertEqual(commands, [])

        dashboard.arduino_initialization_complete = True
        dashboard.initialize_nir_scanner()
        self.assertIn(b"N?\n", commands)

    def test_start_and_stop_system_control_ir_sample(self):
        dashboard = Dashboard()
        commands = []
        dashboard.write_arduino_command = commands.append
        dashboard.arduino_serial = SimpleNamespace(is_open=True)
        dashboard.arduino_initialization_complete = True
        dashboard.start_camera = lambda: None
        dashboard.stop_camera = lambda: None
        dashboard.set_ir_sample_active(True)
        dashboard.update_total_bean_count("BEAN_COUNT: 6")

        dashboard.start_system()
        self.assertTrue(dashboard.ir_sample_requested)
        self.assertEqual(commands[-1], "START_SAMPLE\n")
        self.assertEqual(dashboard.total_beans_value.text(), "0")

        dashboard.stop_system()
        self.assertFalse(dashboard.ir_sample_requested)
        self.assertEqual(commands[-1], "STOP_SAMPLE\n")

        final_count = b"FINAL_BEAN_COUNT: 3\n"
        dashboard.arduino_serial = SimpleNamespace(
            in_waiting=len(final_count),
            read=lambda size: final_count,
        )
        dashboard.arduino_port = "COM-test"
        dashboard.read_arduino_messages(SimpleNamespace(device="COM-test"))
        self.assertEqual(dashboard.total_beans_value.text(), "3")
        self.assertEqual(
            dashboard.current_seed_value.text(),
            f"{date.today():%Y%m%d}0003",
        )

    def test_dashboard_displays_current_combined_load_as_batch_weight(self):
        dashboard = Dashboard()
        self.assertEqual(dashboard.batch_weight_value.text(), "0")

        dashboard.update_batch_weight_display(1.275)

        self.assertEqual(dashboard.batch_weight_value.text(), "1275.00")
        self.assertEqual(
            dashboard.cards[1].findChild(QLabel, "card_title").text(),
            "TOTAL BATCH WEIGHT",
        )

        dashboard.update_batch_weight_display(None)
        self.assertEqual(dashboard.batch_weight_value.text(), "0")

    def test_dashboard_keeps_original_element_sizes_with_compact_spacing(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        dashboard = Dashboard()
        scroll.setWidget(dashboard)
        scroll.resize(630, 420)
        scroll.show()
        self.application.processEvents()

        self.assertEqual(dashboard.card_columns, 2)
        self.assertFalse(dashboard.dashboard_subtitle.isHidden())
        self.assertEqual(
            dashboard.camera_frame.size().toTuple(),
            (min(608, max(320, dashboard.width() - 36)), 180),
        )
        self.assertEqual(dashboard.layout().contentsMargins().top(), 0)
        self.assertEqual(dashboard.layout().itemAt(0).layout().spacing(), 0)
        self.assertEqual(dashboard.cards_layout.horizontalSpacing(), 12)
        self.assertEqual(dashboard.cards_layout.verticalSpacing(), 12)
        for card in dashboard.cards:
            self.assertEqual(card.minimumHeight(), 112)
            self.assertEqual(card.layout().contentsMargins().left(), 14)
            self.assertEqual(card.layout().spacing(), 4)
            self.assertEqual(
                card.sizePolicy().verticalPolicy(),
                QSizePolicy.Policy.Fixed,
            )
        self.assertEqual(
            dashboard.camera_frame.sizePolicy().verticalPolicy(),
            QSizePolicy.Policy.Expanding,
        )
        self.assertEqual(dashboard.camera_container.width(), dashboard.width() - 20)
        live_size = dashboard.camera_frame.size()
        dashboard.camera_frame.setPixmap(QPixmap(640, 480))
        dashboard.update_camera_status("Camera is Off")
        self.assertEqual(dashboard.camera_frame.size(), live_size)
        self.assertEqual(
            dashboard.camera_container.layout()
            .itemAt(1)
            .layout()
            .contentsMargins()
            .bottom(),
            30,
        )
        frame_center = dashboard.camera_frame.mapTo(
            dashboard.camera_container,
            QPoint(dashboard.camera_frame.width() // 2, 0),
        ).x()
        self.assertAlmostEqual(frame_center, dashboard.camera_container.width() / 2)
        title = dashboard.findChild(QLabel, "page_title")
        self.assertLessEqual(
            dashboard.dashboard_subtitle.y(),
            title.y() + title.height() + 4,
        )
        self.assertEqual(
            dashboard.dashboard_subtitle.y(),
            title.y() + title.height(),
        )

        dashboard.camera_timer.stop()
        dashboard.arduino_timer.stop()
        scroll.close()

    def test_dashboard_shows_total_beans_as_fifth_evenly_spaced_card(self):
        dashboard = Dashboard()
        dashboard.resize(1100, 700)
        dashboard.update_responsive_layout()
        dashboard.show()
        self.application.processEvents()

        self.assertEqual(len(dashboard.cards), 5)
        self.assertEqual(dashboard.card_columns, 5)
        self.assertEqual(
            dashboard.cards_layout.count(),
            5,
        )
        total_beans_labels = [
            label
            for label in dashboard.cards[-1].findChildren(QLabel)
            if label.text() == "TOTAL BEANS"
        ]
        self.assertEqual(len(total_beans_labels), 1)
        self.assertEqual(
            dashboard.cards_layout.getItemPosition(4),
            (0, 4, 1, 1),
        )
        card_widths = [card.width() for card in dashboard.cards]
        self.assertLessEqual(max(card_widths) - min(card_widths), 4)
        dashboard.camera_timer.stop()
        dashboard.arduino_timer.stop()
        dashboard.close()

    def test_camera_usage_setting_only_controls_permission_until_user_starts_camera(self):
        dashboard = FakeDashboard()
        settings = SettingsPage(camera_controller=dashboard)
        button = settings.camera_usage_button

        self.assertTrue(button.isCheckable())
        self.assertTrue(button.isChecked())
        self.assertEqual(button.text(), "Camera Usage: Enabled")
        self.assertFalse(dashboard.camera_enabled)
        self.assertEqual(dashboard.camera_start_count, 0)

        button.click()
        self.assertFalse(dashboard.camera_usage_enabled)
        self.assertFalse(dashboard.camera_enabled)
        self.assertEqual(dashboard.camera_start_count, 0)
        self.assertEqual(button.text(), "Camera Usage: Disabled")

        button.click()
        self.assertTrue(dashboard.camera_usage_enabled)
        self.assertFalse(dashboard.camera_enabled)
        self.assertEqual(dashboard.camera_start_count, 0)
        self.assertEqual(button.text(), "Camera Usage: Enabled")

        dashboard.set_camera_usage_enabled(False)
        dashboard.start_camera()
        self.assertEqual(dashboard.camera_start_count, 0)
        settings.port_refresh_timer.stop()
        settings.close()

    def test_settings_displays_115200_baud_without_connected_controller(self):
        settings = SettingsPage()
        self.assertEqual(settings.baud_rate_input.text(), "115200")
        settings.port_refresh_timer.stop()
        settings.close()

    def test_settings_arduino_port_selection_updates_dashboard(self):
        dashboard = FakeDashboard()
        ports = [
            SimpleNamespace(device="COM3", description="Arduino Mega"),
            SimpleNamespace(device="COM4", description="USB Serial Device"),
        ]
        with patch("GUI.settings.list_ports.comports", return_value=ports):
            settings = SettingsPage(dashboard)

        self.assertEqual(dashboard.selected_arduino_port, "COM3")
        settings.arduino_port_input.setCurrentIndex(
            settings.arduino_port_input.findData("COM4")
        )
        self.assertEqual(dashboard.selected_arduino_port, "COM4")
        settings.port_refresh_timer.stop()
        settings.close()

    def test_camera_settings_capture_button_starts_camera_only_when_allowed(self):
        dashboard = FakeDashboard()
        page = CameraPage(camera_controller=dashboard)

        page.start_camera()
        self.assertEqual(dashboard.camera_start_count, 1)
        self.assertTrue(dashboard.camera_enabled)
        self.assertTrue(page.camera_timer.isActive())
        page.stop_camera()

        dashboard.set_camera_usage_enabled(False)
        with patch("GUI.camera.QMessageBox.warning") as warning:
            page.start_camera()
        self.assertEqual(dashboard.camera_start_count, 1)
        self.assertFalse(dashboard.camera_enabled)
        self.assertFalse(page.camera_timer.isActive())
        warning.assert_called_once()
        page.close()

    def test_as7265x_parser_preserves_missing_channels_as_no_data(self):
        readings = AS7265XReader.parse_line("410nm: 1.25, 460nm: 2.50")
        self.assertEqual(len(readings), len(WAVELENGTHS))
        self.assertEqual(readings[0].value, 1.25)
        self.assertEqual(readings[2].value, 2.50)
        self.assertIsNone(readings[1].value)
        self.assertEqual(readings[1].status, "NO DATA")

    def test_pricing_calculator_matches_weighted_price_formula(self):
        result = PricingSettingsPage.calculate_price(
            price_per_kilo=200,
            moisture_score=88,
            pns_score=90,
            weight_kg=5709,
            moisture_percent=50,
        )
        self.assertEqual(str(result["quality_score"]), "89.00")
        self.assertEqual(str(result["price_per_kilo"]), "178.00")
        self.assertEqual(str(result["total_price"]), "1016202.00")

    def test_pricing_calculator_requires_real_input_values(self):
        self.assertIsNone(
            PricingSettingsPage.calculate_price(
                price_per_kilo=200,
                moisture_score=None,
                pns_score=90,
                weight_kg=5709,
                moisture_percent=50,
            )
        )
        result_without_weight = PricingSettingsPage.calculate_price(
            price_per_kilo=200,
            moisture_score=88,
            pns_score=90,
            weight_kg=None,
            moisture_percent=50,
        )
        self.assertEqual(str(result_without_weight["price_per_kilo"]), "178.00")
        self.assertIsNone(result_without_weight["total_price"])

    def test_pricing_total_uses_unrounded_price_per_kilo(self):
        result = PricingSettingsPage.calculate_price(
            price_per_kilo=0.01,
            moisture_score=100,
            pns_score=0,
            weight_kg=1.5,
            moisture_percent=50,
        )
        self.assertEqual(str(result["price_per_kilo"]), "0.01")
        self.assertEqual(str(result["total_price"]), "0.01")

    def test_pns_grading_matches_each_table_grade_and_substandard_limits(self):
        cases = (
            (100, 3, 3, 3, 100, "1A"),
            (101, 3, 3, 3, 95, "1B"),
            (111, 3, 3, 3, 90, "1C"),
            (100, 4, 8, 6, 85, "2A"),
            (101, 4, 8, 6, 80, "2B"),
            (111, 4, 8, 6, 75, "2C"),
            (121, 0, 0, 0, 60, "Substandard"),
            (100, 4.01, 0, 0, 60, "Substandard"),
            (100, 3, 8.01, 0, 60, "Substandard"),
            (100, 3, 3, 6.01, 60, "Substandard"),
        )
        for count, moldy, slaty, defected, score, grade in cases:
            with self.subTest(
                count=count,
                moldy=moldy,
                slaty=slaty,
                defected=defected,
            ):
                self.assertEqual(
                    PricingSettingsPage.calculate_pns_grade(
                        count,
                        moldy,
                        slaty,
                        defected,
                    ),
                    {"score": score, "grade": grade},
                )

    def test_pns_grading_requires_complete_and_valid_sample_values(self):
        self.assertIsNone(
            PricingSettingsPage.calculate_pns_grade(100, None, 0, 0)
        )
        for values in (
            (0, 0, 0, 0),
            (100.5, 0, 0, 0),
            (100, -0.1, 0, 0),
            (100, 0, 0, 100.1),
        ):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    PricingSettingsPage.calculate_pns_grade(*values)

    def test_pricing_pns_score_is_calculated_from_sensor_and_ai_sample_data(self):
        page = PricingSettingsPage()
        self.assertTrue(page.pns_score_input.isReadOnly())
        self.assertEqual(page.pns_score_input.text(), "")
        self.assertEqual(page.pns_grade_label.text(), "")

        page.set_pns_sample_data(105, 4, 5, 4)
        self.assertEqual(page.pns_score_input.text(), "80")
        self.assertEqual(page.pns_grade_label.text(), "2B")
        self.assertIsNone(
            page.findChild(QLineEdit, "pricing_pns_bean_count_input")
        )
        with self.assertRaises(ValueError):
            page.set_pns_sample_data(100, 40, 40, 30)
        page.deleteLater()

    def test_pricing_score_weights_always_total_one_hundred_percent(self):
        pricing_page = PricingSettingsPage()
        self.assertEqual(
            pricing_page.total_price_result.text(),
            "",
        )
        self.assertEqual(
            pricing_page.moisture_contribution_result.text(),
            "",
        )
        self.assertEqual(
            pricing_page.pns_contribution_result.text(),
            "",
        )
        self.assertEqual(
            pricing_page.unit_price_result.text(),
            "",
        )
        self.assertEqual(pricing_page.weight_input.text(), "")
        self.assertTrue(pricing_page.weight_input.isReadOnly())
        self.assertEqual(pricing_page.weight_input.validator().decimals(), 3)
        self.assertEqual(
            pricing_page.weight_input.alignment(),
            pricing_page.moisture_score_input.alignment(),
        )
        self.assertEqual(
            pricing_page.weight_input.alignment(),
            pricing_page.pns_score_input.alignment(),
        )
        pricing_page.moisture_effect_slider.setValue(35)
        self.assertEqual(pricing_page.moisture_effect_label.text(), "35%")
        self.assertEqual(pricing_page.pns_effect_label.text(), "65%")
        pricing_page.base_price_input.setText("200")
        pricing_page.moisture_score_input.setText("88")
        pricing_page.set_pns_sample_data(115, 0, 0, 0)
        self.assertEqual(pricing_page.pns_score_input.text(), "90")
        self.assertEqual(pricing_page.moisture_contribution_result.text(), "30.80")
        self.assertEqual(pricing_page.pns_contribution_result.text(), "58.50")
        self.assertEqual(pricing_page.unit_price_result.text(), "₱ 178.60 / kg")
        self.assertEqual(
            {
                label.text()
                for label in pricing_page.findChildren(QLabel)
            }.intersection(
                {
                    "Overall Moisture Score",
                    "Overall PNS Score",
                    "Current Weight (kg)",
                    "Price Per Kilo",
                }
            ),
            {
                "Overall Moisture Score",
                "Overall PNS Score",
                "Current Weight (kg)",
                "Price Per Kilo",
            },
        )
        self.assertNotIn(
            "Weighted quality score",
            {label.text() for label in pricing_page.findChildren(QLabel)},
        )
        self.assertEqual(pricing_page.total_price_result.text(), "")
        pricing_page.set_current_weight(1)
        pricing_page.save_inputs_button.click()
        self.assertEqual(pricing_page.total_price_result.text(), "₱ 178.60")
        pricing_page.deleteLater()

    def test_pricing_page_updates_from_entered_values(self):
        page = PricingSettingsPage()
        page.base_price_input.setText("200")
        page.moisture_score_input.setText("88")
        page.set_pns_sample_data(115, 0, 0, 0)
        weight_kg = Dashboard.parse_load_cell_weight_kg(
            "Load Cell 1: 125.00 g | Load Cell 2: 125.00 g"
        )
        page.set_current_weight(weight_kg)
        self.assertEqual(page.weight_input.text(), "0.250")
        page.set_current_weight(None)
        self.assertEqual(page.unit_price_result.text(), "₱ 178.00 / kg")
        self.assertEqual(page.total_price_result.text(), "")
        page.save_inputs_button.click()
        self.assertEqual(page.total_price_result.text(), "")
        page.set_current_weight(1)
        self.assertEqual(page.total_price_result.text(), "₱ 178.00")
        page.base_price_input.setText("250")
        self.assertEqual(page.total_price_result.text(), "₱ 222.50")
        page.set_current_weight(2)
        self.assertEqual(page.total_price_result.text(), "₱ 445.00")
        page.moisture_effect_slider.setValue(35)
        self.assertEqual(page.unit_price_result.text(), "₱ 223.25 / kg")
        self.assertEqual(page.total_price_result.text(), "₱ 446.50")
        page.set_current_weight(None)
        self.assertEqual(page.weight_input.text(), "")
        self.assertEqual(page.total_price_result.text(), "")
        page.deleteLater()

    def test_pricing_score_and_weight_fields_accept_typed_decimal_values(self):
        page = PricingSettingsPage()
        page.base_price_input.setText("200.75")
        page.moisture_score_input.setText("88.5")
        page.set_pns_sample_data(115, 0, 0, 0)
        page.set_current_weight(2.5)
        self.assertEqual(page.base_price_input.text(), "200.75")
        self.assertEqual(page.base_price_input.validator().decimals(), 2)
        self.assertEqual(page.weight_input.text(), "2.500")
        self.assertEqual(page.weight_input.validator().decimals(), 3)
        self.assertEqual(
            page.moisture_score_input.validator().decimals(),
            2,
        )
        self.assertEqual(page.pns_score_input.text(), "90")
        self.assertEqual(page.unit_price_result.text(), "₱ 179.17 / kg")
        self.assertEqual(page.total_price_result.text(), "")
        page.save_inputs_button.click()
        self.assertEqual(page.total_price_result.text(), "₱ 447.92")
        page.deleteLater()

    def test_pricing_total_is_not_shown_when_scores_are_missing(self):
        page = PricingSettingsPage()
        page.base_price_input.setText("200")
        self.assertEqual(
            page.total_price_result.text(),
            "",
        )
        page.save_inputs_button.click()
        self.assertEqual(
            page.total_price_result.text(),
            "",
        )
        page.deleteLater()

    def test_pricing_result_has_clear_total_card_and_quiet_calibration_controls(self):
        page = PricingSettingsPage()
        self.assertIsNotNone(
            page.findChild(QWidget, "pricing_total_card")
        )
        self.assertGreaterEqual(
            len(page.findChildren(QWidget, "pricing_result_row")),
            3,
        )
        self.assertTrue(page.calibration_prompt_label.isHidden())
        self.assertTrue(page.calibration_continue_button.isHidden())
        page.set_arduino_status(
            "Connected on COM7; waiting for Arduino sensor readings."
        )
        self.assertTrue(page.arduino_status_label.isHidden())
        self.assertEqual(page.arduino_status_label.text(), "")
        page.set_arduino_status("Live load-cell reading: 2.000 kg")
        self.assertEqual(
            page.arduino_status_label.property("status_state"),
            "connected",
        )
        self.assertEqual(
            page.arduino_status_label.text(),
            "Load cells connected",
        )
        page.update_calibration_prompt("Send C to tare.")
        self.assertFalse(page.calibration_prompt_label.isHidden())
        self.assertFalse(page.calibration_continue_button.isHidden())
        page.deleteLater()

    def test_bean_data_current_summary_values_start_blank(self):
        page = BeanDataSheetPage()
        expected_titles = {
            "Current Bean Number",
            "Current PNS Sample Number",
            "Current Good Bean Number",
            "Current Weight",
            "PNS Grade Summary",
            "Moisture Content Grade Summary",
        }
        current_values = {}
        for card in page.findChildren(QWidget, "bean_sheet_summary_card"):
            labels = card.findChildren(QLabel)
            title = next(
                label.text()
                for label in labels
                if label.objectName()
                in {
                    "bean_sheet_summary_title",
                    "bean_sheet_current_label",
                }
            )
            value = next(
                label.text()
                for label in labels
                if label.objectName()
                in {
                    "bean_sheet_summary_value",
                    "bean_sheet_current_value",
                }
            )
            if title in expected_titles:
                current_values[title] = value
        self.assertEqual(current_values, {title: "" for title in expected_titles})
        self.assertFalse(page.empty_state.isVisible())
        self.assertEqual(page.empty_state.text(), "")
        page.deleteLater()

    def test_bean_data_tables_update_from_dashboard_metrics(self):
        page = BeanDataSheetPage()
        page.update_dashboard_metrics(
            {
                "bean_id": "202610260001",
                "bean_count": 1,
                "batch_weight_grams": 125.5,
                "moisture": None,
                "quality": "GOOD",
            }
        )
        self.assertEqual(page.current_bean_number_value.text(), "1")

        table = page.data_table
        self.assertEqual(table.rowCount(), 1)
        self.assertEqual(table.item(0, 0).text(), "202610260001")
        self.assertEqual(table.item(0, 1).text(), "125.50")
        self.assertEqual(table.item(0, 2).text(), "1")
        self.assertEqual(table.item(0, 4).text(), "GOOD")
        self.assertEqual(table.item(0, 5).text(), "100.00%")

        page.show_table("PNS Grade Sample")
        self.assertEqual(page.data_table.rowCount(), 1)
        self.assertEqual(page.data_table.item(0, 3).text(), "1")
        self.assertEqual(page.data_table.item(0, 4).text(), "1")
        self.assertEqual(page.data_table.item(0, 2).text(), "1A")
        self.assertEqual(page.data_table.item(0, 8).text(), "100")

        page.update_dashboard_metrics(
            {
                "bean_id": "202610260002",
                "bean_count": 2,
                "batch_weight_grams": 251.0,
                "moisture": None,
                "quality": "MOLDY",
            }
        )
        self.assertEqual(page.current_bean_number_value.text(), "2")
        self.assertEqual(page.data_table.rowCount(), 2)
        self.assertEqual(page.data_table.item(1, 0).text(), "202610260002")
        self.assertEqual(page.data_table.item(1, 3).text(), "2")
        self.assertEqual(page.data_table.item(1, 2).text(), "Substandard")
        self.assertEqual(page.data_table.item(1, 4).text(), "1")
        self.assertEqual(page.data_table.item(1, 5).text(), "1")
        self.assertEqual(page.data_table.item(1, 8).text(), "60")

        page.show_table("Beans in 100g Sample")
        self.assertEqual(page.data_table.item(0, 5).text(), "100.00%")
        self.assertEqual(page.data_table.item(0, 6).text(), "0.00%")
        self.assertEqual(page.data_table.item(0, 8).text(), "0.00%")
        self.assertEqual(page.data_table.item(1, 5).text(), "0.00%")
        self.assertEqual(page.data_table.item(1, 6).text(), "100.00%")
        self.assertEqual(page.data_table.item(1, 8).text(), "0.00%")

        page.update_dashboard_metrics(
            {
                "bean_id": "202610260003",
                "bean_count": 3,
                "batch_weight_grams": 376.5,
                "moisture": None,
                "quality": "INSECT-DAMAGED",
            }
        )
        self.assertEqual(page.data_table.item(2, 4).text(), "INSECT-DAMAGED")
        self.assertEqual(page.data_table.item(2, 8).text(), "100.00%")

        page.update_dashboard_metrics(
            {
                "bean_id": "0" * 12,
                "bean_count": 0,
                "batch_weight_grams": None,
                "moisture": None,
                "quality": "UNDEFINED",
            }
        )
        self.assertEqual(page.current_bean_number_value.text(), "0")
        page.show_table("PNS Grade Sample")
        self.assertEqual(page.data_table.rowCount(), 3)
        self.assertEqual(page.data_table.item(0, 0).text(), "202610260001")

        page.show_table("Moisture Content Sample")
        self.assertEqual(page.data_table.rowCount(), 3)
        self.assertEqual(page.data_table.item(0, 0).text(), "202610260001")
        self.assertEqual(page.data_table.item(0, 1).text(), "--")
        page.deleteLater()

    def test_quality_counts_include_foreign_objects_and_germinated_beans_as_defects(self):
        records = [
            {"quality": "FOREIGN-OBJECT"},
            {"quality": "GERMINATED"},
            {"quality": "SLATY"},
        ]

        self.assertEqual(
            BeanDataSheetPage._quality_counts(records),
            {
                "GOOD": 0,
                "MOLDY": 0,
                "SLATY": 1,
                "DEFECTIVE": 2,
            },
        )

    def test_admin_panel_reuses_dashboard_and_blocks_commands_after_logout(self):
        session = AdminSession()
        session.grant_admin()
        dashboard = FakeDashboard()
        panel = AdminControlPanel(dashboard, session)
        self.assertIs(panel.dashboard, dashboard)
        self.assertFalse(hasattr(panel, "pricing_page"))
        self.assertEqual(
            panel.SECTION_NAMES[:3],
            ("System Overview", "Camera", "NIR Analysis"),
        )
        self.assertEqual(panel.stack.count(), len(panel.SECTION_NAMES))
        self.assertNotIn("Servo Control", panel.SECTION_NAMES)
        self.assertFalse(hasattr(panel, "servo_page"))
        self.assertEqual(dashboard.commands, [])
        self.assertEqual(len(panel.admin_scroll_areas), 7)
        self.assertTrue(panel.navigation_buttons[-1].isHidden())
        overview = panel.admin_scroll_areas[0].widget()
        self.assertEqual(
            overview.status_values["Camera"].text(),
            "NOT CONNECTED",
        )
        self.assertEqual(
            overview.status_values["AI Model"].text(),
            "NOT READY",
        )
        self.assertEqual(
            overview.status_values["Load Cell"].text(),
            "NOT CONNECTED",
        )
        self.assertNotIn("Infrared Sensor", overview.status_values)
        dashboard.arduino_connected = True
        overview.refresh_status()
        dashboard.ir_sensor_connected = True
        dashboard.ir_sensor_status_changed.emit(True)
        dashboard.ir_sensor_connected = False
        dashboard.ir_sensor_status_changed.emit(False)
        dashboard.ir_sensor_connected = True
        overview.refresh_status()
        dashboard.ir_batch_active = True
        overview.refresh_status()
        dashboard.ir_batch_active = False
        dashboard.current_weight_kg = 1.25
        overview.refresh_status()
        self.assertEqual(
            overview.status_values["Load Cell"].text(),
            "CONNECTED",
        )
        self.assertEqual(
            overview.status_values["Load Cell"].property("connection_state"),
            "connected",
        )
        dashboard.current_weight_kg = None
        overview.refresh_status()
        self.assertEqual(
            overview.status_values["Load Cell"].text(),
            "NOT CONNECTED",
        )
        dashboard.camera_connected = True
        overview.refresh_status()
        self.assertEqual(
            overview.status_values["Camera"].text(),
            "CONNECTED",
        )
        self.assertEqual(
            overview.status_values["Camera"].property("connection_state"),
            "connected",
        )
        panel.change_page(panel.SECTION_NAMES.index("Create Admin Account"))
        self.assertNotEqual(
            panel.stack.currentIndex(),
            panel.SECTION_NAMES.index("Create Admin Account"),
        )
        account_page = panel.stack.widget(
            panel.SECTION_NAMES.index("Create Admin Account")
        ).widget()
        account_page.username_input.setText("unauthorized")
        account_page.password_input.setText("secure-admin-password")
        account_page.create_button.click()
        self.assertEqual(
            account_page.status_label.text(),
            "Only the Super Admin can create admin accounts.",
        )
        for scroll in panel.admin_scroll_areas:
            self.assertTrue(scroll.autoFillBackground())
            self.assertTrue(scroll.viewport().autoFillBackground())
            self.assertEqual(
                scroll.viewport().palette().color(
                    scroll.viewport().backgroundRole()
                ).name(),
                "#f4f6f8",
            )

        session.revoke()
        self.assertFalse(
            panel.settings_page.set_nir_scan_delay(250)
        )
        panel.deleteLater()

    def test_super_admin_can_create_admin_with_username_and_password_only(self):
        with tempfile.TemporaryDirectory() as folder:
            credentials = AdminCredentials(
                Path(folder) / "admin_credentials.json"
            )
            credentials.ensure_default_super_admin()
            session = AdminSession()
            session.grant_admin("admin", SUPER_ADMIN_ROLE, "Super Admin")
            panel = AdminControlPanel(
                FakeDashboard(),
                session,
                credentials,
            )
            account_page = panel.stack.widget(
                panel.SECTION_NAMES.index("Create Admin Account")
            ).widget()

            account_page.username_input.setText("operator")
            account_page.password_input.setText("secure-admin-password")
            self.assertEqual(
                account_page.password_input.echoMode(),
                QLineEdit.EchoMode.Password,
            )
            account_page.show_password_checkbox.click()
            self.assertEqual(
                account_page.password_input.echoMode(),
                QLineEdit.EchoMode.Normal,
            )
            account_page.show_password_checkbox.click()
            self.assertEqual(
                account_page.password_input.echoMode(),
                QLineEdit.EchoMode.Password,
            )
            account_page.create_button.click()

            self.assertEqual(
                credentials.authenticate("operator", "secure-admin-password")[
                    "role"
                ],
                "admin",
            )
            self.assertEqual(account_page.username_input.text(), "")
            self.assertEqual(account_page.password_input.text(), "")
            self.assertEqual(
                account_page.status_label.text(),
                "Admin account 'operator' created.",
            )
            self.assertEqual(account_page.account_cards_layout.count(), 2)
            account_card = next(
                account_page.account_cards_layout.itemAt(index).widget()
                for index in range(account_page.account_cards_layout.count())
                if account_page.account_cards_layout.itemAt(index)
                .widget()
                .findChild(QLabel, "admin_account_username")
                .text()
                == "operator"
            )
            self.assertIsNotNone(
                account_card.findChild(QWidget, "admin_account_toggle_button")
            )
            self.assertIsNotNone(
                account_card.findChild(QWidget, "admin_account_delete_button")
            )
            self.assertIsNotNone(
                account_card.findChild(
                    QWidget, "admin_account_reset_password_button"
                )
            )

            with patch(
                "GUI.admin_panel.AdminPasswordResetDialog"
            ) as reset_dialog:
                reset_dialog.return_value.exec.return_value = (
                    QDialog.DialogCode.Accepted
                )
                reset_dialog.return_value.password = "new-admin-password"
                account_page.reset_admin_password("operator")
            self.assertIsNone(
                credentials.authenticate("operator", "secure-admin-password")
            )
            self.assertIsNotNone(
                credentials.authenticate("operator", "new-admin-password")
            )
            self.assertIn(
                "was reset",
                account_page.status_label.text().lower(),
            )

            account_card = next(
                account_page.account_cards_layout.itemAt(index).widget()
                for index in range(account_page.account_cards_layout.count())
                if account_page.account_cards_layout.itemAt(index)
                .widget()
                .findChild(QLabel, "admin_account_username")
                .text()
                == "operator"
            )
            account_card.findChild(
                QWidget, "admin_account_toggle_button"
            ).click()
            self.assertFalse(
                credentials.authenticate("operator", "new-admin-password")
            )
            self.assertIn("disabled", account_page.status_label.text())

            account_card = next(
                account_page.account_cards_layout.itemAt(index).widget()
                for index in range(account_page.account_cards_layout.count())
                if account_page.account_cards_layout.itemAt(index)
                .widget()
                .findChild(QLabel, "admin_account_username")
                .text()
                == "operator"
            )
            account_card.findChild(
                QWidget, "admin_account_toggle_button"
            ).click()
            self.assertIsNotNone(
                credentials.authenticate("operator", "new-admin-password")
            )
            with patch(
                "GUI.admin_panel.QMessageBox.exec",
                return_value=QMessageBox.StandardButton.Yes,
            ):
                account_card = next(
                    account_page.account_cards_layout.itemAt(index).widget()
                    for index in range(account_page.account_cards_layout.count())
                    if account_page.account_cards_layout.itemAt(index)
                    .widget()
                    .findChild(QLabel, "admin_account_username")
                    .text()
                    == "operator"
                )
                account_card.findChild(
                    QWidget, "admin_account_delete_button"
                ).click()
            self.assertIsNone(
                credentials.authenticate("operator", "new-admin-password")
            )
            self.assertEqual(account_page.account_cards_layout.count(), 1)
            panel.deleteLater()

    def test_create_admin_navigation_updates_when_panel_is_reused_by_admin(self):
        with tempfile.TemporaryDirectory() as folder:
            credentials = AdminCredentials(
                Path(folder) / "admin_credentials.json"
            )
            credentials.ensure_default_super_admin()
            session = AdminSession()
            session.grant_admin("admin", SUPER_ADMIN_ROLE, "Super Admin")
            panel = AdminControlPanel(FakeDashboard(), session, credentials)
            create_admin_index = panel.SECTION_NAMES.index(
                "Create Admin Account"
            )
            create_admin_button = panel.navigation_buttons[create_admin_index]
            self.assertFalse(create_admin_button.isHidden())

            session.grant_admin("operator", "admin", "Operator")
            panel.activate_admin_view()
            self.assertTrue(create_admin_button.isHidden())
            panel.change_page(create_admin_index)
            self.assertNotEqual(panel.stack.currentIndex(), create_admin_index)

            session.grant_admin("admin", SUPER_ADMIN_ROLE, "Super Admin")
            panel.activate_admin_view()
            self.assertFalse(create_admin_button.isHidden())
            panel.deleteLater()

    def test_admin_password_reset_dialog_allows_viewing_typed_new_password(self):
        self.application.setStyleSheet(APP_STYLE)
        dialog = AdminPasswordResetDialog("operator")
        dialog.show()
        self.application.processEvents()
        self.assertEqual(
            dialog.grab().toImage().pixelColor(2, 2).name(),
            "#ffffff",
        )
        self.assertEqual(
            dialog.password_input.echoMode(),
            QLineEdit.EchoMode.Password,
        )
        dialog.password_input.setText("new")
        dialog.show_password_checkbox.click()
        self.assertEqual(
            dialog.password_input.echoMode(),
            QLineEdit.EchoMode.Normal,
        )
        self.assertEqual(dialog.password, "new")
        dialog.close()

    def test_login_show_password_uses_native_check_indicator_and_reveals_password(self):
        with tempfile.TemporaryDirectory() as folder:
            credentials = AdminCredentials(
                Path(folder) / "admin_credentials.json"
            )
            credentials.ensure_default_super_admin()
            dialog = AdminLoginDialog(credentials)
            self.assertEqual(dialog.username_input.text(), "")
            dialog.password_input.setText("secret")

            self.assertEqual(
                dialog.password_input.echoMode(),
                QLineEdit.EchoMode.Password,
            )
            dialog.show_password_checkbox.resize(150, 24)
            unchecked_image = dialog.show_password_checkbox.grab().toImage()
            outline_pixels = sum(
                1
                for y in range(unchecked_image.height())
                for x in range(min(18, unchecked_image.width()))
                if unchecked_image.pixelColor(x, y).red() < 100
            )
            self.assertGreaterEqual(outline_pixels, 20)
            dialog.show_password_checkbox.click()
            self.assertEqual(
                dialog.password_input.echoMode(),
                QLineEdit.EchoMode.Normal,
            )
            checked_image = dialog.show_password_checkbox.grab().toImage()
            self.assertTrue(
                any(
                    unchecked_image.pixel(x, y) != checked_image.pixel(x, y)
                    for y in range(unchecked_image.height())
                    for x in range(unchecked_image.width())
                )
            )
            self.assertNotIn("QCheckBox#admin_show_password_checkbox::indicator", APP_STYLE)
            self.assertNotIn("QCheckBox#create_admin_show_password_checkbox::indicator", APP_STYLE)
            dialog.close()

    def test_system_status_tracks_arduino_not_camera(self):
        with patch("GUI.main_window.Dashboard", FakeDashboard):
            window = MainWindow()

        self.assertEqual(window.status_text.text(), "SYSTEM NOT CONNECTED")
        window.dashboard_page.arduino_connected = True
        window.dashboard_page.arduino_connection_changed.emit(True)
        self.assertEqual(window.status_text.text(), "SYSTEM CONNECTED")
        window.dashboard_page.camera_status_changed.emit("NOT CONNECTED")
        self.assertEqual(window.status_text.text(), "SYSTEM CONNECTED")

    def test_normal_window_starts_on_dashboard_and_denies_admin_routes(self):
        with patch("GUI.main_window.Dashboard", FakeDashboard):
            window = MainWindow()
        self.assertTrue(window.pricing_page.arduino_status_label.isHidden())
        self.assertEqual(window.pricing_page.arduino_status_label.text(), "")
        window.dashboard_page.current_weight_changed.emit(2.0)
        self.assertEqual(window.pricing_page.weight_input.text(), "2.000")
        window.dashboard_page.arduino_status_changed.emit(
            "Live load-cell reading: 2.000 kg"
        )
        self.assertEqual(
            window.pricing_page.arduino_status_label.text(),
            "Live load-cell reading: 2.000 kg",
        )
        window.dashboard_page.nir_message_received.emit(
            "Send C to tare."
        )
        self.assertTrue(
            window.pricing_page.calibration_continue_button.isEnabled()
        )
        window.pricing_page.calibration_continue_button.click()
        self.assertFalse(
            window.pricing_page.calibration_continue_button.isEnabled()
        )
        self.assertIn(
            ("calibration-continue",),
            window.dashboard_page.commands,
        )
        self.assertEqual(window.pages.currentIndex(), 0)
        self.assertFalse(
            hasattr(window, "camera_toggle_button"),
            "Normal dashboard must not expose the camera power control.",
        )
        self.assertEqual(
            window.pages.count(),
            3,
            "Normal navigation should contain Dashboard, Pricing Settings, and Bean Data Sheet.",
        )
        self.assertFalse(hasattr(window, "camera_page"))
        self.assertFalse(hasattr(window, "nir_page"))
        self.assertTrue(hasattr(window, "pricing_page"))
        self.assertIsNone(window.admin_panel)
        self.assertEqual(window.dashboard_page.camera_start_count, 0)
        self.assertEqual(len(window.menu_buttons), 3)
        self.assertEqual(
            window.menu_buttons[0].text().strip(),
            "Dashboard",
        )
        self.assertEqual(
            window.menu_buttons[1].text().strip(),
            "Pricing Settings",
        )
        self.assertEqual(
            window.menu_buttons[2].text().strip(),
            "Bean Data Sheet",
        )
        window.dashboard_page.start_system_button.click()
        self.assertEqual(window.dashboard_page.camera_start_count, 1)
        window.dashboard_page.stop_system_button.click()
        self.assertEqual(window.dashboard_page.camera_stop_count, 1)
        summary_area = window.bean_data_sheet_page.layout().itemAt(2).layout()
        self.assertIsInstance(summary_area, QHBoxLayout)
        current_summary_column = summary_area.itemAt(0).layout()
        grading_summary_row = summary_area.itemAt(1).layout()
        self.assertIsInstance(current_summary_column, QVBoxLayout)
        self.assertIsInstance(grading_summary_row, QHBoxLayout)
        self.assertEqual(current_summary_column.count(), 4)
        self.assertEqual(grading_summary_row.count(), 2)
        window.change_page(1)
        self.assertEqual(window.pages.currentIndex(), 1)
        window.change_page(2)
        self.assertEqual(window.pages.currentIndex(), 2)
        self.assertEqual(
            window.bean_data_sheet_page.data_table.columnCount(),
            9,
        )
        self.assertEqual(
            [
                window.bean_data_sheet_page.data_table.horizontalHeaderItem(i).text()
                for i in range(
                    window.bean_data_sheet_page.data_table.columnCount()
                )
            ],
            [
                "Bean ID",
                "Accumulated Weight",
                "Bean Count",
                "PNS Sample ID",
                "Condition",
                "Good (%)",
                "Moldy (%)",
                "Slaty (%)",
                "Defective (%)",
            ],
        )
        header = window.bean_data_sheet_page.data_table.horizontalHeader()
        for column in range(
            window.bean_data_sheet_page.data_table.columnCount()
        ):
            self.assertEqual(
                header.sectionResizeMode(column),
                QHeaderView.ResizeMode.Stretch,
            )
        weight_header = window.bean_data_sheet_page.data_table.horizontalHeaderItem(1)
        self.assertLess(weight_header.font().pointSizeF(), 10)
        window.bean_data_sheet_page.show_table("PNS Grade Sample")
        self.assertEqual(
            window.bean_data_sheet_page.data_table.columnCount(),
            9,
        )
        self.assertEqual(window.bean_data_sheet_page.data_table.rowCount(), 0)
        window.bean_data_sheet_page.show_table("Moisture Content Sample")
        self.assertEqual(
            [
                window.bean_data_sheet_page.data_table.horizontalHeaderItem(i).text()
                for i in range(
                    window.bean_data_sheet_page.data_table.columnCount()
                )
            ],
            [
                "Good Bean ID",
                "Moisture Content",
                "Moisture Grade",
                "Moisture Score",
            ],
        )
        self.assertEqual(window.bean_data_sheet_page.data_table.rowCount(), 0)
        for title in ("Beans in 100g Sample", "PNS Grade Sample"):
            window.bean_data_sheet_page.show_table(title)
            header = window.bean_data_sheet_page.data_table.horizontalHeader()
            for column in range(window.bean_data_sheet_page.data_table.columnCount()):
                self.assertEqual(
                    header.sectionResizeMode(column),
                    QHeaderView.ResizeMode.Stretch,
                )
        window.change_page(3)
        self.assertEqual(window.pages.currentIndex(), 2)
        window.close()
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()

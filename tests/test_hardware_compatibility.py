import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
    system_log_received = Signal(str)
    nir_message_received = Signal(str)
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
        self.arduino_status_message = "Arduino not detected."
        self.current_weight_kg = None
        self.arduino_serial = None
        self.arduino_baud_rate = 115200
        self.camera_source = 0
        self.nir_scan_delay_ms = 0
        self.nir_detected = False
        self.nir_connected = False
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

    def set_nir_scanning(self, enabled):
        self.commands.append(("scan", enabled))

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
            description="USB Serial Device",
            manufacturer="Arduino",
            product="",
            hwid="USB VID:PID",
        )
        unrelated = SimpleNamespace(
            description="Bluetooth Adapter",
            manufacturer="",
            product="",
            hwid="",
        )
        self.assertTrue(Dashboard.is_arduino_port(arduino))
        self.assertFalse(Dashboard.is_arduino_port(unrelated))

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

    def test_pricing_score_weights_always_total_one_hundred_percent(self):
        pricing_page = PricingSettingsPage()
        self.assertEqual(
            pricing_page.total_price_result.text(),
            "0",
        )
        self.assertEqual(
            pricing_page.moisture_contribution_result.text(),
            "0",
        )
        self.assertEqual(
            pricing_page.pns_contribution_result.text(),
            "0",
        )
        self.assertEqual(
            pricing_page.unit_price_result.text(),
            "0",
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
        pricing_page.pns_score_input.setText("90")
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
        self.assertEqual(pricing_page.total_price_result.text(), "0")
        pricing_page.set_current_weight(1)
        pricing_page.save_inputs_button.click()
        self.assertEqual(pricing_page.total_price_result.text(), "₱ 178.60")
        pricing_page.deleteLater()

    def test_pricing_page_updates_from_entered_values(self):
        page = PricingSettingsPage()
        page.base_price_input.setText("200")
        page.moisture_score_input.setText("88")
        page.pns_score_input.setText("90")
        weight_kg = Dashboard.parse_load_cell_weight_kg(
            "Load Cell 1: 125.00 g | Load Cell 2: 125.00 g"
        )
        page.set_current_weight(weight_kg)
        self.assertEqual(page.weight_input.text(), "0.250")
        page.set_current_weight(None)
        self.assertEqual(page.unit_price_result.text(), "₱ 178.00 / kg")
        self.assertEqual(page.total_price_result.text(), "0")
        page.save_inputs_button.click()
        self.assertEqual(page.total_price_result.text(), "0")
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
        self.assertEqual(page.total_price_result.text(), "0")
        page.deleteLater()

    def test_pricing_score_and_weight_fields_accept_typed_decimal_values(self):
        page = PricingSettingsPage()
        page.base_price_input.setText("200.75")
        page.moisture_score_input.setText("88.5")
        page.pns_score_input.setText("90.25")
        page.set_current_weight(2.5)
        self.assertEqual(page.base_price_input.text(), "200.75")
        self.assertEqual(page.base_price_input.validator().decimals(), 2)
        self.assertEqual(page.weight_input.text(), "2.500")
        self.assertEqual(page.weight_input.validator().decimals(), 3)
        self.assertEqual(
            page.moisture_score_input.validator().decimals(),
            2,
        )
        self.assertEqual(page.pns_score_input.text(), "90.25")
        self.assertEqual(page.unit_price_result.text(), "₱ 179.42 / kg")
        self.assertEqual(page.total_price_result.text(), "0")
        page.save_inputs_button.click()
        self.assertEqual(page.total_price_result.text(), "₱ 448.55")
        page.deleteLater()

    def test_pricing_total_is_not_shown_when_scores_are_missing(self):
        page = PricingSettingsPage()
        page.base_price_input.setText("200")
        self.assertEqual(
            page.total_price_result.text(),
            "0",
        )
        page.save_inputs_button.click()
        self.assertEqual(
            page.total_price_result.text(),
            "Enter valid inputs to calculate",
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
                if label.objectName() == "bean_sheet_summary_title"
            )
            value = next(
                label.text()
                for label in labels
                if label.objectName() == "bean_sheet_summary_value"
            )
            if title in expected_titles:
                current_values[title] = value
        self.assertEqual(current_values, {title: "" for title in expected_titles})
        self.assertFalse(page.empty_state.isVisible())
        self.assertEqual(page.empty_state.text(), "")
        page.deleteLater()

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

    def test_normal_window_starts_on_dashboard_and_denies_admin_routes(self):
        with patch("GUI.main_window.Dashboard", FakeDashboard):
            window = MainWindow()
        self.assertEqual(
            window.pricing_page.arduino_status_label.text(),
            "Arduino not detected.",
        )
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

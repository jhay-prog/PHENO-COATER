import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from GUI.admin_panel import AdminControlPanel, AdminPasswordResetDialog
from GUI.admin_login import AdminLoginDialog
from GUI.auth import AdminCredentials, AdminSession, SUPER_ADMIN_ROLE
from GUI.dashboard import Dashboard
from GUI.main_window import MainWindow
from GUI.pricing import PricingSettingsPage
from GUI.styles import APP_STYLE
from NIR.as7265x import AS7265XReader, WAVELENGTHS


class FakeDashboard(QWidget):
    camera_status_changed = Signal(str)
    system_log_received = Signal(str)
    nir_message_received = Signal(str)
    servo_status_received = Signal(int, int)
    servo_sweep_status_received = Signal(int, bool)

    def __init__(self):
        super().__init__()
        self.camera_enabled = False
        self.camera_capture = None
        self.arduino_serial = None
        self.arduino_baud_rate = 115200
        self.camera_source = 0
        self.nir_scan_delay_ms = 0
        self.nir_detected = False
        self.nir_scanning = False
        self.servo_sweeping = {1: False, 2: False}
        self.camera_button = None
        self.commands = []

    def set_camera_toggle_button(self, button):
        self.camera_button = button

    def toggle_camera(self):
        pass

    def update_responsive_layout(self):
        pass

    @staticmethod
    def is_arduino_port(port):
        return Dashboard.is_arduino_port(port)

    def set_nir_scanning(self, enabled):
        self.commands.append(("scan", enabled))

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

    def test_pricing_score_weights_always_total_one_hundred_percent(self):
        pricing_page = PricingSettingsPage()
        self.assertEqual(
            pricing_page.total_price_result.text(),
            "—",
        )
        pricing_page.moisture_effect_slider.setValue(35)
        self.assertEqual(pricing_page.moisture_effect_label.text(), "35%")
        self.assertEqual(pricing_page.pns_effect_label.text(), "65%")
        pricing_page.deleteLater()

    def test_pricing_page_updates_from_entered_values(self):
        page = PricingSettingsPage()
        page.base_price_input.setValue(200)
        page.moisture_score_input.setValue(88)
        page.pns_score_input.setValue(90)
        page.weight_input.setValue(5709)
        self.assertEqual(page.quality_result.text(), "89.00%")
        self.assertEqual(page.unit_price_result.text(), "P 178.00 / kg")
        self.assertEqual(
            page.total_price_result.text(),
            "P 1,016,202.00",
        )
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
        self.assertEqual(dashboard.commands, [])
        self.assertEqual(len(panel.admin_scroll_areas), 8)
        self.assertTrue(panel.navigation_buttons[-1].isHidden())
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

        panel._set_servo_angle(1, 90)
        self.assertEqual(dashboard.commands, [("angle", 1, 90)])

        session.revoke()
        panel._set_servo_angle(1, 120)
        self.assertEqual(dashboard.commands, [("angle", 1, 90)])
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
        self.assertEqual(window.pages.currentIndex(), 0)
        self.assertFalse(
            hasattr(window, "camera_toggle_button"),
            "Normal dashboard must not expose the camera power control.",
        )
        self.assertEqual(
            window.pages.count(),
            2,
            "Normal navigation should contain Dashboard and Pricing Settings.",
        )
        self.assertFalse(hasattr(window, "camera_page"))
        self.assertFalse(hasattr(window, "nir_page"))
        self.assertTrue(hasattr(window, "pricing_page"))
        self.assertIsNone(window.admin_panel)
        self.assertEqual(len(window.menu_buttons), 2)
        self.assertEqual(
            window.menu_buttons[0].text().strip(),
            "Dashboard",
        )
        self.assertEqual(
            window.menu_buttons[1].text().strip(),
            "Pricing Settings",
        )
        window.change_page(1)
        self.assertEqual(window.pages.currentIndex(), 1)
        window.change_page(3)
        self.assertEqual(window.pages.currentIndex(), 1)
        window.close()
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()

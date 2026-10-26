import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QPushButton,
)

try:
    from .admin_login import AdminLoginDialog
    from .admin_panel import AdminControlPanel
    from .animated_button import AnimatedButton
    from .auth import AdminCredentials, AdminSession, AuthStorageError
    from .bean_data_sheet import BeanDataSheetPage
    from .dashboard import Dashboard
    from .pricing import PricingSettingsPage
except ImportError:
    from admin_login import AdminLoginDialog
    from admin_panel import AdminControlPanel
    from animated_button import AnimatedButton
    from auth import AdminCredentials, AdminSession, AuthStorageError
    from bean_data_sheet import BeanDataSheetPage
    from dashboard import Dashboard
    from pricing import PricingSettingsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.admin_credentials = AdminCredentials()
        self.admin_credentials.ensure_default_super_admin()
        self.admin_session = AdminSession()
        self.admin_panel = None
        self.setWindowTitle('PhenoCoater - Cacao Seed Sorting & Grading System')
        self.resize(1400, 850)
        self.setMinimumSize(640, 480)
        self.setup_ui()
        self.dashboard_page.start_system_button.clicked.connect(
            self.dashboard_page.start_system
        )
        self.dashboard_page.stop_system_button.clicked.connect(
            self.dashboard_page.stop_system
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'dashboard_page'):
            QTimer.singleShot(0, self.dashboard_page.update_responsive_layout)

    def setup_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName('central_widget')
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 14, 8, 12)
        sidebar_layout.setSpacing(5)

        logo_title = QLabel('PHENOCOATER')
        logo_title.setObjectName('logo_title')
        logo_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo_title)

        logo_subtitle = QLabel('Cacao Seed Sorting' + '\n' + '& Grading System')
        logo_subtitle.setObjectName('logo_subtitle')
        logo_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo_subtitle)
        sidebar_layout.addSpacing(12)

        self.dashboard_button = self.create_menu_button('Dashboard')
        self.pricing_button = self.create_menu_button('Pricing Settings')
        self.bean_data_sheet_button = self.create_menu_button('Bean Data Sheet')
        self.menu_buttons = [
            self.dashboard_button,
            self.pricing_button,
            self.bean_data_sheet_button,
        ]

        for button in self.menu_buttons:
            button.setCheckable(True)
            sidebar_layout.addWidget(button)

        self.dashboard_button.setChecked(True)
        sidebar_layout.addStretch()

        self.status_text = QLabel('SYSTEM NOT CONNECTED')
        self.status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_text.setStyleSheet("""
            color: #c0392b;
            font-size: 12px;
            font-weight: bold;
            padding: 4px;
        """)
        sidebar_layout.addWidget(self.status_text)

        right_side = QWidget()
        right_side.setObjectName('right_side')
        right_layout = QVBoxLayout(right_side)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        header = QWidget()
        header.setObjectName('header')
        header.setFixedHeight(70)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)

        page_title = QLabel('PhenoCoater Control Panel')
        page_title.setObjectName('page_title')
        header_layout.addWidget(page_title)
        header_layout.addStretch()

        self.admin_button = QPushButton('⚙')
        self.admin_button.setObjectName('admin_button')
        self.admin_button.setToolTip('Administrator login')
        self.admin_button.setAccessibleName('Administrator login')
        self.admin_button.clicked.connect(self.open_admin_login)
        header_layout.addWidget(self.admin_button)

        right_layout.addWidget(header)

        self.pages = QStackedWidget()
        self.pages.setObjectName('pages')

        self.dashboard_page = Dashboard()
        self.dashboard_page.camera_status_changed.connect(self.update_system_status)
        self.update_system_status('NOT CONNECTED')

        dashboard_scroll = QScrollArea()
        dashboard_scroll.setObjectName('dashboard_scroll')
        dashboard_scroll.setWidgetResizable(True)
        dashboard_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        dashboard_scroll.setWidget(self.dashboard_page)
        self.pages.addWidget(dashboard_scroll)

        self.pricing_page = PricingSettingsPage()
        self.dashboard_page.current_weight_changed.connect(
            self.pricing_page.set_current_weight
        )
        self.dashboard_page.arduino_status_changed.connect(
            self.pricing_page.set_arduino_status
        )
        self.pricing_page.set_arduino_status(
            getattr(
                self.dashboard_page,
                "arduino_status_message",
                "Checking for Arduino serial connection...",
            )
        )
        self.pricing_page.set_current_weight(
            getattr(self.dashboard_page, "current_weight_kg", None)
        )
        self.dashboard_page.nir_message_received.connect(
            self.pricing_page.update_calibration_prompt
        )
        self.pricing_page.calibration_continue_requested.connect(
            self.dashboard_page.continue_load_cell_calibration
        )
        pricing_scroll = QScrollArea()
        pricing_scroll.setObjectName('pricing_scroll')
        pricing_scroll.setWidgetResizable(True)
        pricing_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        pricing_scroll.setWidget(self.pricing_page)
        self.pages.addWidget(pricing_scroll)

        self.bean_data_sheet_page = BeanDataSheetPage()
        self.dashboard_page.bean_data_updated.connect(
            self.bean_data_sheet_page.update_dashboard_metrics
        )
        self.bean_data_sheet_page.update_dashboard_metrics(
            self.dashboard_page.get_bean_data_snapshot()
        )
        bean_data_sheet_scroll = QScrollArea()
        bean_data_sheet_scroll.setObjectName('bean_data_sheet_scroll')
        bean_data_sheet_scroll.setWidgetResizable(True)
        bean_data_sheet_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        bean_data_sheet_scroll.setWidget(self.bean_data_sheet_page)
        self.pages.addWidget(bean_data_sheet_scroll)

        right_layout.addWidget(self.pages)
        main_layout.addWidget(sidebar)
        main_layout.addWidget(right_side)

        self.dashboard_button.clicked.connect(lambda: self.change_page(0))
        self.pricing_button.clicked.connect(lambda: self.change_page(1))
        self.bean_data_sheet_button.clicked.connect(lambda: self.change_page(2))

    def change_page(self, index):
        if not 0 <= index < self.pages.count():
            return
        self.pages.setCurrentIndex(index)
        for button in self.menu_buttons:
            button.setChecked(False)
        self.menu_buttons[index].setChecked(True)

    def open_admin_login(self):
        try:
            self.admin_credentials.ensure_default_super_admin()
            dialog = AdminLoginDialog(self.admin_credentials, self)
        except (OSError, AuthStorageError) as exc:
            QMessageBox.critical(
                self,
                'Administrator access',
                f'Could not open administrator credentials: {exc}',
            )
            return

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        account = dialog.authenticated_account
        if account is None:
            QMessageBox.critical(self, 'Administrator access', 'Login failed.')
            return

        self.admin_session.grant_admin(
            account.get('username'),
            account.get('role', 'admin'),
            account.get('name'),
        )
        if self.admin_panel is None:
            self.admin_panel = AdminControlPanel(
                self.dashboard_page,
                self.admin_session,
                self.admin_credentials,
            )
            self.admin_panel.logout_requested.connect(self.logout_admin)
        self.admin_panel.activate_admin_view()
        self.hide()
        self.admin_panel.show()
        self.admin_panel.raise_()
        self.admin_panel.activateWindow()

    def logout_admin(self):
        self.admin_session.revoke()
        if self.admin_panel is not None:
            self.admin_panel.deactivate_admin_view()
            self.admin_panel.hide()
        self.dashboard_page.set_camera_usage_button(None)
        self.show()
        self.raise_()
        self.activateWindow()

    def update_system_status(self, state):
        connected = state == 'CONNECTED'
        status_text = 'SYSTEM CONNECTED' if connected else 'SYSTEM NOT CONNECTED'
        self.status_text.setText(status_text)
        color = '#2e7d4f' if connected else '#c0392b'
        self.status_text.setStyleSheet(f"""
            color: {color};
            font-size: 12px;
            font-weight: bold;
            padding: 10px;
        """)

    def create_menu_button(self, label):
        button = AnimatedButton(label)
        button.setProperty('class', 'menu_button')
        button.setObjectName('menu_button')
        return button


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())

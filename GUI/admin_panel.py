from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .auth import (
    SUPER_ADMIN_ROLE,
    AdminCredentials,
    AdminSession,
    AuthStorageError,
)
from .camera import CameraPage
from .history import HistoryPage
from .nir_analysis import NIRAnalysisPage
from .results import ResultsPage
from .settings import SettingsPage
from .show_password_checkbox import ShowPasswordCheckBox
from .touch_scrolling import enable_touch_scrolling


class AdminPasswordResetDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setObjectName("admin_password_reset_dialog")
        self.setWindowTitle(f"Reset password - {username}")
        self.setModal(True)
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Enter a new password for {username}."))

        self.password_input = QLineEdit()
        self.password_input.setObjectName("reset_admin_password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("New password")
        layout.addWidget(self.password_input)

        self.show_password_checkbox = ShowPasswordCheckBox("Show password")
        self.show_password_checkbox.setObjectName(
            "reset_admin_show_password_checkbox"
        )
        self.show_password_checkbox.toggled.connect(
            self._toggle_password_visibility
        )
        layout.addWidget(self.show_password_checkbox)

        self.error_label = QLabel()
        self.error_label.setObjectName("reset_admin_password_error")
        self.error_label.setStyleSheet("color: #c0392b;")
        layout.addWidget(self.error_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Save password"
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName(
            "admin_password_reset_save_button"
        )
        self.buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setObjectName("admin_password_reset_cancel_button")
        self.buttons.accepted.connect(self._accept_if_valid)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    @property
    def password(self):
        return self.password_input.text()

    def _toggle_password_visibility(self, checked):
        mode = (
            QLineEdit.EchoMode.Normal
            if checked
            else QLineEdit.EchoMode.Password
        )
        self.password_input.setEchoMode(mode)

    def _accept_if_valid(self):
        if not self.password:
            self.error_label.setText("Please provide a password.")
            return
        self.accept()


class SystemOverviewPage(QWidget):
    def __init__(self, dashboard):
        super().__init__()
        self.setObjectName("admin_system_overview_page")
        self.dashboard = dashboard
        self.dashboard.ir_sensor_status_changed.connect(self.refresh_status)
        self.dashboard.nir_status_changed.connect(self.refresh_status)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)

        title = QLabel("System Overview")
        title.setObjectName("page_title")
        description = QLabel(
            "Live status from the application's existing hardware controller."
        )
        description.setObjectName("settings_description")
        description.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(description)

        status_container = QFrame()
        status_container.setProperty("class", "card")
        status_container.setObjectName("dashboard_status_panel")
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(12, 12, 12, 12)
        status_layout.setSpacing(8)

        status_title = QLabel("System Status")
        status_title.setProperty("class", "section_title")
        status_title.setObjectName("section_title")
        status_layout.addWidget(status_title)

        self.status_values = {}
        for name in (
            "Camera",
            "Arduino",
            "NIR Sensor",
            "NIR AI Model",
            "Load Cell",
            "AI Model",
        ):
            row = QHBoxLayout()
            label = QLabel(name)
            label.setObjectName("dashboard_status_name")
            value = QLabel("Unknown")
            value.setObjectName("dashboard_status_value")
            row.addWidget(label)
            row.addStretch()
            row.addWidget(value)
            status_layout.addLayout(row)
            self.status_values[name] = value
        status_layout.addStretch()
        layout.addWidget(status_container)
        layout.addStretch()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(500)
        self.refresh_status()

    def refresh_status(self, *_args):
        states = {
            "Camera": self.dashboard.camera_connected,
            "Arduino": self.dashboard.arduino_connected,
            "NIR Sensor": self.dashboard.nir_connected,
            "NIR AI Model": getattr(
                self.dashboard,
                "nir_classifier",
                None,
            ) is not None,
            "Load Cell": getattr(
                self.dashboard,
                "current_weight_kg",
                None,
            ) is not None,
            "AI Model": getattr(self.dashboard, "ai_model", None) is not None,
        }
        for name, connected in states.items():
            value = self.status_values[name]
            if name in ("AI Model", "NIR AI Model"):
                status_text = "READY" if connected else "NOT READY"
                if (
                    name == "NIR AI Model"
                    and connected
                    and getattr(self.dashboard, "nir_model_warning", "")
                ):
                    status_text = "READY (CHECK VERSION)"
            else:
                status_text = "CONNECTED" if connected else "NOT CONNECTED"
            value.setText(status_text)
            value.setProperty(
                "connection_state",
                "connected" if connected else "disconnected",
            )
            value.style().unpolish(value)
            value.style().polish(value)


class ProcessMonitorPage(QWidget):
    def __init__(self, dashboard):
        super().__init__()
        self.setObjectName("admin_process_monitor_page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)
        title = QLabel("Debug Logs")
        title.setObjectName("page_title")
        description = QLabel(
            "Runtime hardware status and messages received from the connected controller."
        )
        description.setObjectName("settings_description")
        layout.addWidget(title)
        layout.addWidget(description)
        self.log_output = QPlainTextEdit()
        self.log_output.setObjectName("admin_log_output")
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(1000)
        layout.addWidget(self.log_output)
        dashboard.system_log_received.connect(self.append_log)
        dashboard.nir_message_received.connect(self.append_log)

    def append_log(self, message):
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        self.log_output.appendPlainText(f"{timestamp}  {message}")
        self.log_output.ensureCursorVisible()


class AdminAccountCreationPage(QWidget):
    def __init__(
        self,
        session: AdminSession,
        credentials: AdminCredentials,
    ):
        super().__init__()
        self.session = session
        self.credentials = credentials
        self.setObjectName("admin_account_creation_page")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)
        title = QLabel("Create Admin")
        title.setObjectName("page_title")
        description = QLabel(
            "Create an administrator account using a username and password."
        )
        description.setObjectName("settings_description")
        layout.addWidget(title)
        layout.addWidget(description)

        form = QFormLayout()
        self.username_input = QLineEdit()
        self.username_input.setObjectName("new_admin_username")
        self.username_input.setPlaceholderText("Username")
        form.addRow("Username", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setObjectName("new_admin_password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password")
        form.addRow("Password", self.password_input)
        layout.addLayout(form)

        self.show_password_checkbox = ShowPasswordCheckBox("Show password")
        self.show_password_checkbox.setObjectName(
            "create_admin_show_password_checkbox"
        )
        self.show_password_checkbox.toggled.connect(
            self._toggle_password_visibility
        )
        layout.addWidget(self.show_password_checkbox)

        self.create_button = QPushButton("Create Admin")
        self.create_button.setObjectName("create_admin_button")
        self.create_button.clicked.connect(self.create_admin_account)
        layout.addWidget(self.create_button)

        self.status_label = QLabel()
        self.status_label.setObjectName("admin_account_status")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        accounts_title = QLabel("Registered Administrators")
        accounts_title.setObjectName("admin_accounts_heading")
        layout.addWidget(accounts_title)
        self.account_cards_layout = QVBoxLayout()
        self.account_cards_layout.setSpacing(10)
        layout.addLayout(self.account_cards_layout)
        layout.addStretch()
        self.refresh_accounts()

    def _toggle_password_visibility(self, checked):
        mode = (
            QLineEdit.EchoMode.Normal
            if checked
            else QLineEdit.EchoMode.Password
        )
        self.password_input.setEchoMode(mode)

    def create_admin_account(self):
        if not self._authorize_super_admin():
            return

        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username:
            self.status_label.setText("Please provide a username.")
            return

        try:
            self.credentials.create_account(
                name=username,
                username=username,
                secret=password,
            )
        except ValueError as exc:
            self.status_label.setText(str(exc))
            return
        except AuthStorageError as exc:
            self.status_label.setText(f"Could not save the admin account: {exc}")
            return

        self.username_input.clear()
        self.password_input.clear()
        self.status_label.setText(f"Admin account '{username}' created.")
        self.refresh_accounts()

    def refresh_accounts(self):
        while self.account_cards_layout.count():
            item = self.account_cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self.session.can_create_admin_accounts():
            return
        try:
            accounts = self.credentials.list_accounts()
        except AuthStorageError as exc:
            self.status_label.setText(f"Could not load admin accounts: {exc}")
            return

        if not accounts:
            empty_label = QLabel("No administrator accounts found.")
            empty_label.setObjectName("admin_accounts_empty")
            self.account_cards_layout.addWidget(empty_label)
            return

        for account in accounts:
            self._add_account_card(account)

    def _add_account_card(self, account):
        username = account["username"]
        is_super_admin = account.get("role") == SUPER_ADMIN_ROLE
        is_active = account.get("is_active", True)
        card = QFrame()
        card.setObjectName("admin_account_card")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 10, 14, 10)

        details = QVBoxLayout()
        account_label = QLabel(username)
        account_label.setObjectName("admin_account_username")
        role_label = QLabel(
            "Super Admin · Protected"
            if is_super_admin
            else f"Admin · {'Active' if is_active else 'Disabled'}"
        )
        role_label.setObjectName("admin_account_role")
        details.addWidget(account_label)
        details.addWidget(role_label)
        row.addLayout(details)
        row.addStretch()

        if not is_super_admin:
            toggle_button = QToolButton()
            toggle_button.setObjectName("admin_account_toggle_button")
            toggle_button.setIcon(
                self.style().standardIcon(
                    QStyle.StandardPixmap.SP_MediaPause
                    if is_active
                    else QStyle.StandardPixmap.SP_MediaPlay
                )
            )
            toggle_action = "Disable" if is_active else "Enable"
            toggle_button.setToolTip(f"{toggle_action} {username}")
            toggle_button.setAccessibleName(f"{toggle_action} admin {username}")
            toggle_button.clicked.connect(
                lambda _checked=False, account_username=username:
                self.toggle_account_status(account_username)
            )
            row.addWidget(toggle_button)

            delete_button = QToolButton()
            delete_button.setObjectName("admin_account_delete_button")
            delete_button.setIcon(
                self.style().standardIcon(
                    QStyle.StandardPixmap.SP_DialogDiscardButton
                )
            )
            delete_button.style().unpolish(delete_button)
            delete_button.style().polish(delete_button)
            delete_button.setToolTip(f"Delete {username}")
            delete_button.setAccessibleName(f"Delete admin {username}")
            delete_button.clicked.connect(
                lambda _checked=False, account_username=username:
                self.delete_admin_account(account_username)
            )
            row.addWidget(delete_button)

            reset_button = QToolButton()
            reset_button.setObjectName("admin_account_reset_password_button")
            reset_button.setIcon(
                self.style().standardIcon(
                    QStyle.StandardPixmap.SP_FileDialogDetailedView
                )
            )
            reset_button.setToolTip(f"Reset password for {username}")
            reset_button.setAccessibleName(
                f"Reset password for admin {username}"
            )
            reset_button.clicked.connect(
                lambda _checked=False, account_username=username:
                self.reset_admin_password(account_username)
            )
            row.addWidget(reset_button)

        self.account_cards_layout.addWidget(card)

    def toggle_account_status(self, username):
        if not self._authorize_super_admin():
            return
        try:
            account = next(
                (
                    item for item in self.credentials.list_accounts()
                    if item["username"].lower() == username.lower()
                ),
                None,
            )
            if account is None:
                self.status_label.setText("Administrator account not found.")
                self.refresh_accounts()
                return
            self.credentials.disable_account(
                username,
                disabled=account.get("is_active", True),
            )
        except (ValueError, AuthStorageError) as exc:
            self.status_label.setText(str(exc))
            return
        self.status_label.setText(
            f"Admin account '{username}' "
            f"{'disabled' if account.get('is_active', True) else 'enabled'}."
        )
        self.refresh_accounts()

    def delete_admin_account(self, username):
        if not self._authorize_super_admin():
            return
        confirmation = QMessageBox(self)
        confirmation.setObjectName("admin_delete_confirmation_dialog")
        confirmation.setIcon(QMessageBox.Icon.Question)
        confirmation.setWindowTitle("Delete Admin Account")
        confirmation.setText(f"Delete the admin account '{username}'?")
        confirmation.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        confirmation.button(
            QMessageBox.StandardButton.Yes
        ).setObjectName("admin_delete_confirm_button")
        confirmation.button(
            QMessageBox.StandardButton.No
        ).setObjectName("admin_delete_cancel_button")
        confirmation.style().unpolish(confirmation)
        confirmation.style().polish(confirmation)
        for button in (
            confirmation.button(QMessageBox.StandardButton.Yes),
            confirmation.button(QMessageBox.StandardButton.No),
        ):
            button.style().unpolish(button)
            button.style().polish(button)
        confirmation.setDefaultButton(QMessageBox.StandardButton.No)
        answer = confirmation.exec()
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.credentials.delete_account(username)
        except (ValueError, AuthStorageError) as exc:
            self.status_label.setText(str(exc))
            return
        self.status_label.setText(f"Admin account '{username}' deleted.")
        self.refresh_accounts()

    def reset_admin_password(self, username):
        if not self._authorize_super_admin():
            return
        dialog = AdminPasswordResetDialog(username, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.credentials.reset_password(username, dialog.password)
        except (ValueError, AuthStorageError) as exc:
            self.status_label.setText(str(exc))
            return
        dialog.password_input.clear()
        self.status_label.setText(
            f"Password for admin account '{username}' was reset."
        )
        self.refresh_accounts()

    def _authorize_super_admin(self):
        try:
            self.session.require_admin()
        except PermissionError:
            self.status_label.setText("Administrator access is required.")
            return False
        if not self.session.can_create_admin_accounts():
            self.status_label.setText("Only the Super Admin can create admin accounts.")
            return False
        return True


class AdminControlPanel(QMainWindow):
    logout_requested = Signal()

    SECTION_NAMES = (
        "System Overview",
        "Camera",
        "NIR Analysis",
        "Weight Analysis",
        "System Settings",
        "Process Monitor / Debug Logs",
        "History",
        "Create Admin Account",
    )

    def __init__(
        self,
        dashboard,
        session: AdminSession,
        credentials: AdminCredentials | None = None,
    ):
        session.require_admin()
        super().__init__()
        self.dashboard = dashboard
        self.session = session
        self.credentials = credentials or AdminCredentials()
        self.setObjectName("admin_control_panel")
        self.setWindowTitle("PhenoCoater - Admin Control Panel")
        self.resize(1200, 760)
        self.setMinimumSize(640, 360)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("admin_panel_central")
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("admin_sidebar")
        sidebar.setFixedWidth(340)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 14, 14, 12)
        heading = QLabel("ADMIN")
        heading.setObjectName("logo_title")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(heading)
        sidebar_layout.addSpacing(10)

        self.stack = QStackedWidget()
        self.stack.setObjectName("admin_pages")
        self.camera_page = CameraPage(camera_controller=self.dashboard)
        self.nir_page = NIRAnalysisPage()
        self.nir_page.set_classifier_result(
            (
                "MODEL READY WITH WARNING"
                if getattr(self.dashboard, "nir_model_warning", "")
                else "MODEL READY"
            )
            if getattr(self.dashboard, "nir_classifier", None) is not None
            else "UNAVAILABLE"
        )
        self.results_page = ResultsPage(self.dashboard)
        self.settings_page = SettingsPage(
            self.dashboard,
            permission_check=lambda: self.session.is_admin,
        )
        self.settings_page.ai_model_path_changed.connect(
            self.camera_page.use_dashboard_model
        )
        self.history_page = HistoryPage()
        pages = [
            SystemOverviewPage(self.dashboard),
            self.camera_page,
            self.nir_page,
            self.results_page,
            self.settings_page,
            ProcessMonitorPage(self.dashboard),
            self.history_page,
            AdminAccountCreationPage(self.session, self.credentials),
        ]
        self.dashboard.nir_message_received.connect(
            self.nir_page.append_serial_line
        )
        nir_classification_signal = getattr(
            self.dashboard,
            "nir_classification_changed",
            None,
        )
        if nir_classification_signal is not None:
            nir_classification_signal.connect(
                self.nir_page.set_classifier_result
            )
        nir_model_error = getattr(self.dashboard, "nir_model_error", "")
        if nir_model_error:
            self.dashboard.system_log_received.emit(nir_model_error)
        nir_model_warning = getattr(
            self.dashboard,
            "nir_model_warning",
            "",
        )
        if nir_model_warning:
            self.dashboard.system_log_received.emit(
                f"NIR AI model compatibility warning: {nir_model_warning}"
            )

        self.navigation_buttons = []
        self.admin_scroll_areas = []
        for index, name in enumerate(self.SECTION_NAMES):
            label = {
                "Process Monitor / Debug Logs": "Debug Logs",
                "Create Admin Account": "Create Admin",
            }.get(name, name)
            button = QPushButton(label)
            button.setObjectName("admin_navigation_button")
            button.setCheckable(True)
            button.clicked.connect(
                lambda _checked=False, page_index=index: self.change_page(page_index)
            )
            sidebar_layout.addWidget(button)
            self.navigation_buttons.append(button)
            if name == "Create Admin Account":
                button.setVisible(self.session.can_create_admin_accounts())
            scroll = QScrollArea()
            scroll.setObjectName("admin_page_scroll")
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            enable_touch_scrolling(scroll)
            scroll.setAutoFillBackground(True)
            scroll.viewport().setAutoFillBackground(True)
            palette = scroll.palette()
            palette.setColor(QPalette.ColorRole.Window, QColor("#f4f6f8"))
            scroll.setPalette(palette)
            scroll.viewport().setPalette(palette)
            scroll.setWidget(pages[index])
            self.stack.addWidget(scroll)
            self.admin_scroll_areas.append(scroll)

        sidebar_layout.addStretch()
        logout_button = QPushButton("Log out")
        logout_button.setObjectName("admin_logout_button")
        logout_button.clicked.connect(self.logout_requested.emit)
        sidebar_layout.addWidget(logout_button)
        layout.addWidget(sidebar)

        content = QWidget()
        content.setObjectName("admin_panel_content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        header = QWidget()
        header.setObjectName("admin_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)
        title = QLabel("PhenoCoater Administrator")
        title.setObjectName("page_title")
        header_layout.addWidget(title)
        header_layout.addStretch()
        content_layout.addWidget(header)
        content_layout.addWidget(self.stack)
        layout.addWidget(content)
        self.change_page(0)

    def activate_admin_view(self):
        self.session.require_admin()
        self._update_admin_management_access()
        self.dashboard.set_camera_usage_button(
            self.settings_page.camera_usage_button
        )
        self.nir_page.set_scanning_state(
            getattr(self.dashboard, "nir_scanning", False)
        )

    def _update_admin_management_access(self):
        can_manage_accounts = self.session.can_create_admin_accounts()
        accounts_index = self.SECTION_NAMES.index("Create Admin Account")
        self.navigation_buttons[accounts_index].setVisible(can_manage_accounts)
        account_page = self.stack.widget(accounts_index).widget()
        account_page.refresh_accounts()
        if not can_manage_accounts and self.stack.currentIndex() == accounts_index:
            self.change_page(0)

    def deactivate_admin_view(self):
        self.camera_page.camera_timer.stop()

    def change_page(self, index):
        if not self._authorize():
            return
        if (
            index == self.SECTION_NAMES.index("Create Admin Account")
            and not self.session.can_create_admin_accounts()
        ):
            self.statusBar().showMessage(
                "Only the Super Admin can create admin accounts.", 5000
            )
            return
        self.stack.setCurrentIndex(index)
        for button in self.navigation_buttons:
            button.setChecked(False)
        self.navigation_buttons[index].setChecked(True)

    def _authorize(self):
        try:
            self.session.require_admin()
        except PermissionError:
            self.statusBar().showMessage(
                "Administrator session expired; log in again.", 5000
            )
            self.logout_requested.emit()
            return False
        return True

    def closeEvent(self, event):
        self.logout_requested.emit()
        event.ignore()

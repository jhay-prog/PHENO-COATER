from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from .auth import AdminCredentials, AuthStorageError
from .show_password_checkbox import ShowPasswordCheckBox


class AdminLoginDialog(QDialog):
    def __init__(self, credentials: AdminCredentials, parent=None):
        super().__init__(parent)
        self.credentials = credentials
        self.setup_required = not credentials.is_configured()
        self.authenticated_account = None
        self.setObjectName('admin_login_dialog')
        self.setWindowTitle(
            'Set up administrator' if self.setup_required else 'Administrator login'
        )
        self.setModal(True)
        self.setMinimumWidth(420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 30, 32, 28)
        layout.setSpacing(18)

        title = QLabel(
            'Set up administrator' if self.setup_required else 'Administrator login'
        )
        title.setObjectName('admin_login_title')
        layout.addWidget(title)

        description = QLabel(
            'Create the initial administrator account.'
            if self.setup_required
            else 'Enter the administrator credentials to open the control panel.'
        )
        description.setObjectName('admin_login_description')
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 0)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(14)
        self.username_input = QLineEdit()
        self.username_input.setObjectName('admin_login_username_input')
        self.username_input.setPlaceholderText('Username or email')
        form.addRow('Username', self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setObjectName('admin_login_password_input')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText('Password')
        form.addRow('Password', self.password_input)

        self.confirm_input = None
        if self.setup_required:
            self.confirm_input = QLineEdit()
            self.confirm_input.setObjectName('admin_login_confirm_input')
            self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm_input.setPlaceholderText('Repeat password')
            form.addRow('Confirm', self.confirm_input)

        self.show_password_checkbox = ShowPasswordCheckBox('Show password')
        self.show_password_checkbox.setObjectName('admin_show_password_checkbox')
        self.show_password_checkbox.toggled.connect(self._toggle_password_visibility)
        layout.addLayout(form)
        layout.addWidget(self.show_password_checkbox)

        self.error_label = QLabel()
        self.error_label.setObjectName('admin_login_error')
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch()
        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.setObjectName('admin_login_cancel_button')
        self.submit_button = QPushButton(
            'Create administrator' if self.setup_required else 'Log in'
        )
        self.submit_button.setObjectName('admin_login_submit_button')
        self.submit_button.setDefault(True)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.submit_button)
        layout.addLayout(actions)

        self.submit_button.clicked.connect(self._submit)
        self.cancel_button.clicked.connect(self.reject)
        self.password_input.returnPressed.connect(self._submit)
        self.username_input.returnPressed.connect(self._submit)
        if self.confirm_input is not None:
            self.confirm_input.returnPressed.connect(self._submit)
        self.username_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _toggle_password_visibility(self, checked):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.password_input.setEchoMode(mode)
        if self.confirm_input is not None:
            self.confirm_input.setEchoMode(mode)

    def _submit(self):
        if not self.submit_button.isEnabled():
            return

        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirmation = self.confirm_input.text() if self.confirm_input is not None else ''

        try:
            if self.setup_required:
                if password != confirmation:
                    raise ValueError('The passwords do not match.')
                if not username:
                    raise ValueError('Please provide a username.')
                self.credentials.create_initial_admin(password, confirmation)
                account = self.credentials.authenticate(username, password)
            else:
                account = self.credentials.authenticate(username, password)
            if account is None:
                raise ValueError('Incorrect username or password.')
            self.authenticated_account = account
            self.password_input.clear()
            if self.confirm_input is not None:
                self.confirm_input.clear()
            self.accept()
        except (ValueError, AuthStorageError) as exc:
            self.password_input.clear()
            if self.confirm_input is not None:
                self.confirm_input.clear()
            self.error_label.setText(str(exc))

    def reject(self):
        if hasattr(self, 'submit_button') and not self.submit_button.isEnabled():
            return
        super().reject()

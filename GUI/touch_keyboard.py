import ctypes
import logging
import os
import subprocess

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QTextEdit,
)


_LOGGER = logging.getLogger(__name__)
_EDITABLE_WIDGETS = (QLineEdit, QPlainTextEdit, QTextEdit)
_keyboard_process = None


def _find_osk():
    windir = os.environ.get("SystemRoot", r"C:\Windows")
    # Sysnative = the real System32 as seen by a 32-bit process
    for folder in ("Sysnative", "System32"):
        path = os.path.join(windir, folder, "osk.exe")
        if os.path.isfile(path):
            return path
    return None


def _launch_windows_keyboard():
    global _keyboard_process

    # Already open? Don't spawn another one.
    if _keyboard_process is not None and _keyboard_process.poll() is None:
        return True

    path = _find_osk()
    if path:
        try:
            _keyboard_process = subprocess.Popen([path])
            return True
        except OSError:
            _LOGGER.exception("Could not launch %s", path)

    # Last resort: let Windows resolve osk.exe itself
    result = ctypes.windll.shell32.ShellExecuteW(
        None, "open", "osk.exe", None, None, 1
    )
    if result > 32:
        return True

    _LOGGER.error("ShellExecuteW failed with code %s", result)
    return False


class TouchKeyboardFilter(QObject):
    def __init__(self, application):
        super().__init__(application)
        self._failure_notified = False

    def eventFilter(self, watched, event):
        if (
            event.type() == QEvent.Type.FocusIn
            and isinstance(watched, _EDITABLE_WIDGETS)
            and not watched.isReadOnly()
        ):
            QTimer.singleShot(0, self._launch_keyboard)
        return False

    def _launch_keyboard(self):
        if _launch_windows_keyboard() or self._failure_notified:
            return
        self._failure_notified = True
        QMessageBox.warning(
            None,
            "On-screen keyboard unavailable",
            "Windows could not find or launch its touch keyboard or On-Screen Keyboard.",
        )


def install_touch_keyboard(application):
    if not isinstance(application, QApplication):
        raise TypeError("On-screen keyboard support requires a QApplication.")
    if application.findChild(TouchKeyboardFilter) is not None:
        return

    keyboard_filter = TouchKeyboardFilter(application)
    application.installEventFilter(keyboard_filter)
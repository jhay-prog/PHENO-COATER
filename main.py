import sys

from PySide6.QtWidgets import QApplication

from GUI.main_window import MainWindow
from GUI.styles import APP_STYLE
from GUI.touch_keyboard import install_touch_keyboard


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    install_touch_keyboard(app)

    window = MainWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

import sys

from PySide6.QtWidgets import QApplication

from GUI.main_window import MainWindow
from GUI.styles import APP_STYLE


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer
from PySide6.QtWidgets import QPushButton


class AnimatedButton(QPushButton):
    """Push button with a short scale animation on press and release."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._normal_geometry = None
        self._animation = QPropertyAnimation(self, b"geometry", self)
        self._animation.setDuration(120)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def mousePressEvent(self, event):
        self._normal_geometry = self.geometry()
        self._animate_scale(0.97)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        QTimer.singleShot(0, lambda: self._animate_scale(1.0))

    def _animate_scale(self, scale):
        if self._normal_geometry is None:
            return
        geometry = self._normal_geometry
        target_width = round(geometry.width() * scale)
        target_height = round(geometry.height() * scale)
        target = geometry.adjusted(
            (geometry.width() - target_width) // 2,
            (geometry.height() - target_height) // 2,
            -(geometry.width() - target_width) // 2,
            -(geometry.height() - target_height) // 2,
        )
        self._animation.stop()
        self._animation.setStartValue(self.geometry())
        self._animation.setEndValue(target)
        self._animation.start()

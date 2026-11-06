from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QScroller


def enable_touch_scrolling(scroll_area: QScrollArea) -> None:
    scroll_area.setVerticalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    QScroller.grabGesture(
        scroll_area.viewport(),
        QScroller.ScrollerGestureType.TouchGesture,
    )

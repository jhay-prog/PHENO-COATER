from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QCheckBox


class ShowPasswordCheckBox(QCheckBox):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        indicator_size = 16
        indicator_y = (self.height() - indicator_size) // 2
        indicator = QRectF(1, indicator_y, indicator_size, indicator_size)
        painter.setPen(QPen(QColor("#000000"), 1.5))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(indicator, 2, 2)

        if self.isChecked():
            check = QPainterPath()
            check.moveTo(indicator.left() + 3.5, indicator.top() + 8)
            check.lineTo(indicator.left() + 6.5, indicator.top() + 11)
            check.lineTo(indicator.left() + 12.5, indicator.top() + 5)
            painter.setPen(
                QPen(
                    QColor("#173f2a"),
                    2,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(check)

        painter.setPen(self.palette().color(self.foregroundRole()))
        text_rect = QRect(
            indicator_size + 8,
            0,
            max(0, self.width() - indicator_size - 8),
            self.height(),
        )
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.text(),
        )

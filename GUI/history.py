from dataclasses import dataclass
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QStyle,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class BatchRecord:
    batch_id: str
    process_date: date
    price_per_kilo: float
    total_weight_kg: float
    total_beans: int
    pns_grade_score: int
    current_weight_kg: float
    moisture_score_percent: float


_BATCHES = (
    BatchRecord(
        batch_id="0001",
        process_date=date(2026, 11, 20),
        price_per_kilo=250.00,
        total_weight_kg=12.40,
        total_beans=1248,
        pns_grade_score=92,
        current_weight_kg=11.85,
        moisture_score_percent=7.2,
    ),
)


def get_batches():
    return tuple(
        sorted(_BATCHES, key=lambda batch: batch.process_date, reverse=True)
    )


def get_batch_by_id(batch_id):
    return next(
        (batch for batch in _BATCHES if batch.batch_id == batch_id),
        None,
    )


class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("admin_history_page")
        self._setup_ui()
        self.show_history_list()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 14)
        root_layout.setSpacing(8)

        title = QLabel("History")
        title.setObjectName("page_title")
        subtitle = QLabel("Review past sorting batches and their results.")
        subtitle.setObjectName("settings_description")
        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        self.views = QStackedWidget()
        self.views.setObjectName("history_views")
        self.list_view = self._create_list_view()
        self.details_view = self._create_details_view()
        self.views.addWidget(self.list_view)
        self.views.addWidget(self.details_view)
        root_layout.addWidget(self.views)
        root_layout.addStretch()

    def _create_list_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        self.batch_entries = QVBoxLayout()
        self.batch_entries.setSpacing(8)
        layout.addLayout(self.batch_entries)
        layout.addStretch()
        return view

    def _create_details_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        back_button = QPushButton("Back")
        back_button.setObjectName("history_back_button")
        back_button.setFixedWidth(180)
        back_button.setStyleSheet("text-align: center;")
        back_button.clicked.connect(self.show_history_list)
        layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.summary_grid = QGridLayout()
        self.summary_grid.setHorizontalSpacing(10)
        self.summary_grid.setVerticalSpacing(10)
        self.summary_values = {}
        self.summary_cards = []
        layout.addLayout(self.summary_grid)

        layout.addStretch()
        return view

    def show_history_list(self):
        while self.batch_entries.count():
            item = self.batch_entries.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        batches = get_batches()
        if not batches:
            empty_message = QLabel("No batches yet")
            empty_message.setObjectName("history_empty_message")
            self.batch_entries.addWidget(empty_message)
        else:
            for batch in batches:
                entry = QPushButton(
                    f"{batch.process_date.strftime('%B %d, %Y')} - "
                    f"Batch ({batch.batch_id})"
                )
                entry.setObjectName("history_batch_entry")
                entry.setMinimumHeight(76)
                entry.setIcon(
                    self.style().standardIcon(
                        QStyle.StandardPixmap.SP_ArrowRight
                    )
                )
                entry.clicked.connect(
                    lambda _checked=False, batch_id=batch.batch_id:
                    self.show_batch_details(batch_id)
                )
                self.batch_entries.addWidget(entry)

        self.views.setCurrentWidget(self.list_view)

    def show_batch_details(self, batch_id):
        batch = get_batch_by_id(batch_id)
        if batch is None:
            return False

        values = (
            ("Batch ID", batch.batch_id, "Batch number"),
            ("Price per kilo", f"₱ {batch.price_per_kilo:,.2f}", "Per kg"),
            ("Total weight", f"{batch.total_weight_kg:,.2f} kg", "Load cell"),
            ("Total beans", f"{batch.total_beans:,}", "Infrared"),
            (
                "Overall PNS grade score",
                f"{batch.pns_grade_score} / 100",
                "Dashboard",
            ),
            ("Current weight", f"{batch.current_weight_kg:,.2f} kg", "Dashboard"),
            (
                "Overall moisture score",
                f"{batch.moisture_score_percent:g} %",
                "Dashboard",
            ),
            (
                "Date",
                batch.process_date.strftime("%b %d, %Y"),
                "Process date",
            ),
        )
        while self.summary_grid.count():
            item = self.summary_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.summary_values.clear()
        self.summary_cards.clear()
        for name, value, caption in values:
            card = QFrame()
            card.setObjectName("history_summary_card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(8)
            name_label = QLabel(name)
            name_label.setObjectName("history_summary_name")
            value_label = QLabel(value)
            value_label.setObjectName("history_summary_value")
            value_label.setWordWrap(True)
            caption_label = QLabel(caption)
            caption_label.setObjectName("history_summary_caption")
            card_layout.addWidget(name_label)
            card_layout.addWidget(value_label)
            card_layout.addStretch()
            card_layout.addWidget(caption_label)
            self.summary_cards.append(card)
            self.summary_values[name] = value_label

        self._layout_summary_cards()
        self.views.setCurrentWidget(self.details_view)
        return True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.summary_cards:
            self._layout_summary_cards()

    def _layout_summary_cards(self):
        while self.summary_grid.count():
            self.summary_grid.takeAt(0)
        if self.width() >= 700:
            columns = 4
        elif self.width() >= 420:
            columns = 2
        else:
            columns = 1
        for index, card in enumerate(self.summary_cards):
            self.summary_grid.addWidget(card, index // columns, index % columns)

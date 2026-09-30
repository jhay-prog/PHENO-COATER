from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QFrame, QHeaderView, QTableWidget, QVBoxLayout, QWidget
from .animated_button import AnimatedButton


class ResultsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("results_page")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 30)
        layout.setSpacing(20)

        title_label = QLabel("Results")
        title_label.setObjectName("page_title")
        subtitle = QLabel("Seed grading summary and acceptance history")
        subtitle.setObjectName("settings_description")
        layout.addWidget(title_label)
        layout.addWidget(subtitle)

        summary_cards = QGridLayout()
        summary_cards.setHorizontalSpacing(15)
        summary_cards.setVerticalSpacing(15)
        for index, (label, value) in enumerate([
            ("Total seeds", "0"),
            ("Foreign Objects", "0"),
        ]):
            card = QFrame()
            card.setObjectName("settings_panel")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 18, 18, 18)
            name = QLabel(label)
            name.setStyleSheet("color: #6b7280; font-size: 12px;")
            value_label = QLabel(value)
            value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
            card_layout.addWidget(name)
            card_layout.addWidget(value_label)
            summary_cards.addWidget(card, index // 2, index % 2)
        layout.addLayout(summary_cards)

        table = QTableWidget()
        table.setObjectName("results_table")
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Seed ID", "Weight", "Moisture", "Quality"])
        table.setRowCount(0)
        table.setMinimumHeight(220)
        table.horizontalHeader().setSectionsMovable(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        table.verticalHeader().setDefaultSectionSize(34)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table)

        actions = QHBoxLayout()
        actions.addStretch()
        report_btn = AnimatedButton("GENERATE REPORT")
        report_btn.setObjectName("settings_save_button")
        export_btn = AnimatedButton("EXPORT CSV")
        export_btn.setObjectName("settings_reset_button")
        actions.addWidget(report_btn)
        actions.addWidget(export_btn)
        layout.addLayout(actions)
        layout.addStretch()

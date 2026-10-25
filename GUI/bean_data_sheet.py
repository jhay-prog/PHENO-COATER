from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)


class BeanDataSheetPage(QWidget):
    TABLE_COLUMNS = {
        "Beans in 100g Sample": (
            "Bean ID",
            "Accumulated Weight",
            "Bean Count",
            "PNS Sample ID",
            "Condition",
            "Good (%)",
            "Moldy (%)",
            "Slaty (%)",
            "Defective (%)",
        ),
        "PNS Grade Sample": (
            "Sample ID",
            "Weight",
            "PNS Grade",
            "Bean Count",
            "Good",
            "Moldy",
            "Slaty",
            "Defective",
            "PNS Score",
        ),
        "Moisture Content Sample": (
            "Good Bean ID",
            "Moisture Content",
            "Moisture Grade",
            "Moisture Score",
        ),
    }

    def __init__(self):
        super().__init__()
        self.setObjectName("bean_data_sheet_page")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)

        heading = QLabel("Bean Data Sheet")
        heading.setObjectName("bean_sheet_title")
        layout.addWidget(heading)

        description = QLabel(
            "Review bean samples, PNS grading, and moisture content data."
        )
        description.setObjectName("bean_sheet_description")
        layout.addWidget(description)

        summary_area = QHBoxLayout()
        summary_area.setSpacing(8)
        current_summary_column = QVBoxLayout()
        current_summary_column.setSpacing(8)
        for title in (
            "Current Bean Number",
            "Current PNS Sample Number",
            "Current Good Bean Number",
            "Current Weight",
        ):
            current_summary_column.addWidget(
                self._create_summary_card(title, horizontal=True),
                1,
            )
        summary_area.addLayout(current_summary_column, 1)

        grading_summary_row = QHBoxLayout()
        grading_summary_row.setSpacing(8)
        grading_summary_row.addWidget(
            self._create_summary_card(
                "PNS Grade Summary",
            ),
            1,
        )
        grading_summary_row.addWidget(
            self._create_summary_card(
                "Moisture Content Grade Summary",
            ),
            1,
        )
        summary_area.addLayout(grading_summary_row, 2)
        layout.addLayout(summary_area, 1)

        table_panel = QFrame()
        table_panel.setObjectName("bean_sheet_table_panel")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(10, 8, 10, 10)
        table_layout.setSpacing(8)

        table_title = QLabel("Data Table")
        table_title.setObjectName("bean_sheet_table_title")
        table_layout.addWidget(
            table_title,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        tabs_layout = QHBoxLayout()
        tabs_layout.setSpacing(6)
        self.table_tabs = {}
        for title in self.TABLE_COLUMNS:
            tab = QPushButton(title)
            tab.setObjectName("bean_sheet_tab")
            tab.setCheckable(True)
            tab.setProperty("table_title", title)
            tab.clicked.connect(self._show_selected_table)
            tabs_layout.addWidget(tab)
            self.table_tabs[title] = tab
        table_layout.addLayout(tabs_layout)

        self.data_table = QTableWidget(0, 0)
        self.data_table.setObjectName("bean_data_table")
        self.data_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.data_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.data_table.setAlternatingRowColors(True)
        self.data_table.verticalHeader().setVisible(False)
        self.data_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        table_layout.addWidget(self.data_table, 1)

        self.empty_state = QLabel()
        self.empty_state.setObjectName("bean_sheet_empty_state")
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.hide()
        table_layout.addWidget(self.empty_state)

        layout.addWidget(table_panel, 2)
        self.show_table("Beans in 100g Sample")

    @staticmethod
    def _create_summary_card(title, value="", horizontal=False):
        card = QFrame()
        card.setObjectName("bean_sheet_summary_card")
        card_layout = QHBoxLayout(card) if horizontal else QVBoxLayout(card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(10 if horizontal else 4)

        title_label = QLabel(title)
        title_label.setObjectName(
            "bean_sheet_current_label"
            if horizontal
            else "bean_sheet_summary_title"
        )
        title_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            if horizontal
            else Qt.AlignmentFlag.AlignCenter
        )
        title_label.setWordWrap(not horizontal)
        card_layout.addWidget(
            title_label,
            alignment=(
                Qt.AlignmentFlag.AlignVCenter
                if horizontal
                else Qt.AlignmentFlag(0)
            ),
        )
        if horizontal:
            card_layout.addStretch()

        value_label = QLabel(value)
        value_label.setObjectName(
            "bean_sheet_current_value"
            if horizontal
            else "bean_sheet_summary_value"
        )
        value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            if horizontal
            else Qt.AlignmentFlag.AlignCenter
        )
        value_label.setWordWrap(True)
        card_layout.addWidget(
            value_label,
            alignment=(
                Qt.AlignmentFlag.AlignVCenter
                if horizontal
                else Qt.AlignmentFlag(0)
            ),
        )
        return card

    def show_table(self, title):
        if title not in self.TABLE_COLUMNS:
            raise ValueError(f"Unknown bean data table: {title}")
        for tab_title, tab in self.table_tabs.items():
            tab.setChecked(tab_title == title)
        columns = self.TABLE_COLUMNS[title]
        self.data_table.clear()
        self.data_table.setColumnCount(len(columns))
        self.data_table.setHorizontalHeaderLabels(columns)
        self.data_table.setRowCount(0)
        self.empty_state.hide()

    def _show_selected_table(self, checked):
        if checked:
            tab = self.sender()
            self.show_table(tab.property("table_title"))

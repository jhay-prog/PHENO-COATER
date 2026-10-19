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
        layout.setContentsMargins(34, 28, 34, 32)
        layout.setSpacing(18)

        heading = QLabel("Bean Data Sheet")
        heading.setObjectName("bean_sheet_title")
        layout.addWidget(heading)

        description = QLabel(
            "Review bean samples, PNS grading, and moisture content data."
        )
        description.setObjectName("bean_sheet_description")
        layout.addWidget(description)

        summary_area = QHBoxLayout()
        summary_area.setSpacing(12)
        current_summary_column = QVBoxLayout()
        current_summary_column.setSpacing(12)
        for title in (
            "Current Bean Number",
            "Current PNS Sample Number",
            "Current Good Bean Number",
            "Current Weight",
        ):
            current_summary_column.addWidget(
                self._create_summary_card(title),
                1,
            )
        summary_area.addLayout(current_summary_column, 1)

        grading_summary_row = QHBoxLayout()
        grading_summary_row.setSpacing(12)
        grading_summary_row.addWidget(
            self._create_summary_card(
                "PNS Grade Summary",
                "No PNS grade results available",
            ),
            1,
        )
        grading_summary_row.addWidget(
            self._create_summary_card(
                "Moisture Content Grade Summary",
                "No moisture grade results available",
            ),
            1,
        )
        summary_area.addLayout(grading_summary_row, 2)
        layout.addLayout(summary_area)

        table_panel = QFrame()
        table_panel.setObjectName("bean_sheet_table_panel")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(18, 16, 18, 18)
        table_layout.setSpacing(12)

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

        self.empty_state = QLabel(
            "No bean records are available yet."
        )
        self.empty_state.setObjectName("bean_sheet_empty_state")
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        table_layout.addWidget(self.empty_state)

        layout.addWidget(table_panel, 1)
        self.show_table("Beans in 100g Sample")

    @staticmethod
    def _create_summary_card(title, value="—"):
        card = QFrame()
        card.setObjectName("bean_sheet_summary_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 12, 15, 12)
        card_layout.setSpacing(7)

        title_label = QLabel(title)
        title_label.setObjectName("bean_sheet_summary_title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        card_layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setObjectName("bean_sheet_summary_value")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setWordWrap(True)
        card_layout.addWidget(value_label)
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
        if title == "Beans in 100g Sample":
            weight_column = columns.index("Accumulated Weight")
            header_font = self.data_table.horizontalHeaderItem(
                weight_column
            ).font()
            header_font.setPointSizeF(5)
            self.data_table.horizontalHeaderItem(weight_column).setFont(
                header_font
            )
        self.data_table.setRowCount(0)
        self.empty_state.setVisible(True)

    def _show_selected_table(self, checked):
        if checked:
            tab = self.sender()
            self.show_table(tab.property("table_title"))

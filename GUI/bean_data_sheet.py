from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidgetItem,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
from .pricing import PricingSettingsPage


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
        self.bean_records = {}
        self.batch_number = 1
        self.last_batch_bean_count = 0
        self.batch_snapshot = {
            "bean_id": "0" * 12,
            "bean_count": 0,
            "batch_weight_grams": None,
            "moisture": None,
            "quality": "UNDEFINED",
        }
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
            card = self._create_summary_card(title, horizontal=True)
            if title == "Current Bean Number":
                self.current_bean_number_value = card.findChild(
                    QLabel,
                    "bean_sheet_current_value",
                )
            current_summary_column.addWidget(card, 1)
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
        self._populate_table(title)

    def update_dashboard_metrics(self, metrics):
        self.batch_snapshot.update(metrics)
        bean_id = metrics.get("bean_id")
        bean_count = metrics.get("bean_count", 0)
        if bean_count == 0:
            self.current_bean_number_value.setText("0")
        else:
            self.current_bean_number_value.setText(str(bean_count))
        if bean_count == 0:
            if self.last_batch_bean_count > 0:
                self.batch_number += 1
            self.last_batch_bean_count = 0
        if bean_id and bean_count > 0:
            record_key = (self.batch_number, bean_id)
            record = self.bean_records.setdefault(
                record_key,
                {
                    "bean_id": bean_id,
                    "bean_count": bean_count,
                    "batch_weight_grams": None,
                    "moisture": None,
                    "quality": "UNDEFINED",
                },
            )
            record.update(metrics)
            self.bean_records[record_key] = record
            self.last_batch_bean_count = bean_count
        self._populate_table(
            next(
                (
                    title
                    for title, tab in self.table_tabs.items()
                    if tab.isChecked()
                ),
                "Beans in 100g Sample",
            )
        )

    def _populate_table(self, title):
        self.data_table.setRowCount(0)
        rows = []
        if title == "Beans in 100g Sample":
            rows = self._bean_sample_rows()
        elif title == "PNS Grade Sample":
            rows = self._pns_sample_rows()
        elif title == "Moisture Content Sample":
            rows = [self._moisture_row(record) for record in self.bean_records.values()]
        for values in rows:
            row = self.data_table.rowCount()
            self.data_table.insertRow(row)
            for column, value in enumerate(values):
                self.data_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(str(value)),
                )
        self.empty_state.hide()

    def _bean_sample_rows(self):
        records = list(self.bean_records.values())
        rows = []
        for record in records:
            class_counts = self._quality_counts([record])
            rows.append((
                record["bean_id"],
                self._format_weight(record["batch_weight_grams"]),
                record["bean_count"],
                "--",
                record["quality"],
                self._format_percentage(class_counts["GOOD"], 1),
                self._format_percentage(class_counts["MOLDY"], 1),
                self._format_percentage(class_counts["SLANTY"], 1),
                self._format_percentage(class_counts["DEFECTIVE"], 1),
            ))
        return rows

    def _pns_sample_rows(self):
        rows = []
        batch_counts = {}
        for (batch_number, _), record in self.bean_records.items():
            counts = batch_counts.setdefault(
                batch_number,
                {"GOOD": 0, "MOLDY": 0, "SLANTY": 0, "DEFECTIVE": 0},
            )
            quality_counts = self._quality_counts([record])
            for quality, count in quality_counts.items():
                counts[quality] += count

            bean_count = record["bean_count"]
            pns_result = None
            if bean_count > 0:
                pns_result = PricingSettingsPage.calculate_pns_grade(
                    bean_count,
                    counts["MOLDY"] * 100 / bean_count,
                    counts["SLANTY"] * 100 / bean_count,
                    counts["DEFECTIVE"] * 100 / bean_count,
                )
            rows.append(
                (
                    record["bean_id"],
                    self._format_weight(record["batch_weight_grams"]),
                    pns_result["grade"] if pns_result else "--",
                    bean_count,
                    counts["GOOD"],
                    counts["MOLDY"],
                    counts["SLANTY"],
                    counts["DEFECTIVE"],
                    pns_result["score"] if pns_result else "--",
                )
            )
        return rows

    @staticmethod
    def _moisture_row(record):
        return (
            record["bean_id"],
            record["moisture"] if record["moisture"] is not None else "--",
            "--",
            "--",
        )

    @staticmethod
    def _quality_counts(records):
        counts = {
            "GOOD": 0,
            "MOLDY": 0,
            "SLANTY": 0,
            "DEFECTIVE": 0,
        }
        for record in records:
            quality = record["quality"].upper()
            if quality == "GOOD":
                counts["GOOD"] += 1
            elif quality == "MOLDY":
                counts["MOLDY"] += 1
            elif quality == "SLANTY":
                counts["SLANTY"] += 1
            elif quality in {
                "INSECT-DAMAGED",
                "BLACK",
                "FLAT",
                "DOUBLE",
            }:
                counts["DEFECTIVE"] += 1
        return counts

    @staticmethod
    def _format_weight(weight):
        return "--" if weight is None else f"{weight:.2f}"

    @staticmethod
    def _format_percentage(count, total):
        return "--" if total == 0 else f"{count * 100 / total:.2f}%"

    def _show_selected_table(self, checked):
        if checked:
            tab = self.sender()
            self.show_table(tab.property("table_title"))

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtCharts import QCategoryAxis, QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QPlainTextEdit,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
from .animated_button import AnimatedButton
from NIR.as7265x import AS7265XReader, NIRReading, WAVELENGTHS


class NIRAnalysisPage(QWidget):
    scan_requested = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setObjectName("nir_analysis_page")
        self.nir_reader = AS7265XReader()
        self.readings = [NIRReading(wavelength, None) for wavelength in WAVELENGTHS]
        self.received_serial_data = False
        self.scanning = False
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 30)
        layout.setSpacing(20)

        title_label = QLabel("NIR Analysis")
        title_label.setObjectName("page_title")
        subtitle = QLabel("Spectral scan and moisture estimation")
        subtitle.setObjectName("settings_description")
        layout.addWidget(title_label)
        layout.addWidget(subtitle)

        output_panel = QWidget()
        output_panel.setObjectName("settings_panel")
        output_layout = QVBoxLayout(output_panel)
        output_layout.setContentsMargins(20, 20, 20, 20)
        output_title = QLabel("AS7265X Serial Monitor")
        output_title.setProperty("class", "section_title")
        output_layout.addWidget(output_title)
        self.serial_output = QPlainTextEdit()
        self.serial_output.setReadOnly(True)
        self.serial_output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.serial_output.setMinimumHeight(180)
        self.serial_output.setMaximumBlockCount(500)
        self.serial_output.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px;"
        )
        self.serial_output.setPlainText(
            "Waiting for AS7265X serial data..."
        )
        layout.addWidget(output_panel)

        top = QHBoxLayout()
        top.setSpacing(20)
        chart_panel = QWidget()
        chart_panel.setObjectName("settings_panel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(20, 20, 20, 20)
        chart_label = QLabel("Spectral Response")
        chart_label.setProperty("class", "section_title")
        chart_layout.addWidget(chart_label)

        self.spectrum_series = QLineSeries()
        self.spectrum_series.setName("AS7265X response")
        line_pen = QPen(QColor("#2e7d4f"))
        line_pen.setWidth(3)
        self.spectrum_series.setPen(line_pen)
        self.spectrum_series.setPointsVisible(True)

        spectrum_chart = QChart()
        spectrum_chart.addSeries(self.spectrum_series)
        spectrum_chart.legend().hide()
        spectrum_chart.setBackgroundBrush(QColor("#ffffff"))
        spectrum_chart.setPlotAreaBackgroundBrush(QColor("#f4f6f8"))
        spectrum_chart.setPlotAreaBackgroundVisible(True)

        self.wavelength_axis = QCategoryAxis()
        self.wavelength_axis.setStartValue(-0.5)
        self.wavelength_axis.setRange(-0.5, len(WAVELENGTHS) - 0.5)
        self.wavelength_axis.setLabelsPosition(
            QCategoryAxis.AxisLabelsPosition.AxisLabelsPositionCenter
        )
        channel_font = QFont()
        channel_font.setPointSize(8)
        self.wavelength_axis.setLabelsFont(channel_font)
        for index, wavelength in enumerate(WAVELENGTHS):
            self.wavelength_axis.append(str(wavelength), index + 0.5)
        spectrum_chart.addAxis(self.wavelength_axis, Qt.AlignmentFlag.AlignTop)
        self.spectrum_series.attachAxis(self.wavelength_axis)

        self.intensity_axis = QValueAxis()
        self.intensity_axis.setTitleText("Intensity")
        self.intensity_axis.setRange(0, 1)
        self.intensity_axis.setTickCount(6)
        self.intensity_axis.setLabelFormat("%.2f")
        spectrum_chart.addAxis(self.intensity_axis, Qt.AlignmentFlag.AlignLeft)
        self.spectrum_series.attachAxis(self.intensity_axis)

        spectrum_view = QChartView(spectrum_chart)
        spectrum_view.setObjectName("nir_spectrum_chart")
        spectrum_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        spectrum_view.setMinimumHeight(320)
        self.spectrum_chart = spectrum_chart
        chart_layout.addWidget(spectrum_view)
        top.addWidget(chart_panel, 3)

        summary_panel = QWidget()
        summary_panel.setObjectName("settings_panel")
        summary = QVBoxLayout(summary_panel)
        summary.setContentsMargins(20, 20, 20, 20)
        summary.setSpacing(12)
        summary_title = QLabel("Current Reading")
        summary_title.setProperty("class", "section_title")
        summary.addWidget(summary_title)
        for label, value in [("Moisture Content", "0%"), ("Quality", "Good")]:
            row = QHBoxLayout()
            name = QLabel(label)
            name.setStyleSheet("color: #6b7280;")
            val = QLabel(value)
            val.setStyleSheet("font-weight: bold;")
            row.addWidget(name)
            row.addStretch()
            row.addWidget(val)
            summary.addLayout(row)
        summary.addStretch()
        top.addWidget(summary_panel, 1)
        layout.addLayout(top)

        table = QTableWidget()
        self.table = table
        table.setObjectName("nir_table")
        table.setAccessibleName("Live AS7265X readings")
        table.setColumnCount(len(WAVELENGTHS))
        table.setHorizontalHeaderLabels([f"{wavelength}nm" for wavelength in WAVELENGTHS])
        table.setRowCount(0)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        table.setMinimumHeight(180)
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionsMovable(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        for column in range(table.columnCount()):
            table.setColumnWidth(column, 78)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        table.verticalHeader().setDefaultSectionSize(34)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(False)
        layout.addWidget(table)

        buttons = QHBoxLayout()
        buttons.addStretch()
        scan_btn = AnimatedButton("START SCAN")
        scan_btn.setObjectName("settings_save_button")
        self.start_scan_button = scan_btn
        stop_btn = AnimatedButton("STOP SCANNING")
        stop_btn.setObjectName("settings_reset_button")
        self.stop_scan_button = stop_btn
        self.stop_scan_button.setEnabled(False)
        scan_btn.clicked.connect(self.start_scanning)
        stop_btn.clicked.connect(self.stop_scanning)
        buttons.addWidget(scan_btn)
        buttons.addWidget(stop_btn)
        layout.addLayout(buttons)
        layout.addStretch()

    def start_scanning(self):
        if self.scanning:
            return
        self.set_scanning_state(True)
        self.scan_requested.emit(True)

    def stop_scanning(self):
        if not self.scanning:
            return
        self.set_scanning_state(False)
        self.scan_requested.emit(False)

    def set_scanning_state(self, enabled):
        self.scanning = enabled
        self.start_scan_button.setEnabled(not enabled)
        self.stop_scan_button.setEnabled(enabled)

    def append_serial_line(self, line):
        if not line:
            return
        if "nm:" in line and not self.scanning:
            return
        if not self.received_serial_data:
            self.serial_output.clear()
            self.received_serial_data = True
        if line.startswith("-"):
            self.serial_output.appendPlainText("--------------------")
            return
        if "nm:" in line:
            self.readings = self.nir_reader.parse_line(line)
            self.update_spectrum_chart()
            formatted_line = " | ".join(
                f"{reading.wavelength_nm}nm : {reading.value:.2f}"
                for reading in self.readings
                if reading.value is not None
            )
            self.serial_output.appendPlainText("--------------------")
            self.serial_output.appendPlainText(formatted_line)
            self.serial_output.appendPlainText("--------------------")
            self.append_reading_row(formatted_line)
            self.serial_output.ensureCursorVisible()
            return
        self.serial_output.appendPlainText(line)
        self.serial_output.ensureCursorVisible()

    def update_spectrum_chart(self):
        available_readings = [
            reading
            for reading in self.readings
            if reading.value is not None
        ]
        points = [
            QPointF(index, reading.value)
            for index, reading in enumerate(self.readings)
            if reading.value is not None
        ]
        self.spectrum_series.replace(points)
        if available_readings:
            maximum_value = max(reading.value for reading in available_readings)
            self.intensity_axis.setRange(0, max(1.0, maximum_value * 1.1))

    def append_reading_row(self, formatted_line):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, reading in enumerate(self.readings):
            value = "--" if reading.value is None else f"{reading.value:.2f}"
            reading_item = QLabel(value)
            reading_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, column, reading_item)
        self.table.scrollToBottom()


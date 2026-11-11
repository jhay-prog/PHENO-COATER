from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
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
from .styles import TYPOGRAPHY_SCALE
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
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)

        title_label = QLabel("NIR Analysis")
        title_label.setObjectName("page_title")
        subtitle = QLabel("Spectral scan and moisture estimation")
        subtitle.setObjectName("settings_description")
        layout.addWidget(title_label)
        layout.addWidget(subtitle)

        output_panel = QWidget()
        output_panel.setObjectName("settings_panel")
        output_layout = QVBoxLayout(output_panel)
        output_layout.setContentsMargins(10, 10, 10, 10)
        output_title = QLabel("AS7265X Serial Monitor")
        output_title.setProperty("class", "section_title")
        output_layout.addWidget(output_title)
        self.serial_output = QPlainTextEdit()
        self.serial_output.setReadOnly(True)
        self.serial_output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.serial_output.setMinimumHeight(180)
        self.serial_output.setMaximumBlockCount(500)
        self.serial_output.setPlainText(
            "Waiting for AS7265X serial data..."
        )
        layout.addWidget(output_panel)

        top = QHBoxLayout()
        top.setSpacing(8)
        chart_panel = QWidget()
        chart_panel.setObjectName("settings_panel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(10, 10, 10, 10)
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

        self.wavelength_axis = QValueAxis()
        self.wavelength_axis.setTitleText("Wavelength (nm)")
        self.wavelength_axis.setRange(
            WAVELENGTHS[0],
            WAVELENGTHS[-1],
        )
        self.wavelength_axis.setTickCount(12)
        self.wavelength_axis.setLabelFormat("%.0f")
        channel_font = QFont()
        channel_font.setPixelSize(round(TYPOGRAPHY_SCALE["body"] * 1.5))
        self.wavelength_axis.setLabelsFont(channel_font)
        self.wavelength_axis.setTitleFont(channel_font)
        spectrum_chart.addAxis(
            self.wavelength_axis,
            Qt.AlignmentFlag.AlignBottom,
        )
        self.spectrum_series.attachAxis(self.wavelength_axis)

        self.intensity_axis = QValueAxis()
        self.intensity_axis.setTitleText("Intensity")
        self.intensity_axis.setRange(0, 150)
        self.intensity_axis.setTickCount(6)
        self.intensity_axis.setLabelFormat("%.0f")
        self.intensity_axis.setLabelsFont(channel_font)
        self.intensity_axis.setTitleFont(channel_font)
        spectrum_chart.addAxis(self.intensity_axis, Qt.AlignmentFlag.AlignLeft)
        self.spectrum_series.attachAxis(self.intensity_axis)

        spectrum_view = QChartView(spectrum_chart)
        spectrum_view.setObjectName("nir_spectrum_chart")
        spectrum_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        spectrum_view.setMinimumHeight(450)
        self.spectrum_chart = spectrum_chart
        chart_layout.addWidget(spectrum_view)
        top.addWidget(chart_panel, 3)

        summary_panel = QWidget()
        summary_panel.setObjectName("settings_panel")
        summary = QVBoxLayout(summary_panel)
        summary.setContentsMargins(10, 10, 10, 10)
        summary.setSpacing(8)
        summary_title = QLabel("Current Reading")
        summary_title.setProperty("class", "section_title")
        summary.addWidget(summary_title)
        for label, value in [
            ("Moisture Content", ""),
            ("Quality", ""),
        ]:
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
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setMinimumHeight(360)
        table.horizontalHeader().setSectionsMovable(False)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        table.verticalHeader().setDefaultSectionSize(34)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
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
        if line.startswith("NIR_SCAN_STATUS:"):
            status = line.partition(":")[2].strip().upper()
            self.set_scanning_state(
                status in ("SCANNING", "WAITING", "MEASURING")
            )
        elif line.startswith("NIR_SCAN_ERROR:"):
            self.set_scanning_state(False)
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
        points = [
            QPointF(reading.wavelength_nm, reading.value)
            for reading in self.readings
            if reading.value is not None
        ]
        self.spectrum_series.replace(points)

    def append_reading_row(self, formatted_line):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, reading in enumerate(self.readings):
            value = "--" if reading.value is None else f"{reading.value:.2f}"
            reading_item = QLabel(value)
            reading_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, column, reading_item)
        self.table.scrollToBottom()

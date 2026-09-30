# main_window.py

import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QScrollArea,
    QFrame,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QTableWidget,
)

from PySide6.QtCore import Qt, QTimer

try:
    from .animated_button import AnimatedButton
    from .camera import CameraPage
    from .dashboard import Dashboard
    from .nir_analysis import NIRAnalysisPage
    from .results import ResultsPage
    from .settings import SettingsPage
    from .servo import ServoPage
    from .styles import APP_STYLE
except ImportError:  # pragma: no cover - direct script execution
    from animated_button import AnimatedButton
    from camera import CameraPage
    from dashboard import Dashboard
    from nir_analysis import NIRAnalysisPage
    from results import ResultsPage
    from settings import SettingsPage
    from servo import ServoPage
    from styles import APP_STYLE


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "PhenoCoater - Cacao Seed Sorting & Grading System"
        )

        self.resize(1400, 850)

        self.setMinimumSize(640, 480)

        self.setup_ui()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if hasattr(self, "dashboard_page"):
            QTimer.singleShot(
                0,
                self.dashboard_page.update_responsive_layout,
            )

    def setup_ui(self):

        # =====================================
        # CENTRAL WIDGET
        # =====================================

        central_widget = QWidget()
        central_widget.setObjectName("central_widget")

        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =====================================
        # SIDEBAR
        # =====================================

        sidebar = QWidget()

        sidebar.setObjectName("sidebar")

        sidebar.setFixedWidth(230)

        sidebar_layout = QVBoxLayout(sidebar)

        sidebar_layout.setContentsMargins(
            15, 25, 15, 20
        )

        sidebar_layout.setSpacing(8)

        # LOGO / TITLE

        logo_title = QLabel("PHENOCOATER")

        logo_title.setObjectName("logo_title")

        logo_title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        sidebar_layout.addWidget(logo_title)

        logo_subtitle = QLabel(
            "Cacao Seed Sorting\n& Grading System"
        )

        logo_subtitle.setObjectName("logo_subtitle")

        logo_subtitle.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        sidebar_layout.addWidget(logo_subtitle)

        sidebar_layout.addSpacing(30)

        # MENU BUTTONS

        self.dashboard_button = self.create_menu_button("▦", "Dashboard")
        self.camera_button = self.create_menu_button("◉", "Camera")
        self.nir_button = self.create_menu_button("≋", "NIR Analysis")
        self.servo_button = self.create_menu_button("◉", "Servo")
        self.results_button = self.create_menu_button("☷", "Results")
        self.settings_button = self.create_menu_button("⚙", "Settings")

        self.menu_buttons = [
            self.dashboard_button,
            self.camera_button,
            self.nir_button,
            self.servo_button,
            self.results_button,
            self.settings_button,
        ]

        for button in self.menu_buttons:

            button.setCheckable(True)

            sidebar_layout.addWidget(button)

        self.dashboard_button.setChecked(True)

        sidebar_layout.addStretch()

        # SYSTEM STATUS

        self.status_text = QLabel(
            "SYSTEM NOT CONNECTED"
        )

        self.status_text.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.status_text.setStyleSheet(
            """
            color: #c0392b;
            font-size: 12px;
            font-weight: bold;
            padding: 10px;
            """
        )

        sidebar_layout.addWidget(self.status_text)

        # =====================================
        # RIGHT SIDE
        # =====================================

        right_side = QWidget()
        right_side.setObjectName("right_side")

        right_layout = QVBoxLayout(right_side)

        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # =====================================
        # HEADER
        # =====================================

        header = QWidget()

        header.setObjectName("header")

        header.setFixedHeight(70)

        header_layout = QHBoxLayout(header)

        header_layout.setContentsMargins(
            25, 10, 25, 10
        )

        page_title = QLabel(
            "PhenoCoater Control Panel"
        )

        page_title.setObjectName("page_title")

        header_layout.addWidget(page_title)

        header_layout.addStretch()

        right_layout.addWidget(header)

        # =====================================
        # CONTENT
        # =====================================

        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")

        self.dashboard_page = Dashboard()
        self.dashboard_page.camera_status_changed.connect(self.update_system_status)
        self.update_system_status("NOT CONNECTED")

        dashboard_scroll = QScrollArea()
        dashboard_scroll.setObjectName("dashboard_scroll")
        dashboard_scroll.setWidgetResizable(True)
        dashboard_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        dashboard_scroll.setWidget(self.dashboard_page)

        self.pages.addWidget(
            dashboard_scroll
        )

        camera_scroll = QScrollArea()
        camera_scroll.setObjectName("camera_scroll")
        camera_scroll.setWidgetResizable(True)
        camera_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        camera_scroll.setWidget(CameraPage(camera_controller=self.dashboard_page))

        self.pages.addWidget(camera_scroll)

        nir_scroll = QScrollArea()
        nir_scroll.setObjectName("nir_scroll")
        nir_scroll.setWidgetResizable(True)
        nir_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.nir_page = NIRAnalysisPage()
        self.dashboard_page.nir_message_received.connect(self.nir_page.append_serial_line)
        self.nir_page.scan_requested.connect(self.dashboard_page.set_nir_scanning)
        nir_scroll.setWidget(self.nir_page)
        self.pages.addWidget(nir_scroll)

        servo_scroll = QScrollArea()
        servo_scroll.setObjectName("servo_scroll")
        servo_scroll.setWidgetResizable(True)
        servo_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.servo_page = ServoPage()
        self.servo_page.angle_requested.connect(self.dashboard_page.set_servo_angle)
        self.servo_page.sweep_config_requested.connect(
            self.dashboard_page.set_servo_sweep_config
        )
        self.servo_page.sweep_requested.connect(self.dashboard_page.set_servo_sweeping)
        self.dashboard_page.servo_status_received.connect(
            self.servo_page.set_motor_status
        )
        self.dashboard_page.servo_sweep_status_received.connect(
            self.servo_page.set_sweep_status
        )
        servo_scroll.setWidget(self.servo_page)
        self.pages.addWidget(servo_scroll)

        results_scroll = QScrollArea()
        results_scroll.setObjectName("results_scroll")
        results_scroll.setWidgetResizable(True)
        results_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        results_scroll.setWidget(ResultsPage())
        self.pages.addWidget(results_scroll)

        settings_scroll = QScrollArea()
        settings_scroll.setObjectName("settings_scroll")
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        settings_scroll.setWidget(SettingsPage(self.dashboard_page))

        self.pages.addWidget(settings_scroll)

        right_layout.addWidget(self.pages)

        # =====================================
        # ADD EVERYTHING
        # =====================================

        main_layout.addWidget(sidebar)

        main_layout.addWidget(right_side)

        # =====================================
        # BUTTON CONNECTIONS
        # =====================================

        self.dashboard_button.clicked.connect(
            lambda: self.change_page(0)
        )

        self.camera_button.clicked.connect(
            lambda: self.change_page(1)
        )

        self.nir_button.clicked.connect(
            lambda: self.change_page(2)
        )

        self.results_button.clicked.connect(
            lambda: self.change_page(4)
        )

        self.settings_button.clicked.connect(
            lambda: self.change_page(5)
        )

        self.servo_button.clicked.connect(
            lambda: self.change_page(3)
        )

    def change_page(self, index):

        self.pages.setCurrentIndex(index)

        for button in self.menu_buttons:
            button.setChecked(False)

        self.menu_buttons[index].setChecked(True)

    def update_system_status(self, state):
        connected = state == "CONNECTED"
        status_text = "SYSTEM CONNECTED" if connected else "SYSTEM NOT CONNECTED"

        self.status_text.setText(status_text)

        color = "#2e7d4f" if connected else "#c0392b"
        self.status_text.setStyleSheet(
            f"""
            color: {color};
            font-size: 12px;
            font-weight: bold;
            padding: 10px;
            """
        )

    def create_menu_button(self, icon, label):

        button = AnimatedButton(f"{icon}   {label}")
        button.setProperty("class", "menu_button")
        button.setObjectName("menu_button")
        return button

    def create_placeholder(self, title, description):

        page = QWidget()

        layout = QVBoxLayout(page)

        layout.setContentsMargins(50, 50, 50, 50)

        title_label = QLabel(title)

        title_label.setObjectName("page_title")

        description_label = QLabel(description)

        description_label.setStyleSheet(
            """
            color: #6b7280;
            font-size: 15px;
            """
        )

        layout.addWidget(title_label)

        layout.addWidget(description_label)

        layout.addStretch()

        return page

    def create_camera_page(self):
        return CameraPage()

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 30)
        layout.setSpacing(20)

        title_label = QLabel("Camera")
        title_label.setObjectName("page_title")
        subtitle = QLabel("Live seed inspection and capture controls")
        subtitle.setObjectName("settings_description")
        layout.addWidget(title_label)
        layout.addWidget(subtitle)

        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        preview = QWidget()
        preview.setObjectName("settings_panel")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(20, 20, 20, 20)

        preview_title = QLabel("Live Camera Feed")
        preview_title.setProperty("class", "section_title")
        preview_box = QLabel("No camera connected")
        preview_box.setObjectName("main_camera_frame")
        preview_box.setMinimumHeight(320)
        preview_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(preview_box)

        status_panel = QWidget()
        status_panel.setObjectName("settings_panel")
        status_layout = QVBoxLayout(status_panel)
        status_layout.setContentsMargins(20, 20, 20, 20)
        status_layout.setSpacing(12)

        status_title = QLabel("Camera Connection")
        status_title.setProperty("class", "section_title")
        status_layout.addWidget(status_title)

        status_values = [
            ("Camera source", "Built-in laptop camera"),
            ("Capture mode", "Manual capture"),
            ("Connection status", "Connected"),
            ("Exposure mode", "Automatic"),
        ]

        for label, value in status_values:
            row = QHBoxLayout()
            name = QLabel(label)
            name.setStyleSheet("color: #6b7280; font-weight: 600;")
            val = QLabel(value)
            val.setStyleSheet("font-weight: bold;")
            row.addWidget(name)
            row.addStretch()
            row.addWidget(val)
            status_layout.addLayout(row)

        inspection_title = QLabel("Current Inspection")
        inspection_title.setProperty("class", "section_title")
        status_layout.addWidget(inspection_title)

        inspection_values = [
            ("Appearance", "GOOD", "Healthy-looking cacao seed"),
            ("Moisture", "Ideal Moisture", "6.0-7.5%"),
            ("Seed size / grade", "Premium", "92 seeds per 100 g"),
        ]

        for label, value, detail in inspection_values:
            row = QVBoxLayout()
            heading = QLabel(label)
            heading.setStyleSheet("color: #6b7280; font-size: 12px;")
            result = QLabel(value)
            result.setStyleSheet("color: #2e7d4f; font-size: 16px; font-weight: bold;")
            explanation = QLabel(detail)
            explanation.setStyleSheet("color: #6b7280; font-size: 11px;")
            explanation.setWordWrap(True)
            row.addWidget(heading)
            row.addWidget(result)
            row.addWidget(explanation)
            status_layout.addLayout(row)

        category_legend = QLabel(
            "Appearance categories: Good, Moldy, Slanty / Deformed, Germinated, "
            "Insect-Damaged, Black, Flat, Double / Fused"
        )
        category_legend.setStyleSheet("color: #6b7280; font-size: 11px;")
        category_legend.setWordWrap(True)
        status_layout.addWidget(category_legend)

        thresholds = QLabel(
            "Moisture: Brittle / Too Dry < 6.0% | Ideal 6.0-7.5% | "
            "Near Excessive / Too Moist > 7.5%\n"
            "Seeds per 100 g: Premium 80-100 | Standard 101-120 | Small > 120"
        )
        thresholds.setStyleSheet("color: #6b7280; font-size: 11px;")
        thresholds.setWordWrap(True)
        status_layout.addWidget(thresholds)
        status_layout.addStretch()

        top_row.addWidget(preview, 3)
        top_row.addWidget(status_panel, 2)
        layout.addLayout(top_row)

        controls = QHBoxLayout()
        controls.addStretch()
        start_btn = AnimatedButton("START CAPTURE")
        start_btn.setObjectName("start_capture_button")
        stop_btn = AnimatedButton("STOP CAPTURE")
        stop_btn.setObjectName("stop_capture_button")
        controls.addWidget(start_btn)
        controls.addWidget(stop_btn)
        layout.addLayout(controls)

        stats = QWidget()
        stats.setObjectName("settings_panel")
        stats_layout = QGridLayout(stats)
        stats_layout.setContentsMargins(20, 20, 20, 20)
        stats_layout.setHorizontalSpacing(20)
        stats_layout.setVerticalSpacing(10)

        stats_title = QLabel("Capture Summary")
        stats_title.setProperty("class", "section_title")
        stats_layout.addWidget(stats_title, 0, 0, 1, 2)

        items = [
            ("Seeds detected", "76"),
            ("Frame quality", "94%"),
            ("Focus", "Stable"),
            ("Capture trigger", "Ready"),
        ]
        for idx, (name, value) in enumerate(items):
            label = QLabel(name)
            label.setStyleSheet("color: #6b7280; font-size: 12px;")
            value_label = QLabel(value)
            value_label.setStyleSheet("font-size: 22px; font-weight: bold;")
            row = idx // 2 + 1
            column = (idx % 2) * 2
            stats_layout.addWidget(label, row, column)
            stats_layout.addWidget(value_label, row, column + 1)

        layout.addWidget(stats)

        pipeline = QWidget()
        pipeline.setObjectName("settings_panel")
        pipeline_layout = QGridLayout(pipeline)
        pipeline_layout.setContentsMargins(20, 16, 20, 16)
        pipeline_layout.setHorizontalSpacing(24)
        pipeline_layout.setVerticalSpacing(4)

        pipeline_title = QLabel("PhenoCoater Analysis Workflow")
        pipeline_title.setProperty("class", "section_title")
        pipeline_layout.addWidget(pipeline_title, 0, 0, 1, 3)

        pipeline_items = [
            ("Appearance detection", "Camera", "YOLO", "Defect class"),
            ("Moisture analysis", "NIR sensor", "PLS", "Moisture level"),
            ("Size grading", "Weight", "Count per weight", "Grade"),
        ]
        for column, (category, sensor, model, output) in enumerate(pipeline_items):
            category_label = QLabel(category)
            category_label.setStyleSheet("font-weight: bold; color: #173f2a;")
            flow_label = QLabel(f"{sensor}  ->  {model}  ->  {output}")
            flow_label.setStyleSheet("color: #6b7280; font-size: 12px;")
            flow_label.setWordWrap(True)
            pipeline_layout.addWidget(category_label, 1, column)
            pipeline_layout.addWidget(flow_label, 2, column)

        layout.addWidget(pipeline)
        layout.addStretch()
        return page

    def create_nir_page(self):
        return NIRAnalysisPage()

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 30)
        layout.setSpacing(20)

        title_label = QLabel("NIR Analysis")
        title_label.setObjectName("page_title")
        subtitle = QLabel("Spectral scan and moisture estimation")
        subtitle.setObjectName("settings_description")
        layout.addWidget(title_label)
        layout.addWidget(subtitle)

        top = QHBoxLayout()
        top.setSpacing(20)

        chart_panel = QWidget()
        chart_panel.setObjectName("settings_panel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(20, 20, 20, 20)
        chart_label = QLabel("Spectral Response")
        chart_label.setProperty("class", "section_title")
        chart_layout.addWidget(chart_label)

        spectrum = QWidget()
        spectrum.setStyleSheet("background: #f4f6f8; border: 1px solid #dfe3e7; border-radius: 12px;")
        spectrum_layout = QHBoxLayout(spectrum)
        spectrum_layout.setContentsMargins(15, 15, 15, 15)
        bars = [40, 57, 75, 95, 68, 82, 88, 72, 61, 48]
        for height in bars:
            bar = QFrame()
            bar.setStyleSheet(f"background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2e7d4f, stop:1 #6bc38a); border-radius: 6px; max-height: {height}px;")
            bar.setFixedHeight(height * 2)
            bar.setFixedWidth(18)
            spectrum_layout.addWidget(bar)
        chart_layout.addWidget(spectrum)

        top.addWidget(chart_panel, 3)

        summary_panel = QWidget()
        summary_panel.setObjectName("settings_panel")
        summary = QVBoxLayout(summary_panel)
        summary.setContentsMargins(20, 20, 20, 20)
        summary.setSpacing(12)
        summary_title = QLabel("Current Reading")
        summary_title.setProperty("class", "section_title")
        summary.addWidget(summary_title)

        for label, value in [
            ("Moisture", "11.8%"),
            ("Shell Content", "8.4%"),
            ("Protein Index", "0.91"),
            ("Quality Match", "High"),
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
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Wavelength", "Absorbance", "Moisture", "Status"])
        data = [
            ("980 nm", "0.61", "11.2%", "OK"),
            ("1200 nm", "0.74", "11.7%", "OK"),
            ("1450 nm", "0.98", "12.0%", "OK"),
            ("1700 nm", "0.68", "11.5%", "OK"),
        ]
        table.setRowCount(len(data))
        for row, values in enumerate(data):
            for col, value in enumerate(values):
                item = QLabel(value)
                item.setAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setCellWidget(row, col, item)
        table.setMinimumHeight(180)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)

        btns = QHBoxLayout()
        btns.addStretch()
        scan_btn = AnimatedButton("RUN SCAN")
        scan_btn.setObjectName("settings_save_button")
        export_btn = AnimatedButton("EXPORT REPORT")
        export_btn.setObjectName("settings_reset_button")
        btns.addWidget(scan_btn)
        btns.addWidget(export_btn)
        layout.addLayout(btns)

        return page

    def create_results_page(self):
        return ResultsPage()

        page = QWidget()
        layout = QVBoxLayout(page)
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
        cards = [
            ("Total Seed", "342"),
            ("Accepted", "291"),
            ("Rejected", "18"),
            ("Pass Rate", "85.1%"),
        ]
        for idx, (label, value) in enumerate(cards):
            card = QFrame()
            card.setObjectName("settings_panel")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 18, 18, 18)
            name = QLabel(label)
            name.setStyleSheet("color: #6b7280; font-size: 12px;")
            val = QLabel(value)
            val.setStyleSheet("font-size: 24px; font-weight: bold;")
            card_layout.addWidget(name)
            card_layout.addWidget(val)
            summary_cards.addWidget(card, idx // 2, idx % 2)
        layout.addLayout(summary_cards)

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Seed ID", "Weight", "Moisture", "Quality", "Decision", "Time"])
        data = [
            ("#101", "22.4 g", "11.5%", "Premium", "ACCEPTED", "08:42"),
            ("#102", "21.9 g", "12.8%", "Class A", "ACCEPTED", "08:48"),
            ("#103", "20.1 g", "13.6%", "Class B", "REVIEW", "09:10"),
            ("#104", "18.8 g", "14.3%", "Reject", "REJECTED", "09:22"),
        ]
        table.setRowCount(len(data))
        for row, values in enumerate(data):
            for col, value in enumerate(values):
                item = QLabel(value)
                item.setAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setCellWidget(row, col, item)
        table.setMinimumHeight(220)
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
        return page

    def create_settings_page(self):
        return SettingsPage()

        page = QWidget()
        page.setObjectName("settings_page")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 30)
        layout.setSpacing(20)

        title_label = QLabel("Settings")
        title_label.setObjectName("page_title")

        description_label = QLabel(
            "Configure connections and sensor settings."
        )
        description_label.setObjectName("settings_description")

        layout.addWidget(title_label)
        layout.addWidget(description_label)

        connection_form = QFormLayout()
        connection_form.setHorizontalSpacing(25)
        connection_form.setVerticalSpacing(15)

        port_input = QLineEdit()
        port_input.setPlaceholderText("Example: COM3")
        connection_form.addRow("Arduino / ESP32 port", port_input)

        baud_input = QComboBox()
        baud_input.addItems(["9600", "115200", "230400"])
        baud_input.setCurrentText("115200")
        connection_form.addRow("Baud rate", baud_input)

        camera_input = QLineEdit()
        camera_input.setPlaceholderText("Example: 0 or camera URL")
        connection_form.addRow("Camera source", camera_input)

        model_input = QLineEdit()
        model_input.setPlaceholderText("Path to AI model file")
        connection_form.addRow("AI model path", model_input)

        connection_panel = QFrame()
        connection_panel.setObjectName("settings_panel")
        connection_panel.setLayout(connection_form)
        layout.addWidget(connection_panel)

        sensor_form = QFormLayout()
        sensor_form.setHorizontalSpacing(25)
        sensor_form.setVerticalSpacing(15)

        weight_input = QDoubleSpinBox()
        weight_input.setRange(-1000000, 1000000)
        weight_input.setDecimals(3)
        weight_input.setSuffix(" g")
        sensor_form.addRow("Load cell offset", weight_input)

        moisture_input = QDoubleSpinBox()
        moisture_input.setRange(-1000000, 1000000)
        moisture_input.setDecimals(3)
        sensor_form.addRow("Moisture offset", moisture_input)

        sensor_panel = QFrame()
        sensor_panel.setObjectName("settings_panel")
        sensor_panel.setLayout(sensor_form)
        layout.addWidget(sensor_panel)

        action_layout = QHBoxLayout()
        action_layout.addStretch()

        reset_button = AnimatedButton("RESET")
        reset_button.setObjectName("settings_reset_button")

        save_button = AnimatedButton("SAVE SETTINGS")
        save_button.setObjectName("settings_save_button")

        save_state = QLabel()
        save_state.setObjectName("settings_save_state")

        def reset_settings():
            port_input.clear()
            baud_input.setCurrentText("115200")
            camera_input.clear()
            model_input.clear()
            weight_input.setValue(0)
            moisture_input.setValue(0)
            save_state.setText("Settings reset")

        def save_settings():
            save_state.setText("Settings saved")

        reset_button.clicked.connect(reset_settings)
        save_button.clicked.connect(save_settings)

        action_layout.addWidget(save_state)
        action_layout.addWidget(reset_button)
        action_layout.addWidget(save_button)
        layout.addLayout(action_layout)
        layout.addStretch()

        return page


# ============================================
# START APPLICATION
# ============================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    app.setStyleSheet(APP_STYLE)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())
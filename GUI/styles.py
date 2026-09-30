# styles.py

APP_STYLE = """
QMainWindow {
    background-color: #f4f6f8;
}

#central_widget,
#right_side,
#pages,
#dashboard_scroll,
#dashboard {
    background-color: #f4f6f8;
}

#dashboard_scroll {
    border: none;
}

#settings_scroll,
#settings_page,
#camera_scroll,
#nir_scroll,
#servo_scroll,
#results_scroll,
#camera_page,
#nir_analysis_page,
#servo_page,
#results_page {
    background-color: #f4f6f8;
    border: none;
}

#camera_page {
    background-color: #f4fbf5;
}

#nir_analysis_page {
    background-color: #f4f8fc;
}

#servo_page {
    background-color: #f4fbf5;
}

#results_page {
    background-color: #fff9f0;
}

QWidget {
    font-family: "Segoe UI";
    color: #202124;
}

/* Sidebar */

#sidebar {
    background-color: #173f2a;
}

#logo_title {
    color: white;
    font-size: 22px;
    font-weight: bold;
}

#logo_subtitle {
    color: #c8d8ce;
    font-size: 11px;
}

QPushButton {
    border: none;
    border-radius: 8px;
    padding: 12px;
    text-align: left;
    font-size: 14px;
    color: #dce9e1;
    background-color: transparent;
}

#menu_button {
    font-family: "Segoe UI Symbol", "Segoe UI";
    font-size: 14px;
    min-height: 42px;
}

QPushButton:hover {
    background-color: #245b3d;
}

QPushButton:checked {
    background-color: #2e704b;
    color: white;
    font-weight: bold;
}

/* Header */

#header {
    background-color: white;
    border-bottom: 1px solid #dddddd;
}

#page_title {
    font-size: 24px;
    font-weight: bold;
}

#system_status {
    color: #c0392b;
    font-weight: bold;
}

/* Cards */

.card {
    background-color: white;
    border: 1px solid #e2e5e8;
    border-radius: 12px;
}

#settings_panel {
    background-color: white;
    border: 1px solid #e2e5e8;
    border-radius: 12px;
    padding: 20px;
}

#servo_motor_panel {
    background-color: white;
    border: 1px solid #e2e5e8;
    border-radius: 8px;
}

#servo_angle_value {
    color: #173f2a;
    font-size: 32px;
    font-weight: bold;
}

#servo_status {
    color: #a26712;
    font-size: 11px;
    font-weight: bold;
}

QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox {
    min-height: 34px;
    padding: 4px 8px;
    border: 1px solid #cfd5da;
    border-radius: 6px;
    background-color: white;
}

#camera_toggle_button {
    background-color: #2e7d4f;
    color: white;
    font-weight: bold;
    min-width: 140px;
}

#camera_toggle_button[camera_running="true"] {
    background-color: #d9534f;
}

#camera_toggle_button[camera_running="true"]:hover {
    background-color: #b94340;
}

#start_capture_button,
#settings_save_button {
    background-color: #2e7d4f;
    color: white;
    font-weight: bold;
    text-align: center;
}

#start_capture_button:pressed,
#settings_save_button:pressed,
#camera_toggle_button:pressed {
    background-color: #24643e;
}

#stop_capture_button,
#settings_reset_button {
    background-color: #d9534f;
    color: white;
    font-weight: bold;
    text-align: center;
}

#stop_capture_button:hover,
#settings_reset_button:hover {
    background-color: #b94340;
}

#stop_capture_button:pressed,
#settings_reset_button:pressed {
    background-color: #a83232;
}

#camera_toggle_button:hover {
    background-color: #24643e;
}

#settings_save_button {
    background-color: #2e7d4f;
    color: white;
    font-weight: bold;
    text-align: center;
}

#settings_reset_button {
    background-color: #d9534f;
    color: white;
    font-weight: bold;
    text-align: center;
}

#settings_save_state {
    color: #2e7d4f;
    font-weight: bold;
}

#settings_description {
    color: #6b7280;
    font-size: 13px;
}

.card_title {
    color: #6b7280;
    font-size: 13px;
}

.card_value {
    font-size: 25px;
    font-weight: bold;
}

.card_unit {
    color: #6b7280;
    font-size: 13px;
}

/* Section titles */

.section_title {
    font-size: 18px;
    font-weight: bold;
}

/* Camera */

QLabel#camera_frame {
    background-color: #e8f5e9;
    border: 1px solid #a8d5b5;
    border-radius: 12px;
    color: #2e7d4f;
    font-size: 16px;
    font-weight: bold;
    padding: 16px;
    qproperty-wordWrap: true;
}

QLabel#main_camera_frame {
    background-color: #e8f5e9;
    border: 1px solid #a8d5b5;
    border-radius: 12px;
    color: #2e7d4f;
    font-size: 16px;
    font-weight: bold;
    padding: 16px;
    qproperty-wordWrap: true;
}

/* Buttons */

#start_button {
    background-color: #2e7d4f;
    color: white;
    font-weight: bold;
    text-align: center;
}

#start_button:hover {
    background-color: #24643e;
}

#stop_button {
    background-color: #d9534f;
    color: white;
    font-weight: bold;
    text-align: center;
}

#stop_button:hover {
    background-color: #b94340;
}

/* Table */

QTableWidget {
    background-color: white;
    border: 1px solid #e2e5e8;
    border-radius: 10px;
    gridline-color: #eeeeee;
}

QHeaderView::section {
    background-color: #f1f3f5;
    padding: 10px;
    border: none;
    font-weight: bold;
}

QTableWidget#nir_table {
    background-color: #ffffff;
    alternate-background-color: #f7fbf8;
}

QTableWidget#nir_table QHeaderView::section,
QTableWidget#nir_table QTableCornerButton::section,
QTableWidget#dashboard_results_table QHeaderView::section,
QTableWidget#dashboard_results_table QTableCornerButton::section,
QTableWidget#results_table QHeaderView::section,
QTableWidget#results_table QTableCornerButton::section {
    background-color: #dcefe2;
    color: #173f2a;
    border: 1px solid #c7dfce;
    padding: 10px;
    font-weight: bold;
}

QTableWidget#dashboard_results_table,
QTableWidget#results_table {
    background-color: #ffffff;
    alternate-background-color: #f7fbf8;
}

/* General labels */

.info_label {
    color: #6b7280;
}

.result_good {
    color: #2e7d4f;
    font-weight: bold;
}

.result_warning {
    color: #d28b00;
    font-weight: bold;
}

.result_bad {
    color: #c0392b;
    font-weight: bold;
}
"""
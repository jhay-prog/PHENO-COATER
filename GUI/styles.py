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
    color: #173f2a;
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

#admin_button {
    color: #173f2a;
    background-color: #f4f6f8;
    border: 1px solid #d8dee3;
    border-radius: 8px;
    font-family: "Segoe UI Symbol", "Segoe UI";
    font-size: 19px;
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
    padding: 0;
    text-align: center;
}

#admin_button:hover {
    background-color: #e8f5e9;
}

QMainWindow#admin_control_panel,
#admin_panel_central,
#admin_panel_content,
#admin_pages,
#admin_page_scroll,
#admin_page_scroll QWidget#qt_scrollarea_viewport,
#admin_system_overview_page,
#admin_process_monitor_page {
    background-color: #f4f6f8;
}

#admin_account_creation_page {
    background-color: #ffffff;
}

#pricing_settings_page {
    background-color: #f5faf6;
}

#pricing_scroll,
#pricing_scroll QWidget#qt_scrollarea_viewport,
#pricing_scroll > QWidget {
    background-color: #f5faf6;
    border: none;
}

#pricing_panel {
    background-color: #ffffff;
    border: 1px solid #d5e6d9;
    border-radius: 14px;
}

#pricing_panel_heading {
    background-color: #eaf7ee;
    border: 1px solid #cfe7d5;
    border-radius: 10px;
    color: #173f2a;
    font-size: 16px;
    font-weight: 700;
    padding: 12px;
}

#pricing_section_title {
    color: #173f2a;
    font-size: 15px;
    font-weight: bold;
}

#pricing_control_label,
#pricing_result_label {
    color: #355d49;
    font-weight: 600;
}

#pricing_note {
    color: #5b7065;
    font-size: 12px;
}

#pricing_effect_value {
    color: #255e3a;
    font-weight: 700;
}

#pricing_result_value,
#pricing_total_result {
    color: #173f2a;
    font-weight: 700;
}

#pricing_total_result {
    background-color: #edf9f0;
    border: 1px solid #b7d8bf;
    border-radius: 8px;
    color: #173f2a;
    font-size: 18px;
    padding: 12px;
}

QDoubleSpinBox#pricing_base_price_input,
QDoubleSpinBox#pricing_moisture_score_input,
QDoubleSpinBox#pricing_pns_score_input,
QDoubleSpinBox#pricing_weight_input {
    background-color: #ffffff;
    border: 1px solid #cdded6;
    border-radius: 8px;
    color: #173f2a;
    selection-background-color: #cfe9d6;
    selection-color: #173f2a;
}

QDoubleSpinBox#pricing_base_price_input:hover,
QDoubleSpinBox#pricing_moisture_score_input:hover,
QDoubleSpinBox#pricing_pns_score_input:hover,
QDoubleSpinBox#pricing_weight_input:hover {
    border: 1px solid #9fc7a9;
}

QSlider#pricing_effect_slider::groove:horizontal {
    background-color: #dfeee3;
    border: 1px solid #b5d0bb;
    border-radius: 5px;
    height: 10px;
}

QSlider#pricing_effect_slider::sub-page:horizontal {
    background-color: #66b67d;
    border-radius: 5px;
}

QSlider#pricing_effect_slider::add-page:horizontal {
    background-color: #e7f3eb;
    border-radius: 5px;
}

QSlider#pricing_effect_slider::handle:horizontal {
    background-color: #2e7d4f;
    border: 2px solid white;
    border-radius: 8px;
    margin: -5px 0;
    width: 16px;
}

QScrollArea#admin_page_scroll {
    border: none;
}

#admin_sidebar {
    background-color: #173f2a;
}

#admin_sidebar #admin_navigation_button {
    color: #dce9e1;
    background-color: transparent;
    font-size: 13px;
    min-height: 40px;
}

#admin_sidebar #admin_navigation_button:hover {
    background-color: #245b3d;
}

#admin_sidebar #admin_navigation_button:checked {
    background-color: #2e704b;
    color: white;
    font-weight: bold;
}

#admin_header {
    background-color: white;
    border-bottom: 1px solid #dddddd;
}

#admin_log_output {
    background-color: white;
    color: #173f2a;
    border: 1px solid #e2e5e8;
    border-radius: 8px;
    selection-background-color: #dcefe2;
    selection-color: #173f2a;
}

QDialog#admin_login_dialog {
    background-color: #f4f6f8;
}

QDialog#admin_password_reset_dialog {
    background-color: #ffffff;
}

QMessageBox#admin_delete_confirmation_dialog {
    background-color: #ffffff;
}

QMessageBox#admin_delete_confirmation_dialog QPushButton#admin_delete_confirm_button {
    background-color: #d9534f;
    border: 1px solid #d9534f;
    color: #ffffff;
    font-weight: bold;
    text-align: center;
}

QMessageBox#admin_delete_confirmation_dialog QPushButton#admin_delete_confirm_button:hover {
    background-color: #fde9e8;
    border-color: #e6a09d;
    color: #8f2925;
}

QMessageBox#admin_delete_confirmation_dialog QPushButton#admin_delete_cancel_button {
    background-color: #2e7d4f;
    border: 1px solid #2e7d4f;
    color: #ffffff;
    font-weight: bold;
    text-align: center;
}

QMessageBox#admin_delete_confirmation_dialog QPushButton#admin_delete_cancel_button:hover {
    background-color: #dcefe2;
    border-color: #a8d5b5;
    color: #173f2a;
}

QDialog#admin_login_dialog QLabel,
QDialog#admin_password_reset_dialog QLabel,
QMessageBox#admin_delete_confirmation_dialog QLabel {
    color: #173f2a;
    background-color: transparent;
}

QDialog#admin_password_reset_dialog QLineEdit {
    color: #173f2a;
    background-color: #ffffff;
}

QDialog#admin_password_reset_dialog QPushButton#admin_password_reset_save_button {
    background-color: #2e7d4f;
    border: 1px solid #2e7d4f;
    color: #ffffff;
    font-weight: bold;
    text-align: center;
}

QDialog#admin_password_reset_dialog QPushButton#admin_password_reset_save_button:hover {
    background-color: #dcefe2;
    border-color: #a8d5b5;
    color: #173f2a;
}

QDialog#admin_password_reset_dialog QPushButton#admin_password_reset_save_button:pressed {
    background-color: #1f5c38;
    border-color: #17452b;
}

QDialog#admin_password_reset_dialog QPushButton#admin_password_reset_cancel_button {
    background-color: #d9534f;
    border: 1px solid #d9534f;
    color: #ffffff;
    font-weight: bold;
    text-align: center;
}

QDialog#admin_password_reset_dialog QPushButton#admin_password_reset_cancel_button:hover {
    background-color: #fde9e8;
    border-color: #e6a09d;
    color: #8f2925;
}

QDialog#admin_password_reset_dialog QPushButton#admin_password_reset_cancel_button:pressed {
    background-color: #a83232;
    border-color: #8f2925;
}

QCheckBox#admin_show_password_checkbox {
    background-color: transparent;
    color: #173f2a;
    spacing: 8px;
}

QPushButton#create_admin_button {
    background-color: #2e7d4f;
    border: 1px solid #2e7d4f;
    color: white;
    font-weight: bold;
    text-align: center;
}

QPushButton#create_admin_button:hover {
    background-color: #dcefe2;
    border-color: #a8d5b5;
    color: #173f2a;
}

QPushButton#create_admin_button:pressed {
    background-color: #1f5c38;
    border-color: #17452b;
    padding-top: 13px;
    padding-bottom: 11px;
}

#admin_accounts_heading {
    font-size: 18px;
    font-weight: bold;
}

QFrame#admin_account_card {
    background-color: #ffffff;
    border: 1px solid #d8dee3;
    border-radius: 8px;
}

QFrame#admin_account_card QLabel {
    background-color: transparent;
}

#admin_account_username {
    font-weight: bold;
}

#admin_account_role,
#admin_accounts_empty {
    color: #6b7280;
}

QToolButton#admin_account_toggle_button,
QToolButton#admin_account_delete_button,
QToolButton#admin_account_reset_password_button {
    min-width: 34px;
    min-height: 34px;
    padding: 4px;
    border: 1px solid #cfd5da;
    border-radius: 6px;
    background-color: #ffffff;
}

QToolButton#admin_account_toggle_button:hover {
    background-color: #dcefe2;
}

QToolButton#admin_account_delete_button:hover {
    background-color: #fde9e8;
}

QToolButton#admin_account_reset_password_button:hover {
    background-color: #e8f0fe;
}

QPushButton#admin_login_submit_button,
QPushButton#admin_logout_button {
    background-color: #2e7d4f;
    border: 1px solid #2e7d4f;
    color: white;
    font-weight: bold;
    text-align: center;
}

QPushButton#admin_login_submit_button:hover,
QPushButton#admin_logout_button:hover {
    background-color: #24643e;
}

#admin_sidebar QPushButton#admin_logout_button {
    background-color: #2e7d4f;
    border: 1px solid #2e7d4f;
    color: white;
    text-align: center;
}

#admin_sidebar QPushButton#admin_logout_button:hover {
    background-color: #24643e;
}

QPushButton#admin_login_cancel_button {
    background-color: #e8f5e9;
    border: 1px solid #a8d5b5;
    color: #173f2a;
    text-align: center;
}

QPushButton#admin_login_cancel_button:hover {
    background-color: #dcefe2;
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
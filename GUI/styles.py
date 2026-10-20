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
    background-color: #f4fbf5;
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
    color: #dce9e1;
    font-family: "Segoe UI";
    font-size: 14px;
    font-weight: 600;
    min-height: 46px;
    padding: 12px 16px;
    text-align: left;
}

#menu_button:hover {
    background-color: #245b3d;
}

#menu_button:checked {
    background-color: #2e704b;
    color: #ffffff;
    font-weight: 700;
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
    background-color: #f4f7f5;
    font-family: "Segoe UI";
    font-size: 14px;
    color: #1d3428;
}

#pricing_scroll,
#pricing_scroll QWidget#qt_scrollarea_viewport,
#pricing_scroll > QWidget {
    background-color: #f4f7f5;
    border: none;
}

#bean_data_sheet_scroll,
#bean_data_sheet_scroll QWidget#qt_scrollarea_viewport,
#bean_data_sheet_scroll > QWidget,
#bean_data_sheet_page {
    background-color: #f4f7f5;
    border: none;
}

#bean_sheet_title {
    color: #173f2a;
    font-size: 30px;
    font-weight: 700;
}

#bean_sheet_description {
    color: #607267;
    font-size: 14px;
}

#bean_sheet_summary_card,
#bean_sheet_table_panel {
    background-color: #ffffff;
    border: 1px solid #dce5df;
    border-radius: 12px;
}

#bean_sheet_summary_title {
    color: #294d37;
    font-size: 13px;
    font-weight: 700;
}

#bean_sheet_summary_value {
    color: #607267;
    font-size: 14px;
}

#bean_sheet_table_title {
    color: #294d37;
    font-size: 15px;
    font-weight: 700;
    text-transform: uppercase;
}

QPushButton#bean_sheet_tab {
    background-color: #edf2ee;
    border: 1px solid #e0e8e2;
    border-radius: 8px;
    color: #43594a;
    font-size: 12px;
    font-weight: 600;
    min-height: 34px;
    padding: 6px 12px;
    text-align: center;
}

QPushButton#bean_sheet_tab:hover {
    background-color: #e1eee4;
}

QPushButton#bean_sheet_tab:checked {
    background-color: #e3f3e6;
    border-color: #a8d5b5;
    color: #1f5c38;
    font-weight: 700;
}

QTableWidget#bean_data_table {
    background-color: #ffffff;
    alternate-background-color: #f7faf8;
    border: 1px solid #dce5df;
    color: #294d37;
    gridline-color: #e7ece8;
    selection-background-color: #e3f3e6;
    selection-color: #173f2a;
}

QTableWidget#bean_data_table QHeaderView::section {
    background-color: #dff2e2;
    border: none;
    border-bottom: 1px solid #cbded0;
    color: #234b33;
    font-size: 12px;
    font-weight: 700;
    padding: 9px 7px;
}

#bean_sheet_empty_state {
    color: #718077;
    font-size: 13px;
    padding: 10px;
}

#pricing_settings_page #page_title {
    color: #173f2a;
    font-size: 30px;
    font-weight: 700;
}

#pricing_settings_page #settings_description {
    color: #607267;
    font-size: 14px;
}

#pricing_panel {
    background-color: #ffffff;
    border: 1px solid #dce5df;
    border-radius: 14px;
}

#pricing_panel_heading {
    background-color: #f1f6f2;
    border: 1px solid #e2ebe4;
    border-radius: 8px;
    color: #173f2a;
    font-size: 16px;
    font-weight: 700;
    padding: 12px 15px;
}

#pricing_section_title {
    color: #294d37;
    font-size: 15px;
    font-weight: 700;
    padding-top: 6px;
}

#pricing_control_label,
#pricing_result_label {
    color: #3e5648;
    font-size: 14px;
    font-weight: 600;
}

#pricing_form_label {
    color: #3e5648;
    font-size: 14px;
    font-weight: 600;
}

#pricing_note {
    color: #718077;
    font-size: 12px;
}

#pricing_effect_value {
    color: #287044;
    font-size: 15px;
    font-weight: 700;
}

#pricing_result_value {
    color: #234b33;
    font-size: 15px;
    font-weight: 700;
}

#pricing_results_divider {
    background-color: #e7ece8;
    border: none;
    max-height: 1px;
    min-height: 1px;
}

#pricing_total_result {
    background-color: #eaf4ed;
    border: 1px solid #cfe2d4;
    border-radius: 10px;
    color: #1b5b34;
    font-size: 26px;
    font-weight: 700;
    padding: 18px 14px;
}

#pricing_total_result[result_state="status"] {
    color: #68796f;
    font-size: 15px;
    font-weight: 600;
}

#pricing_save_inputs_button {
    background-color: #2e7d4f;
    border: 1px solid #2e7d4f;
    border-radius: 7px;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    min-height: 38px;
    padding: 8px 14px;
    text-align: center;
}

#pricing_save_inputs_button:hover {
    background-color: #24643e;
    border-color: #24643e;
}

#pricing_save_inputs_button:pressed {
    background-color: #1f5c38;
    border-color: #17452b;
}

QDoubleSpinBox#pricing_base_price_input,
QDoubleSpinBox#pricing_moisture_score_input,
QDoubleSpinBox#pricing_pns_score_input,
QDoubleSpinBox#pricing_weight_input,
QLineEdit#pricing_base_price_input,
QLineEdit#pricing_moisture_score_input,
QLineEdit#pricing_pns_score_input,
QLineEdit#pricing_weight_input {
    background-color: #ffffff;
    border: 1px solid #ccd8d0;
    border-radius: 7px;
    color: #20392b;
    font-size: 14px;
    min-height: 24px;
    padding: 8px 10px;
    selection-background-color: #cfe5d5;
    selection-color: #173f2a;
}

QDoubleSpinBox#pricing_base_price_input:hover,
QDoubleSpinBox#pricing_moisture_score_input:hover,
QDoubleSpinBox#pricing_pns_score_input:hover,
QDoubleSpinBox#pricing_weight_input:hover,
QLineEdit#pricing_base_price_input:hover,
QLineEdit#pricing_moisture_score_input:hover,
QLineEdit#pricing_pns_score_input:hover,
QLineEdit#pricing_weight_input:hover {
    border: 1px solid #86b695;
}

QDoubleSpinBox#pricing_base_price_input:focus,
QDoubleSpinBox#pricing_moisture_score_input:focus,
QDoubleSpinBox#pricing_pns_score_input:focus,
QDoubleSpinBox#pricing_weight_input:focus,
QLineEdit#pricing_base_price_input:focus,
QLineEdit#pricing_moisture_score_input:focus,
QLineEdit#pricing_pns_score_input:focus,
QLineEdit#pricing_weight_input:focus {
    border: 1px solid #43845a;
}

#pricing_input_suffix {
    color: #68796f;
    font-size: 13px;
}

QSlider#pricing_effect_slider::groove:horizontal {
    background-color: #e4ebe6;
    border: 1px solid #d4dfd7;
    border-radius: 4px;
    height: 8px;
}

QSlider#pricing_effect_slider::sub-page:horizontal {
    background-color: #4c9563;
    border-radius: 4px;
}

QSlider#pricing_effect_slider::add-page:horizontal {
    background-color: #e4ebe6;
    border-radius: 4px;
}

QSlider#pricing_effect_slider::handle:horizontal {
    background-color: #287044;
    border: 2px solid white;
    border-radius: 9px;
    margin: -6px 0;
    width: 18px;
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
    min-height: 36px;
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
    background-color: #ffffff;
    font-family: "Segoe UI";
}

QDialog#admin_login_dialog #admin_login_title {
    color: #173f2a;
    font-size: 24px;
    font-weight: 700;
}

QDialog#admin_login_dialog #admin_login_description {
    color: #66756c;
    font-size: 13px;
}

QDialog#admin_login_dialog QLabel {
    color: #344b3d;
    font-size: 13px;
    font-weight: 600;
}

QDialog#admin_login_dialog QLineEdit {
    min-height: 38px;
    padding: 7px 10px;
    border: 1px solid #cbd7ce;
    border-radius: 7px;
    background-color: #fbfcfb;
    color: #20392b;
    selection-background-color: #cfe5d5;
    selection-color: #173f2a;
}

QDialog#admin_login_dialog QLineEdit:focus {
    border: 1px solid #43845a;
    background-color: #ffffff;
}

QDialog#admin_login_dialog #admin_login_error {
    color: #b42318;
    font-size: 12px;
}

QDialog#admin_login_dialog QPushButton#admin_login_submit_button {
    min-width: 112px;
    min-height: 40px;
    padding: 8px 14px;
    background-color: #2e7d4f;
    border: 1px solid #2e7d4f;
    border-radius: 7px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    text-align: center;
}

QDialog#admin_login_dialog QPushButton#admin_login_submit_button:hover {
    background-color: #24643e;
    border-color: #24643e;
}

QDialog#admin_login_dialog QPushButton#admin_login_cancel_button {
    min-width: 84px;
    min-height: 40px;
    padding: 8px 14px;
    background-color: #ffffff;
    border: 1px solid #cbd7ce;
    border-radius: 7px;
    color: #344b3d;
    font-size: 13px;
    font-weight: 600;
    text-align: center;
}

QDialog#admin_login_dialog QPushButton#admin_login_cancel_button:hover {
    background-color: #f1f5f2;
    border-color: #9fb4a5;
}

QDialog#admin_password_reset_dialog {
    background-color: #ffffff;
}

QMessageBox#admin_delete_confirmation_dialog {
    background-color: #ffffff;
}

QMessageBox#camera_unavailable_dialog {
    background-color: #f4fbf5;
}

QMessageBox#camera_unavailable_dialog QLabel {
    color: #173f2a;
    background-color: transparent;
    font-size: 14px;
    font-weight: 600;
}

QPushButton#camera_unavailable_ok_button {
    min-width: 88px;
    min-height: 36px;
    background-color: #2e7d4f;
    border: 1px solid #2e7d4f;
    border-radius: 6px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    text-align: center;
}

QPushButton#camera_unavailable_ok_button:hover {
    background-color: #24643e;
    border-color: #24643e;
    color: #ffffff;
}

QPushButton#admin_delete_confirm_button {
    background-color: #d9534f;
    border: 1px solid #d9534f;
    color: #ffffff;
    font-weight: bold;
    text-align: center;
}

QPushButton#admin_delete_confirm_button:hover {
    background-color: #b52b27;
    border-color: #b52b27;
    color: #ffffff;
}

QPushButton#admin_delete_cancel_button {
    background-color: #2e7d4f;
    border: 1px solid #2e7d4f;
    color: #ffffff;
    font-weight: bold;
    text-align: center;
}

QPushButton#admin_delete_cancel_button:hover {
    background-color: #24643e;
    border-color: #24643e;
    color: #ffffff;
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

QToolButton#admin_account_delete_button {
    color: #b42318;
    border-color: #d9534f;
    background-color: #fff5f4;
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

#dashboard {
    background-color: #f4f7f5;
}

#dashboard_subtitle {
    color: #68796f;
    font-size: 14px;
}

QFrame#dashboard_metric_card,
QFrame#dashboard_camera_panel,
QFrame#dashboard_status_panel {
    background-color: #ffffff;
    border: 1px solid #dce5df;
    border-radius: 14px;
}

QFrame#dashboard_metric_card {
    border-top: 3px solid #43845a;
    border-radius: 12px;
}

QLabel#card_title {
    color: #68796f;
    font-size: 11px;
    font-weight: 700;
}

QLabel#card_value {
    color: #173f2a;
    font-size: 28px;
    font-weight: 700;
}

QLabel#card_unit {
    color: #68796f;
    font-size: 12px;
}

QLabel#section_title {
    color: #173f2a;
    font-size: 17px;
    font-weight: 700;
}

QLabel#dashboard_status_name {
    color: #435b4d;
    font-size: 13px;
    font-weight: 600;
}

QLabel#dashboard_status_value {
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
    padding: 5px 8px;
}

QLabel#dashboard_status_value[connection_state="connected"] {
    background-color: #e8f5ec;
    color: #24643e;
}

QLabel#dashboard_status_value[connection_state="disconnected"] {
    background-color: #fcefed;
    color: #a83232;
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
    color: #2e7d4f;
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

#camera_usage_button {
    background-color: #2e7d4f;
    color: white;
    font-weight: bold;
    min-width: 180px;
}

#camera_usage_button[camera_usage_enabled="false"] {
    background-color: #68796f;
}

#camera_usage_button[camera_usage_enabled="false"]:hover {
    background-color: #526158;
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
#camera_usage_button:pressed {
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

#camera_usage_button:hover {
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
    background-color: #17251d;
    border: 1px solid #2d4637;
    border-radius: 10px;
    color: #dce9e1;
    font-size: 15px;
    font-weight: 600;
    padding: 18px;
    qproperty-wordWrap: true;
}

QLabel#main_camera_frame {
    background-color: #f4fbf5;
    border: 1px solid #c7dfce;
    border-radius: 12px;
    color: #173f2a;
    font-size: 16px;
    font-weight: 700;
    padding: 16px;
    qproperty-wordWrap: true;
}

/* Buttons */

#start_button {
    background-color: #2e7d4f;
    border: 1px solid #2e7d4f;
    border-radius: 8px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    min-height: 42px;
    padding: 8px 18px;
    text-align: center;
}

#start_button:hover {
    background-color: #24643e;
    border-color: #24643e;
}

#stop_button {
    background-color: #ffffff;
    border: 1px solid #d9a7a3;
    border-radius: 8px;
    color: #a83232;
    font-size: 13px;
    font-weight: 700;
    min-height: 42px;
    padding: 8px 18px;
    text-align: center;
}

#stop_button:hover {
    background-color: #fcefed;
    border-color: #c77d77;
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
    color: #2e7d4f;
    font-weight: bold;
}

.result_bad {
    color: #c0392b;
    font-weight: bold;
}
"""
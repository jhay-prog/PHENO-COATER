from collections import Counter, deque
from time import perf_counter

import cv2
from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)
from .animated_button import AnimatedButton
from .ai_model import load_yolo_model
from .camera_controls import (
    CAMERA_CONTROL_DEFAULTS,
    CAMERA_FRAME_RATES,
    CAMERA_RESOLUTIONS,
    apply_camera_controls,
    apply_camera_stream_settings,
)


CLASS_NAMES = (
    "GOOD",
    "MOLDY",
    "SLANTY",
    "GERMINATED",
    "INSECT-DAMAGED",
    "BLACK",
    "FLAT",
    "DOUBLE",
)
CONFIDENCE_THRESHOLD = 0.50
STABILITY_WINDOW = 5


class CameraPage(QWidget):
    final_result_changed = Signal(str)
    EMEET_CAMERA_INDEX = 0

    def __init__(self, camera_source=EMEET_CAMERA_INDEX, model_path=None, camera_controller=None):
        super().__init__()
        self.setObjectName("camera_page")
        self.camera_source = camera_source
        self.model_path = model_path
        self.camera_controller = camera_controller
        self.camera_capture = None
        self.local_camera_controls = CAMERA_CONTROL_DEFAULTS.copy()
        self.local_camera_control_overrides = {}
        self.local_camera_stream_overrides = {}
        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self.update_camera_feed)
        self.model = None
        self.result_history = deque(maxlen=STABILITY_WINDOW)
        self.final_result = "NO DETECTION"
        self.last_detection = None
        self.last_frame = None
        self.fps = 0.0
        self.fps_frame_count = 0
        self.fps_started_at = perf_counter()
        self.bean_count = 0
        self.current_bean_id = 0
        self.camera_control_sliders = {}
        self.camera_control_values = CAMERA_CONTROL_DEFAULTS.copy()
        self.has_camera_controls_status_signal = False
        self.setup_ui()
        if camera_controller is not None:
            status_signal = getattr(
                camera_controller,
                "camera_controls_status_changed",
                None,
            )
            if status_signal is not None:
                status_signal.connect(self._set_camera_controls_status)
                self.has_camera_controls_status_signal = True
        if camera_controller is not None and getattr(
            camera_controller, "ai_model", None
        ) is not None:
            self.model = camera_controller.ai_model
            self.model_path = camera_controller.ai_model_path
        else:
            self.load_model(model_path)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)

        title_label = QLabel("Camera")
        title_label.setObjectName("page_title")
        subtitle = QLabel("Live seed inspection and capture controls")
        subtitle.setObjectName("settings_description")
        layout.addWidget(title_label)
        layout.addWidget(subtitle)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        controls_panel = QWidget()
        controls_panel.setObjectName("camera_controls_panel")
        self.camera_controls_panel = controls_panel
        controls_layout = QHBoxLayout(controls_panel)
        controls_layout.setContentsMargins(16, 14, 16, 14)
        controls_layout.setSpacing(20)

        lens_column = QFrame()
        lens_column.setObjectName("camera_control_group")
        lens_layout = QVBoxLayout(lens_column)
        lens_layout.setContentsMargins(14, 14, 14, 14)
        lens_layout.setSpacing(10)
        lens_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        exposure_column = QFrame()
        exposure_column.setObjectName("camera_control_group")
        exposure_layout = QVBoxLayout(exposure_column)
        exposure_layout.setContentsMargins(14, 14, 14, 14)
        exposure_layout.setSpacing(10)
        exposure_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        image_column = QFrame()
        image_column.setObjectName("camera_control_group")
        image_layout = QVBoxLayout(image_column)
        image_layout.setContentsMargins(14, 14, 14, 14)
        image_layout.setSpacing(10)
        image_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        controls_layout.addWidget(lens_column, 1)
        controls_layout.addWidget(exposure_column, 1)
        controls_layout.addWidget(image_column, 1)

        lens_title = QLabel("Lens")
        lens_title.setObjectName("camera_control_section_title")
        lens_layout.addWidget(lens_title)
        self.focus_auto_button, self.focus_manual_button = self._add_mode_buttons(
            lens_layout,
            "Focus",
            auto_selected=True,
            changed=self._set_focus_mode,
        )
        self._add_camera_slider(
            lens_layout,
            "Focus",
            "camera_focus_slider",
            cv2.CAP_PROP_FOCUS,
            0,
            255,
            CAMERA_CONTROL_DEFAULTS[cv2.CAP_PROP_FOCUS],
        )
        focus_range = QHBoxLayout()
        far_label = QLabel("Far")
        far_label.setObjectName("camera_control_hint")
        near_label = QLabel("Near")
        near_label.setObjectName("camera_control_hint")
        near_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.focus_far_label = far_label
        self.focus_near_label = near_label
        focus_range.addWidget(far_label)
        focus_range.addStretch()
        focus_range.addWidget(near_label)
        lens_layout.addLayout(focus_range)

        capture_title = QLabel("Capture")
        capture_title.setObjectName("camera_control_section_title")
        lens_layout.addWidget(capture_title)

        resolution_row = QHBoxLayout()
        resolution_row.addWidget(QLabel("Resolution"))
        self.resolution_selector = QComboBox()
        self.resolution_selector.setObjectName("camera_resolution_selector")
        self.resolution_selector.addItems(list(CAMERA_RESOLUTIONS))
        self.resolution_selector.setCurrentText("1080P")
        resolution_row.addStretch()
        resolution_row.addWidget(self.resolution_selector)
        lens_layout.addLayout(resolution_row)

        fps_row = QHBoxLayout()
        fps_row.addWidget(QLabel("FPS"))
        self.fps_selector = QComboBox()
        self.fps_selector.setObjectName("camera_fps_selector")
        self.fps_selector.addItems(
            [str(frame_rate) for frame_rate in CAMERA_FRAME_RATES]
        )
        self.fps_selector.setCurrentText("30")
        fps_row.addStretch()
        fps_row.addWidget(self.fps_selector)
        lens_layout.addLayout(fps_row)
        self.resolution_selector.currentTextChanged.connect(
            self._set_camera_resolution
        )
        self.fps_selector.currentTextChanged.connect(self._set_camera_fps)

        color_title = QLabel("Color")
        color_title.setObjectName("camera_control_section_title")
        exposure_layout.addWidget(color_title)
        self.exposure_auto_button, self.exposure_manual_button = (
            self._add_mode_buttons(
                exposure_layout,
                "Exposure",
                auto_selected=True,
                changed=self._set_exposure_mode,
            )
        )
        self._add_camera_slider(
            exposure_layout,
            "Exposure",
            "camera_exposure_slider",
            cv2.CAP_PROP_EXPOSURE,
            -13,
            0,
            CAMERA_CONTROL_DEFAULTS[cv2.CAP_PROP_EXPOSURE],
            suffix="EV",
        )
        self._add_camera_slider(
            exposure_layout,
            "Exposure gain",
            "camera_gain_slider",
            cv2.CAP_PROP_GAIN,
            0,
            255,
            CAMERA_CONTROL_DEFAULTS[cv2.CAP_PROP_GAIN],
        )

        flicker_row = QHBoxLayout()
        flicker_label = QLabel("Anti-flicker")
        self.flicker_selector = QComboBox()
        self.flicker_selector.setObjectName("camera_antiflicker_selector")
        self.flicker_selector.addItems(("50Hz", "60Hz"))
        self.flicker_selector.setCurrentText("60Hz")
        self.flicker_selector.setEnabled(False)
        self.flicker_selector.setToolTip(
            "This camera backend does not expose mains-frequency control."
        )
        flicker_row.addWidget(flicker_label)
        flicker_row.addStretch()
        flicker_row.addWidget(self.flicker_selector)
        exposure_layout.addLayout(flicker_row)

        self.white_balance_auto_button, self.white_balance_manual_button = (
            self._add_mode_buttons(
                image_layout,
                "White balance",
                auto_selected=True,
                changed=self._set_white_balance_mode,
            )
        )
        self._add_camera_slider(
            image_layout,
            "Temperature",
            "camera_white_balance_slider",
            cv2.CAP_PROP_WB_TEMPERATURE,
            2000,
            6500,
            CAMERA_CONTROL_DEFAULTS[cv2.CAP_PROP_WB_TEMPERATURE],
            suffix="K",
        )
        self.white_balance_slider.setEnabled(True)

        image_title = QLabel("Image")
        image_title.setObjectName("camera_control_section_title")
        image_layout.addWidget(image_title)

        for label, object_name, property_id in (
            ("Brightness", "camera_brightness_slider", cv2.CAP_PROP_BRIGHTNESS),
            ("Contrast", "camera_contrast_slider", cv2.CAP_PROP_CONTRAST),
            ("Color tone", "camera_hue_slider", cv2.CAP_PROP_HUE),
            ("Saturation", "camera_saturation_slider", cv2.CAP_PROP_SATURATION),
            ("Clarity", "camera_sharpness_slider", cv2.CAP_PROP_SHARPNESS),
        ):
            self._add_camera_slider(
                image_layout,
                label,
                object_name,
                property_id,
                0,
                255,
                CAMERA_CONTROL_DEFAULTS[property_id],
            )

        self.camera_controls_status = QLabel(
            "Controls apply when the camera starts."
        )
        self.camera_controls_status.setObjectName("camera_controls_status")
        self.camera_controls_status.setWordWrap(True)
        image_layout.addWidget(self.camera_controls_status)

        restore_button = QPushButton("Restore")
        restore_button.setObjectName("camera_restore_button")
        restore_button.setMinimumHeight(38)
        restore_button.clicked.connect(self.restore_camera_controls)
        image_layout.addWidget(restore_button)
        image_layout.addStretch()

        preview = QWidget()
        preview.setObjectName("settings_panel")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(10, 10, 10, 10)

        preview_header = QHBoxLayout()
        preview_title = QLabel("Live Camera Feed")
        preview_title.setProperty("class", "section_title")
        preview_header.addWidget(preview_title)
        preview_header.addStretch()
        self.full_view_button = QPushButton("Full view")
        self.full_view_button.setObjectName("camera_full_view_button")
        self.full_view_button.clicked.connect(self.open_full_view)
        preview_header.addWidget(self.full_view_button)
        preview_layout.addLayout(preview_header)

        preview_box = QLabel("No camera connected")
        preview_box.setObjectName("main_camera_frame")
        preview_box.setMinimumSize(320, 240)
        preview_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        preview_box.setScaledContents(False)
        preview_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_box)
        self.preview_box = preview_box
        self.full_view_dialog = None
        self.full_view_box = None
        self.full_view_timer = QTimer(self)
        self.full_view_timer.timeout.connect(self._render_last_frame)

        status_panel = QWidget()
        status_panel.setObjectName("settings_panel")
        status_layout = QVBoxLayout(status_panel)
        status_layout.setContentsMargins(10, 10, 10, 10)
        status_layout.setSpacing(8)

        status_title = QLabel("Camera Metrics")
        status_title.setProperty("class", "section_title")
        status_layout.addWidget(status_title)

        for label, value in [
            ("Camera FPS", "0.0"),
            ("Current bean ID", "--"),
            ("Total beans detected", "0"),
        ]:
            row = QHBoxLayout()
            name = QLabel(label)
            name.setStyleSheet("color: #6b7280; font-weight: 600;")
            val = QLabel(value)
            val.setStyleSheet("font-weight: bold;")
            row.addWidget(name)
            row.addStretch()
            row.addWidget(val)
            status_layout.addLayout(row)
            if label == "Camera FPS":
                self.fps_label = val
            elif label == "Current bean ID":
                self.bean_id_label = val
            else:
                self.bean_count_label = val

        status_layout.addStretch()

        top_row.addWidget(preview, 5)
        top_row.addWidget(status_panel, 2)
        layout.addLayout(top_row)
        layout.addWidget(controls_panel)

        controls = QHBoxLayout()
        controls.addStretch()
        start_btn = AnimatedButton("START CAPTURE")
        start_btn.setObjectName("start_capture_button")
        stop_btn = AnimatedButton("STOP CAPTURE")
        stop_btn.setObjectName("stop_capture_button")
        controls.addWidget(start_btn)
        controls.addWidget(stop_btn)
        layout.addLayout(controls)

        layout.addStretch()

        self.camera_result_label = QLabel("CAMERA RESULT: NO DETECTION")
        self.camera_result_label.setObjectName("camera_result")
        self.camera_result_label.setStyleSheet("color: #2e7d4f; font-weight: bold; font-size: 16px;")
        preview_layout.addWidget(self.camera_result_label)

        start_btn.clicked.connect(self.start_camera)
        stop_btn.clicked.connect(self.stop_camera)

    def _add_mode_buttons(self, layout, name, auto_selected, changed):
        row = QHBoxLayout()
        row.addWidget(QLabel(name))
        row.addStretch()
        group = QButtonGroup(self)
        group.setExclusive(True)
        manual_button = QPushButton("Manual")
        manual_button.setCheckable(True)
        manual_button.setObjectName(f"camera_{name.lower().replace(' ', '_')}_manual")
        auto_button = QPushButton("Auto")
        auto_button.setCheckable(True)
        auto_button.setObjectName(f"camera_{name.lower().replace(' ', '_')}_auto")
        group.addButton(manual_button)
        group.addButton(auto_button)
        manual_button.setChecked(not auto_selected)
        auto_button.setChecked(auto_selected)
        manual_button.clicked.connect(lambda: changed(False))
        auto_button.clicked.connect(lambda: changed(True))
        row.addWidget(manual_button)
        row.addWidget(auto_button)
        layout.addLayout(row)
        return auto_button, manual_button

    def _add_camera_slider(
        self,
        layout,
        label,
        object_name,
        property_id,
        minimum,
        maximum,
        initial_value,
        suffix="",
    ):
        heading = QHBoxLayout()
        heading.addWidget(QLabel(label))
        heading.addStretch()
        value_label = QLabel(f"{initial_value}{suffix}")
        value_label.setObjectName(f"{object_name}_value")
        value_label.setProperty("camera_control_value", True)
        value_label.setMinimumWidth(44)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        heading.addWidget(value_label)
        layout.addLayout(heading)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName(object_name)
        slider.setRange(minimum, maximum)
        slider.setValue(initial_value)
        slider.valueChanged.connect(
            lambda value, prop=property_id, display=value_label, unit=suffix: (
                display.setText(f"{value}{unit}"),
                self._set_camera_control(prop, value),
            )
        )
        layout.addWidget(slider)
        self.camera_control_sliders[property_id] = slider
        self.camera_control_values[property_id] = initial_value
        setattr(self, self._slider_attribute_name(property_id), slider)

    @staticmethod
    def _slider_attribute_name(property_id):
        names = {
            cv2.CAP_PROP_FOCUS: "focus_slider",
            cv2.CAP_PROP_EXPOSURE: "exposure_slider",
            cv2.CAP_PROP_GAIN: "gain_slider",
            cv2.CAP_PROP_WB_TEMPERATURE: "white_balance_slider",
            cv2.CAP_PROP_BRIGHTNESS: "brightness_slider",
            cv2.CAP_PROP_CONTRAST: "contrast_slider",
            cv2.CAP_PROP_HUE: "hue_slider",
            cv2.CAP_PROP_SATURATION: "saturation_slider",
            cv2.CAP_PROP_SHARPNESS: "sharpness_slider",
        }
        return names[property_id]

    def _set_camera_control(self, property_id, value):
        self.camera_control_values[property_id] = value
        if self.camera_controller is None:
            self.local_camera_controls[property_id] = value
            self.local_camera_control_overrides[property_id] = value
            if self.camera_capture is not None:
                unsupported = apply_camera_controls(
                    self.camera_capture,
                    {property_id: value},
                )
                self._set_camera_controls_status(
                    "Not supported by this camera: " + ", ".join(unsupported)
                    if unsupported
                    else "Camera controls applied."
                )
            return

        setter = getattr(self.camera_controller, "set_camera_control", None)
        if setter is None:
            self._set_camera_controls_status(
                "Camera controls are unavailable for this camera."
            )
            return
        result = setter(property_id, value)
        if result is None:
            self._set_camera_controls_status(
                "Saved; this control will apply when the camera starts."
            )
        elif not result and not self.has_camera_controls_status_signal:
            self._set_camera_controls_status(
                "This camera does not support the selected control."
            )

    def _set_camera_resolution(self, resolution):
        width, height = CAMERA_RESOLUTIONS[resolution]
        self._set_camera_stream_settings(
            {
                cv2.CAP_PROP_FRAME_WIDTH: width,
                cv2.CAP_PROP_FRAME_HEIGHT: height,
            }
        )

    def _set_camera_fps(self, frame_rate):
        self._set_camera_stream_setting(cv2.CAP_PROP_FPS, int(frame_rate))

    def _set_camera_stream_setting(self, property_id, value):
        if property_id == cv2.CAP_PROP_FPS:
            self.camera_timer.setInterval(max(1, round(1000 / value)))

        self._set_camera_stream_settings({property_id: value})

    def _set_camera_stream_settings(self, values):
        if cv2.CAP_PROP_FPS in values:
            frame_rate = values[cv2.CAP_PROP_FPS]
            self.camera_timer.setInterval(max(1, round(1000 / frame_rate)))

        if self.camera_controller is None:
            self.local_camera_stream_overrides.update(values)
            if self.camera_capture is not None:
                self.stop_camera()
                self.start_camera()
            return

        setter = getattr(self.camera_controller, "set_camera_stream_settings", None)
        if setter is not None:
            result = setter(values)
        else:
            single_setting_setter = getattr(
                self.camera_controller,
                "set_camera_stream_setting",
                None,
            )
            if single_setting_setter is None:
                self._set_camera_controls_status(
                    "Camera stream settings are unavailable."
                )
                return
            results = [
                single_setting_setter(property_id, value)
                for property_id, value in values.items()
            ]
            result = False if False in results else None
        if result is False and not self.has_camera_controls_status_signal:
            self._set_camera_controls_status(
                "This camera does not support the selected stream setting."
            )

    def _set_focus_mode(self, automatic):
        self._set_camera_control(
            cv2.CAP_PROP_AUTOFOCUS,
            1 if automatic else 0,
        )

    def _set_exposure_mode(self, automatic):
        self._set_camera_control(
            cv2.CAP_PROP_AUTO_EXPOSURE,
            0.75 if automatic else 0.25,
        )

    def _set_white_balance_mode(self, automatic):
        self._set_camera_control(
            cv2.CAP_PROP_AUTO_WB,
            1 if automatic else 0,
        )

    def _set_camera_controls_status(self, status):
        self.camera_controls_status.setText(status)

    def open_full_view(self):
        if self.full_view_dialog is not None:
            self.full_view_dialog.showFullScreen()
            self.full_view_dialog.raise_()
            return

        if self.camera_controller is not None:
            if (
                hasattr(self.camera_controller, "camera_enabled")
                and hasattr(self.camera_controller, "start_camera")
                and (
                    not self.camera_timer.isActive()
                    or not self.camera_controller.camera_enabled
                )
            ):
                self.start_camera()
                if not self.camera_controller.camera_enabled:
                    return
        elif self.camera_capture is None:
            self.start_camera()
            if self.camera_capture is None:
                return

        dialog = QDialog(self)
        dialog.setObjectName("camera_full_view_dialog")
        dialog.setWindowTitle("Live Camera Feed")
        dialog.setStyleSheet(
            "QDialog#camera_full_view_dialog { background-color: #101512; }"
        )
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(16, 12, 16, 16)
        dialog_layout.setSpacing(8)

        toolbar = QHBoxLayout()
        title = QLabel("LIVE CAMERA")
        title.setStyleSheet("color: white; font-weight: 700; font-size: 15px;")
        close_button = QPushButton("Exit full view")
        close_button.setObjectName("camera_full_view_close_button")
        close_button.clicked.connect(dialog.reject)
        toolbar.addWidget(title)
        toolbar.addStretch()
        toolbar.addWidget(close_button)
        dialog_layout.addLayout(toolbar)

        full_view_box = QLabel("Waiting for camera feed...")
        full_view_box.setObjectName("camera_full_view_frame")
        full_view_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        full_view_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        full_view_box.installEventFilter(self)
        dialog_layout.addWidget(full_view_box, 1)

        self.full_view_dialog = dialog
        self.full_view_box = full_view_box
        dialog.finished.connect(self._clear_full_view)
        dialog.showFullScreen()
        self.full_view_timer.start(33)
        if self.last_frame is not None:
            QTimer.singleShot(0, self._render_last_frame)

    def eventFilter(self, watched, event):
        if (
            watched is self.full_view_box
            and event.type() == QEvent.Type.Resize
        ):
            self._render_last_frame()
        return super().eventFilter(watched, event)

    def _render_last_frame(self):
        if self.full_view_box is None:
            return

        frame = self.last_frame
        if self.camera_controller is not None:
            ai_frame = getattr(self.camera_controller, "last_ai_frame", None)
            if ai_frame is not None:
                frame = ai_frame
        if frame is not None:
            self.render_frame(frame)

    def _clear_full_view(self, _result):
        self.full_view_timer.stop()
        self.full_view_dialog = None
        self.full_view_box = None

    def restore_camera_controls(self):
        self.focus_auto_button.setChecked(True)
        self._set_focus_mode(True)
        self.exposure_auto_button.setChecked(True)
        self._set_exposure_mode(True)
        self.white_balance_auto_button.setChecked(True)
        self._set_white_balance_mode(True)
        for property_id, slider in self.camera_control_sliders.items():
            slider.setValue(CAMERA_CONTROL_DEFAULTS[property_id])

    def load_model(self, model_path=None):
        if not model_path:
            return
        self.model, model_file = load_yolo_model(model_path)
        self.model_path = str(model_file)

    def use_dashboard_model(self):
        if self.camera_controller is not None:
            self.model = getattr(self.camera_controller, "ai_model", None)
            self.model_path = getattr(
                self.camera_controller,
                "ai_model_path",
                "",
            )

    def _camera_controls_for_start(self):
        controls = self.camera_control_values.copy()
        if self.focus_auto_button.isChecked():
            controls.pop(cv2.CAP_PROP_FOCUS, None)
        if self.exposure_auto_button.isChecked():
            controls.pop(cv2.CAP_PROP_EXPOSURE, None)
            controls.pop(cv2.CAP_PROP_GAIN, None)
        if self.white_balance_auto_button.isChecked():
            controls.pop(cv2.CAP_PROP_WB_TEMPERATURE, None)
        return controls

    def start_camera(self):
        resolution = self.resolution_selector.currentText()
        width, height = CAMERA_RESOLUTIONS[resolution]
        controls_for_start = self._camera_controls_for_start()
        selected_stream_settings = {
            cv2.CAP_PROP_FRAME_WIDTH: width,
            cv2.CAP_PROP_FRAME_HEIGHT: height,
            cv2.CAP_PROP_FPS: int(self.fps_selector.currentText()),
        }

        if self.camera_controller is not None:
            control_setter = getattr(
                self.camera_controller,
                "set_camera_control",
                None,
            )
            if control_setter is not None:
                for property_id, value in controls_for_start.items():
                    control_setter(property_id, value)

            stream_setter = getattr(
                self.camera_controller,
                "set_camera_stream_settings",
                None,
            )
            if stream_setter is not None:
                stream_setter(selected_stream_settings)
            if not self.camera_controller.camera_enabled:
                self.camera_controller.start_camera()
            if not self.camera_controller.camera_enabled:
                message = (
                    "Camera use is disabled in System Settings."
                    if not self.camera_controller.camera_usage_enabled
                    else "The camera could not be started. Check the camera connection."
                )
                warning = QMessageBox(self)
                warning.setObjectName("camera_unavailable_dialog")
                warning.setIcon(QMessageBox.Icon.Warning)
                warning.setWindowTitle("Camera Unavailable")
                warning.setText(message)
                warning.setStandardButtons(QMessageBox.StandardButton.Ok)
                ok_button = warning.button(QMessageBox.StandardButton.Ok)
                ok_button.setObjectName("camera_unavailable_ok_button")
                warning.style().unpolish(warning)
                warning.style().polish(warning)
                ok_button.style().unpolish(ok_button)
                ok_button.style().polish(ok_button)
                warning.exec()
                return
            if self.camera_timer.isActive():
                return
        else:
            if self.camera_capture is not None and self.camera_capture.isOpened():
                return
            self.local_camera_stream_overrides.update(
                selected_stream_settings
            )
            self.camera_capture = cv2.VideoCapture(self.camera_source, cv2.CAP_DSHOW)
            if not self.camera_capture.isOpened():
                self.camera_capture.release()
                self.camera_capture = None
                self.preview_box.setText("No camera connected")
                return
            stream_errors = apply_camera_stream_settings(
                self.camera_capture,
                self.local_camera_stream_overrides,
            )
            unsupported_controls = apply_camera_controls(
                self.camera_capture,
                controls_for_start,
            )
            self._set_camera_controls_status(
                "Not supported by this camera: "
                + ", ".join(stream_errors + unsupported_controls)
                if stream_errors or unsupported_controls
                else "Using current camera settings."
            )
        self.fps_frame_count = 0
        self.fps_started_at = perf_counter()
        self.fps = 0.0
        self.bean_count = 0
        self.current_bean_id = 0
        self.update_camera_metrics()
        frame_rate = int(self.fps_selector.currentText())
        self.camera_timer.start(max(1, round(1000 / frame_rate)))

    def stop_camera(self):
        self.camera_timer.stop()
        if self.camera_capture is not None:
            self.camera_capture.release()
            self.camera_capture = None
        self.last_frame = None
        self.last_detection = None
        self.fps = 0.0
        self.fps_frame_count = 0
        self.bean_count = 0
        self.current_bean_id = 0
        self.update_camera_metrics()
        self.preview_box.clear()
        self.preview_box.setText("No camera connected")
        self.set_final_result("NO DETECTION")

    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.last_frame is not None:
            self.render_frame(self.last_frame)

    def set_final_result(self, result):
        self.final_result = result if result in CLASS_NAMES else "NO DETECTION"
        self.camera_result_label.setText(f"CAMERA RESULT: {self.final_result}")
        self.final_result_changed.emit(self.final_result)

    def select_detection(self, result):
        if self.model is None or result is None or not result.boxes:
            return None
        names = result.names if hasattr(result, "names") else {}
        candidates = []
        for box in result.boxes:
            confidence = float(box.conf[0])
            if confidence < CONFIDENCE_THRESHOLD:
                continue
            class_id = int(box.cls[0])
            raw_name = names.get(class_id, str(class_id)) if isinstance(names, dict) else names[class_id]
            normalized = str(raw_name).strip().upper().replace("_", "-")
            if normalized in CLASS_NAMES:
                candidates.append((confidence, normalized, box))
        return max(candidates, key=lambda item: item[0]) if candidates else None

    def update_detection(self, result):
        previous_detection = self.last_detection
        detection = self.select_detection(result)
        self.last_detection = detection
        if detection is None:
            self.result_history.clear()
            self.set_final_result("NO DETECTION")
            return

        confidence, label, _ = detection
        if previous_detection is None:
            self.bean_count += 1
            self.current_bean_id = self.bean_count
            self.update_camera_metrics()
        self.result_history.append(label)
        stable_label, count = Counter(self.result_history).most_common(1)[0]
        if count >= (STABILITY_WINDOW // 2 + 1):
            self.set_final_result(stable_label)

    def update_camera_feed(self):
        if self.camera_controller is not None:
            if not self.camera_controller.camera_enabled:
                self.stop_camera()
                return
            controller_model = getattr(
                self.camera_controller,
                "ai_model",
                None,
            )
            if controller_model is not self.model:
                self.model = controller_model
                self.model_path = getattr(
                    self.camera_controller,
                    "ai_model_path",
                    "",
                )
            frame = self.camera_controller.last_frame
            if frame is None:
                return
            frame = frame.copy()
            if self.model is not None:
                ai_result = self.camera_controller.last_ai_result
                self.update_detection(ai_result)
                if ai_result is not None:
                    frame = ai_result.plot(img=frame)
                else:
                    ai_frame = self.camera_controller.last_ai_frame
                    if ai_frame is not None:
                        frame = ai_frame.copy()
            else:
                self.update_detection(None)
        else:
            if self.camera_capture is None or not self.camera_capture.isOpened():
                self.stop_camera()
                return
            success, frame = self.camera_capture.read()
            if not success or frame is None:
                self.stop_camera()
                return

        self.fps_frame_count += 1
        elapsed = perf_counter() - self.fps_started_at
        if elapsed >= 0.5:
            self.fps = self.fps_frame_count / elapsed
            self.fps_frame_count = 0
            self.fps_started_at = perf_counter()
            self.update_camera_metrics()

        if self.camera_controller is None and self.model is not None:
            results = self.model(frame, verbose=False)
            result = results[0] if results else None
            self.update_detection(result)
            if self.last_detection is not None:
                _, label, box = self.last_detection
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cv2.rectangle(frame, (x1, y1), (x2, y2), (46, 125, 79), 2)
                cv2.putText(frame, label, (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (46, 125, 79), 2)
        elif self.camera_controller is None:
            self.update_detection(None)

        self.last_frame = frame.copy()
        self.render_frame(frame)

    def update_camera_metrics(self):
        self.fps_label.setText(f"{self.fps:.1f}")
        bean_count = getattr(
            self.camera_controller,
            "total_bean_count",
            self.bean_count,
        )
        current_seed_value = getattr(
            self.camera_controller,
            "current_seed_value",
            None,
        )
        if current_seed_value is not None:
            bean_id = current_seed_value.text()
        else:
            bean_id = str(self.current_bean_id) if self.current_bean_id else "--"
        self.bean_id_label.setText(bean_id)
        self.bean_count_label.setText(str(bean_count))

    def render_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_frame.shape
        image = QImage(rgb_frame.data, width, height, channels * width, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.preview_box.setPixmap(self._fit_pixmap(pixmap, self.preview_box))
        if self.full_view_box is not None:
            self.full_view_box.setPixmap(
                self._fit_pixmap(pixmap, self.full_view_box)
            )

    @staticmethod
    def _fit_pixmap(pixmap, label):
        return pixmap.scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )


from PySide6.QtCore import Qt

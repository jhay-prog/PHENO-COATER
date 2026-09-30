from collections import Counter, deque
from pathlib import Path
from time import perf_counter

import cv2
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget, QSizePolicy
from .animated_button import AnimatedButton

try:
    from ultralytics import YOLO
except ImportError:  # The GUI remains usable until a model is configured.
    YOLO = None


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
        self.setup_ui()
        self.load_model(model_path)

    def setup_ui(self):
        layout = QVBoxLayout(self)
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
        preview_box.setMinimumSize(320, 240)
        preview_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        preview_box.setScaledContents(False)
        preview_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(preview_box)
        self.preview_box = preview_box

        status_panel = QWidget()
        status_panel.setObjectName("settings_panel")
        status_layout = QVBoxLayout(status_panel)
        status_layout.setContentsMargins(20, 20, 20, 20)
        status_layout.setSpacing(12)

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

        layout.addStretch()

        self.camera_result_label = QLabel("CAMERA RESULT: NO DETECTION")
        self.camera_result_label.setObjectName("camera_result")
        self.camera_result_label.setStyleSheet("color: #c0392b; font-weight: bold; font-size: 16px;")
        preview_layout.addWidget(self.camera_result_label)

        start_btn.clicked.connect(self.start_camera)
        stop_btn.clicked.connect(self.stop_camera)

    def load_model(self, model_path=None):
        if YOLO is None or not model_path:
            return
        model_file = Path(model_path)
        if model_file.exists():
            self.model = YOLO(str(model_file))

    def start_camera(self):
        if self.camera_controller is not None:
            if not self.camera_controller.camera_enabled:
                QMessageBox.warning(
                    self,
                    "Camera is Off",
                    "You need to turn on the camera in Settings before starting capture.",
                )
                return
            if self.camera_timer.isActive():
                return
        else:
            if self.camera_capture is not None and self.camera_capture.isOpened():
                return
            self.camera_capture = cv2.VideoCapture(self.camera_source, cv2.CAP_DSHOW)
            if not self.camera_capture.isOpened():
                self.camera_capture.release()
                self.camera_capture = None
                self.preview_box.setText("No camera connected")
                return
        self.fps_frame_count = 0
        self.fps_started_at = perf_counter()
        self.fps = 0.0
        self.bean_count = 0
        self.current_bean_id = 0
        self.update_camera_metrics()
        self.camera_timer.start(30)

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
            frame = self.camera_controller.last_frame
            if frame is None:
                return
            frame = frame.copy()
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

        if self.model is not None:
            results = self.model(frame, verbose=False)
            result = results[0] if results else None
            self.update_detection(result)
            if self.last_detection is not None:
                _, label, box = self.last_detection
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cv2.rectangle(frame, (x1, y1), (x2, y2), (46, 125, 79), 2)
                cv2.putText(frame, label, (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (46, 125, 79), 2)
        else:
            self.update_detection(None)

        self.last_frame = frame.copy()
        self.render_frame(frame)

    def update_camera_metrics(self):
        self.fps_label.setText(f"{self.fps:.1f}")
        self.bean_id_label.setText(str(self.current_bean_id) if self.current_bean_id else "--")
        self.bean_count_label.setText(str(self.bean_count))

    def render_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_frame.shape
        image = QImage(rgb_frame.data, width, height, channels * width, QImage.Format.Format_RGB888)
        box_size = self.preview_box.size()
        scaled = QPixmap.fromImage(image).scaled(
            box_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        crop_x = max((scaled.width() - box_size.width()) // 2, 0)
        crop_y = max((scaled.height() - box_size.height()) // 2, 0)
        filled = scaled.copy(crop_x, crop_y, box_size.width(), box_size.height())
        self.preview_box.setPixmap(filled)


from PySide6.QtCore import Qt

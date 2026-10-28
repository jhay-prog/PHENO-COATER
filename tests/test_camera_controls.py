import unittest
from unittest.mock import patch

import cv2
import numpy as np
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

from GUI.camera import CameraPage
from GUI.camera_controls import (
    CAMERA_CONTROL_DEFAULTS,
    CAMERA_FRAME_RATES,
    CAMERA_CONTROL_NAMES,
    CAMERA_RESOLUTIONS,
    apply_camera_controls,
    apply_camera_stream_settings,
)
from GUI.dashboard import Dashboard


class CameraControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_camera_properties_are_applied_and_unsupported_controls_reported(self):
        class FakeCapture:
            def __init__(self):
                self.values = {}

            def set(self, property_id, value):
                if property_id == cv2.CAP_PROP_SHARPNESS:
                    return False
                self.values[property_id] = value
                return True

        capture = FakeCapture()
        unsupported = apply_camera_controls(capture, CAMERA_CONTROL_DEFAULTS)

        self.assertEqual(len(capture.values), len(CAMERA_CONTROL_DEFAULTS) - 1)
        self.assertEqual(unsupported, [CAMERA_CONTROL_NAMES[cv2.CAP_PROP_SHARPNESS]])

    def test_resolution_and_frame_rate_are_applied_to_capture(self):
        class FakeCapture:
            def __init__(self):
                self.values = {}

            def set(self, property_id, value):
                self.values[property_id] = value
                return True

        capture = FakeCapture()
        width, height = CAMERA_RESOLUTIONS["1080P"]
        unsupported = apply_camera_stream_settings(
            capture,
            {
                cv2.CAP_PROP_FRAME_WIDTH: width,
                cv2.CAP_PROP_FRAME_HEIGHT: height,
                cv2.CAP_PROP_FPS: 30,
            },
        )

        self.assertEqual(unsupported, [])
        self.assertEqual(capture.values[cv2.CAP_PROP_FRAME_WIDTH], 1920)
        self.assertEqual(capture.values[cv2.CAP_PROP_FRAME_HEIGHT], 1080)
        self.assertEqual(capture.values[cv2.CAP_PROP_FPS], 30)

    def test_dashboard_saves_and_applies_control_changes_to_live_camera(self):
        class FakeCapture:
            def __init__(self):
                self.values = {}

            def set(self, property_id, value):
                self.values[property_id] = value
                return property_id != cv2.CAP_PROP_SHARPNESS

            def release(self):
                pass

        with patch("GUI.dashboard.get_configured_ai_model_path", return_value=""):
            with patch.object(Dashboard, "update_arduino_status"):
                dashboard = Dashboard()
        self.addCleanup(dashboard.close)
        dashboard.arduino_timer.stop()
        capture = FakeCapture()
        dashboard.camera_capture = capture
        dashboard.camera_enabled = True

        self.assertTrue(
            dashboard.set_camera_control(cv2.CAP_PROP_BRIGHTNESS, 180)
        )
        self.assertFalse(
            dashboard.set_camera_control(cv2.CAP_PROP_SHARPNESS, 190)
        )
        self.assertEqual(capture.values[cv2.CAP_PROP_BRIGHTNESS], 180)
        self.assertEqual(capture.values[cv2.CAP_PROP_SHARPNESS], 190)
        self.assertEqual(
            dashboard.camera_control_values[cv2.CAP_PROP_BRIGHTNESS],
            180,
        )
        self.assertTrue(
            dashboard.set_camera_stream_setting(cv2.CAP_PROP_FPS, 60)
        )
        self.assertEqual(capture.values[cv2.CAP_PROP_FPS], 60)

    def test_dashboard_does_not_restart_camera_for_current_resolution(self):
        class FakeCapture:
            def __init__(self):
                self.values = {}

            def set(self, property_id, value):
                self.values[property_id] = value
                return True

            def release(self):
                pass

        with patch("GUI.dashboard.get_configured_ai_model_path", return_value=""):
            with patch.object(Dashboard, "update_arduino_status"):
                dashboard = Dashboard()
        self.addCleanup(dashboard.close)
        dashboard.arduino_timer.stop()
        capture = FakeCapture()
        dashboard.camera_capture = capture
        dashboard.camera_enabled = True
        dashboard.last_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch.object(dashboard, "stop_camera") as stop_camera:
            with patch.object(dashboard, "start_camera") as start_camera:
                result = dashboard.set_camera_stream_settings(
                    {
                        cv2.CAP_PROP_FRAME_WIDTH: 1920,
                        cv2.CAP_PROP_FRAME_HEIGHT: 1080,
                        cv2.CAP_PROP_FPS: 60,
                    }
                )

        self.assertTrue(result)
        stop_camera.assert_not_called()
        start_camera.assert_not_called()
        self.assertEqual(capture.values[cv2.CAP_PROP_FRAME_WIDTH], 1920)
        self.assertEqual(capture.values[cv2.CAP_PROP_FRAME_HEIGHT], 1080)
        self.assertEqual(capture.values[cv2.CAP_PROP_FPS], 60)
        self.assertEqual(dashboard.camera_timer.interval(), 17)

    def test_dashboard_start_preserves_camera_studio_settings(self):
        class FakeCapture:
            def __init__(self):
                self.set_calls = []

            def isOpened(self):
                return True

            def read(self):
                return True, np.zeros((8, 8, 3), dtype=np.uint8)

            def set(self, property_id, value):
                self.set_calls.append((property_id, value))
                return True

            def release(self):
                pass

        with patch("GUI.dashboard.get_configured_ai_model_path", return_value=""):
            with patch.object(Dashboard, "update_arduino_status"):
                dashboard = Dashboard()
        self.addCleanup(dashboard.close)
        dashboard.arduino_timer.stop()
        capture = FakeCapture()
        with patch.object(dashboard, "open_camera", return_value=capture):
            dashboard.start_camera()

        self.assertTrue(dashboard.camera_enabled)
        self.assertEqual(capture.set_calls, [])

        dashboard.stop_camera()
        dashboard.set_camera_control(cv2.CAP_PROP_BRIGHTNESS, 180)
        dashboard.set_camera_stream_setting(cv2.CAP_PROP_FPS, 60)
        with patch.object(dashboard, "open_camera", return_value=capture):
            dashboard.start_camera()

        self.assertEqual(
            capture.set_calls,
            [
                (cv2.CAP_PROP_FPS, 60),
                (cv2.CAP_PROP_BRIGHTNESS, 180),
            ],
        )
        self.assertEqual(dashboard.camera_timer.interval(), 17)

    def test_dashboard_falls_back_when_selected_resolution_has_no_frames(self):
        class FakeCapture:
            def __init__(self, has_frame):
                self.has_frame = has_frame
                self.set_calls = []
                self.released = False

            def isOpened(self):
                return True

            def read(self):
                if not self.has_frame:
                    return False, None
                return True, np.zeros((8, 8, 3), dtype=np.uint8)

            def set(self, property_id, value):
                self.set_calls.append((property_id, value))
                return True

            def release(self):
                self.released = True

        with patch("GUI.dashboard.get_configured_ai_model_path", return_value=""):
            with patch.object(Dashboard, "update_arduino_status"):
                dashboard = Dashboard()
        self.addCleanup(dashboard.close)
        dashboard.arduino_timer.stop()
        unsupported_mode = FakeCapture(has_frame=False)
        default_mode = FakeCapture(has_frame=True)
        dashboard.camera_stream_overrides = {
            cv2.CAP_PROP_FRAME_WIDTH: 3840,
            cv2.CAP_PROP_FRAME_HEIGHT: 2160,
        }
        with patch.object(
            dashboard,
            "open_camera",
            side_effect=[unsupported_mode, default_mode],
        ):
            dashboard.start_camera()

        self.assertTrue(dashboard.camera_enabled)
        self.assertTrue(unsupported_mode.released)
        self.assertEqual(dashboard.camera_stream_overrides, {})
        self.assertEqual(
            unsupported_mode.set_calls,
            [
                (cv2.CAP_PROP_FRAME_WIDTH, 3840),
                (cv2.CAP_PROP_FRAME_HEIGHT, 2160),
            ],
        )
        self.assertEqual(default_mode.set_calls, [])

    def test_admin_capture_applies_selected_resolution_and_fps(self):
        class FakeController(QObject):
            camera_controls_status_changed = Signal(str)

            def __init__(self):
                super().__init__()
                self.camera_enabled = False
                self.camera_usage_enabled = True
                self.stream_values = {}

            def set_camera_stream_settings(self, values):
                self.stream_values.update(values)

            def start_camera(self):
                self.camera_enabled = True

        controller = FakeController()
        page = CameraPage(camera_controller=controller)
        self.addCleanup(page.close)

        page.resolution_selector.setCurrentText("720P")
        page.fps_selector.setCurrentText("60")
        page.start_camera()

        self.assertEqual(
            controller.stream_values[cv2.CAP_PROP_FRAME_WIDTH],
            1280,
        )
        self.assertEqual(
            controller.stream_values[cv2.CAP_PROP_FRAME_HEIGHT],
            720,
        )
        self.assertEqual(controller.stream_values[cv2.CAP_PROP_FPS], 60)
        self.assertTrue(page.camera_timer.isActive())
        self.assertEqual(page.camera_timer.interval(), 17)

    def test_admin_preview_fits_frame_without_cropping(self):
        page = CameraPage(camera_controller=object())
        self.addCleanup(page.close)
        page.preview_box.resize(420, 360)

        page.render_frame(np.zeros((720, 1280, 3), dtype=np.uint8))

        displayed_pixmap = page.preview_box.pixmap()
        self.assertIsNotNone(displayed_pixmap)
        self.assertEqual(displayed_pixmap.width(), 420)
        self.assertLessEqual(displayed_pixmap.height(), 360)
        self.assertAlmostEqual(
            displayed_pixmap.width() / displayed_pixmap.height(),
            16 / 9,
            places=2,
        )

    def test_full_view_shows_shared_feed_and_can_be_closed(self):
        page = CameraPage(camera_controller=object())
        self.addCleanup(page.close)

        page.render_frame(np.zeros((720, 1280, 3), dtype=np.uint8))
        page.open_full_view()
        self.application.processEvents()

        self.assertIsNotNone(page.full_view_dialog)
        self.assertTrue(page.full_view_dialog.isFullScreen())
        self.assertIsNotNone(page.full_view_box.pixmap())
        page.render_frame(np.zeros((720, 1280, 3), dtype=np.uint8))
        self.assertLessEqual(
            page.full_view_box.pixmap().width(),
            page.full_view_box.width(),
        )
        self.assertAlmostEqual(
            page.full_view_box.pixmap().width()
            / page.full_view_box.pixmap().height(),
            16 / 9,
            places=2,
        )

        page.full_view_dialog.reject()
        self.application.processEvents()
        self.assertIsNone(page.full_view_dialog)
        self.assertIsNone(page.full_view_box)

    def test_full_view_starts_shared_camera_with_selected_settings(self):
        class FakeController(QObject):
            camera_controls_status_changed = Signal(str)

            def __init__(self):
                super().__init__()
                self.camera_enabled = False
                self.camera_usage_enabled = True
                self.last_frame = None
                self.stream_values = {}
                self.control_values = {}

            def set_camera_stream_settings(self, values):
                self.stream_values.update(values)

            def set_camera_control(self, property_id, value):
                self.control_values[property_id] = value
                return None

            def start_camera(self):
                self.camera_enabled = True

        controller = FakeController()
        page = CameraPage(camera_controller=controller)
        self.addCleanup(page.close)
        page.resolution_selector.setCurrentText("720P")
        page.fps_selector.setCurrentText("60")

        page.open_full_view()
        self.application.processEvents()

        self.assertTrue(controller.camera_enabled)
        self.assertEqual(
            controller.stream_values[cv2.CAP_PROP_FRAME_WIDTH],
            1280,
        )
        self.assertEqual(
            controller.stream_values[cv2.CAP_PROP_FRAME_HEIGHT],
            720,
        )
        self.assertEqual(controller.stream_values[cv2.CAP_PROP_FPS], 60)
        self.assertEqual(
            controller.control_values[cv2.CAP_PROP_AUTO_EXPOSURE],
            CAMERA_CONTROL_DEFAULTS[cv2.CAP_PROP_AUTO_EXPOSURE],
        )
        self.assertNotIn(cv2.CAP_PROP_EXPOSURE, controller.control_values)
        self.assertNotIn(cv2.CAP_PROP_GAIN, controller.control_values)
        self.assertIsNotNone(page.full_view_dialog)
        page.full_view_dialog.reject()
        self.application.processEvents()
        page.exposure_manual_button.click()
        self.assertIn(
            cv2.CAP_PROP_EXPOSURE,
            page._camera_controls_for_start(),
        )

    def test_admin_preview_uses_ai_frame_when_model_loads_after_page(self):
        class FakeController:
            camera_enabled = True
            camera_usage_enabled = True

            def __init__(self):
                self.ai_model = None
                self.ai_model_path = ""
                self.last_frame = np.zeros((8, 8, 3), dtype=np.uint8)
                self.last_ai_result = None
                self.last_ai_frame = None

        controller = FakeController()
        page = CameraPage(camera_controller=controller)
        self.addCleanup(page.close)
        model = object()
        controller.ai_model = model
        controller.ai_model_path = "model.pt"
        controller.last_ai_frame = np.full(
            (8, 8, 3),
            255,
            dtype=np.uint8,
        )

        page.update_camera_feed()

        self.assertIs(page.model, model)
        self.assertEqual(page.model_path, "model.pt")
        self.assertTrue(np.all(page.last_frame == 255))

    def test_admin_full_view_renders_current_ai_detection_result(self):
        class FakeResult:
            names = {}
            boxes = []

            def plot(self, img=None):
                return np.full_like(img, 255)

        class FakeController:
            camera_enabled = True
            camera_usage_enabled = True

            def __init__(self):
                self.ai_model = object()
                self.ai_model_path = "model.pt"
                self.last_frame = np.zeros((8, 8, 3), dtype=np.uint8)
                self.last_ai_result = FakeResult()
                self.last_ai_frame = None

        controller = FakeController()
        page = CameraPage(camera_controller=controller)
        self.addCleanup(page.close)
        page.open_full_view()
        self.application.processEvents()

        page.update_camera_feed()

        self.assertTrue(np.all(page.last_frame == 255))
        displayed = page.full_view_box.pixmap().toImage()
        self.assertEqual(displayed.pixelColor(0, 0).red(), 255)

        page.full_view_dialog.reject()
        self.application.processEvents()

    def test_full_view_refresh_prefers_dashboard_annotated_frame(self):
        class FakeController:
            ai_model = object()
            ai_model_path = "model.pt"
            last_ai_frame = np.zeros((8, 8, 3), dtype=np.uint8)

        page = CameraPage(camera_controller=FakeController())
        self.addCleanup(page.close)
        page.last_frame = np.zeros((8, 8, 3), dtype=np.uint8)
        page.open_full_view()
        self.application.processEvents()

        page.camera_controller.last_ai_frame = np.full(
            (8, 8, 3),
            255,
            dtype=np.uint8,
        )
        QTest.qWait(50)
        displayed = page.full_view_box.pixmap().toImage()
        self.assertEqual(displayed.pixelColor(0, 0).red(), 255)
        self.assertTrue(page.full_view_timer.isActive())

        page.full_view_dialog.reject()
        self.application.processEvents()
        self.assertFalse(page.full_view_timer.isActive())

    def test_admin_camera_metrics_follow_dashboard_bean_values(self):
        class FakeController:
            total_bean_count = 23

            def __init__(self):
                self.current_seed_value = QLabel("202610280023")

        controller = FakeController()
        page = CameraPage(camera_controller=controller)
        self.addCleanup(page.close)

        page.update_camera_metrics()

        self.assertEqual(page.bean_count_label.text(), "23")
        self.assertEqual(page.bean_id_label.text(), "202610280023")

    def test_focus_range_labels_are_aligned_to_slider_ends(self):
        page = CameraPage(camera_controller=object())
        self.addCleanup(page.close)

        self.assertEqual(page.focus_far_label.text(), "Far")
        self.assertEqual(page.focus_near_label.text(), "Near")
        self.assertTrue(
            page.focus_near_label.alignment() & Qt.AlignmentFlag.AlignRight
        )

    def test_admin_camera_sliders_and_modes_update_camera_properties(self):
        class FakeController(QObject):
            camera_controls_status_changed = Signal(str)

            def __init__(self):
                super().__init__()
                self.values = CAMERA_CONTROL_DEFAULTS.copy()
                self.stream_values = {}

            def set_camera_control(self, property_id, value):
                self.values[property_id] = value
                return None

            def set_camera_stream_setting(self, property_id, value):
                self.stream_values[property_id] = value
                return None

            def set_camera_stream_settings(self, values):
                self.stream_values.update(values)
                return None

        controller = FakeController()
        page = CameraPage(camera_controller=controller)
        self.addCleanup(page.close)

        self.assertIsNotNone(page.layout().itemAt(2).layout())
        self.assertIs(
            page.layout().itemAt(3).widget(),
            page.camera_controls_panel,
        )
        self.assertTrue(page.focus_auto_button.isChecked())
        self.assertTrue(page.exposure_auto_button.isChecked())
        self.assertTrue(page.white_balance_auto_button.isChecked())
        self.assertTrue(page.focus_slider.isEnabled())
        self.assertTrue(page.exposure_slider.isEnabled())
        self.assertTrue(page.white_balance_slider.isEnabled())
        self.assertEqual(page.resolution_selector.currentText(), "1080P")
        self.assertEqual(page.fps_selector.currentText(), "30")
        self.assertEqual(
            page.resolution_selector.count(),
            len(CAMERA_RESOLUTIONS),
        )
        self.assertEqual(
            [int(page.fps_selector.itemText(index)) for index in range(page.fps_selector.count())],
            list(CAMERA_FRAME_RATES),
        )
        self.assertEqual(page.focus_slider.value(), 77)
        self.assertEqual(page.exposure_slider.value(), -5)
        self.assertEqual(page.gain_slider.value(), 0)
        self.assertEqual(page.flicker_selector.currentText(), "60Hz")
        self.assertEqual(page.white_balance_slider.value(), 5000)
        self.assertEqual(
            page.findChild(QLabel, "camera_exposure_slider_value").text(),
            "-5EV",
        )
        self.assertEqual(
            page.findChild(QLabel, "camera_white_balance_slider_value").text(),
            "5000K",
        )
        self.assertEqual(page.brightness_slider.value(), 128)
        self.assertEqual(page.contrast_slider.value(), 128)
        self.assertEqual(page.hue_slider.value(), 128)
        self.assertEqual(page.saturation_slider.value(), 128)
        self.assertEqual(page.sharpness_slider.value(), 128)
        self.assertEqual(
            page.camera_control_sliders[cv2.CAP_PROP_WB_TEMPERATURE].maximum(),
            6500,
        )
        page.brightness_slider.setValue(180)
        page.focus_slider.setValue(80)
        page.resolution_selector.setCurrentText("720P")
        page.fps_selector.setCurrentText("60")
        exposure_value = page.findChild(
            QLabel,
            "camera_exposure_slider_value",
        )
        page.exposure_slider.setValue(-4)
        self.assertEqual(exposure_value.text(), "-4EV")
        page.focus_manual_button.click()
        page.exposure_manual_button.click()
        page.white_balance_auto_button.click()

        self.assertEqual(controller.values[cv2.CAP_PROP_BRIGHTNESS], 180)
        self.assertEqual(controller.values[cv2.CAP_PROP_FOCUS], 80)
        self.assertEqual(controller.values[cv2.CAP_PROP_AUTOFOCUS], 0)
        self.assertEqual(controller.values[cv2.CAP_PROP_AUTO_EXPOSURE], 0.25)
        self.assertEqual(controller.values[cv2.CAP_PROP_AUTO_WB], 1)
        self.assertEqual(
            controller.stream_values[cv2.CAP_PROP_FRAME_WIDTH],
            1280,
        )
        self.assertEqual(
            controller.stream_values[cv2.CAP_PROP_FRAME_HEIGHT],
            720,
        )
        self.assertEqual(controller.stream_values[cv2.CAP_PROP_FPS], 60)
        self.assertTrue(page.focus_slider.isEnabled())
        self.assertTrue(page.exposure_slider.isEnabled())
        page.white_balance_slider.setValue(6400)
        self.assertEqual(controller.values[cv2.CAP_PROP_WB_TEMPERATURE], 6400)
        self.assertTrue(page.white_balance_slider.isEnabled())
        self.assertFalse(page.flicker_selector.isEnabled())

        page.restore_camera_controls()
        self.assertEqual(
            controller.values[cv2.CAP_PROP_BRIGHTNESS],
            CAMERA_CONTROL_DEFAULTS[cv2.CAP_PROP_BRIGHTNESS],
        )
        self.assertEqual(controller.values[cv2.CAP_PROP_AUTOFOCUS], 1)
        self.assertEqual(controller.values[cv2.CAP_PROP_AUTO_EXPOSURE], 0.75)
        self.assertEqual(controller.values[cv2.CAP_PROP_AUTO_WB], 1)


if __name__ == "__main__":
    unittest.main()

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
from threading import Event
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PySide6.QtWidgets import QApplication, QLabel

from GUI.ai_model import resolve_model_file
from GUI.animated_button import AnimatedButton
from GUI.dashboard import Dashboard
from GUI.settings import SettingsPage


class AiModelPathTests(unittest.TestCase):
    def test_model_folder_resolves_preferred_model_weights(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            other_model = folder / "other.pt"
            preferred_model = folder / "my_model.pt"
            other_model.touch()
            preferred_model.touch()

            self.assertEqual(
                resolve_model_file(folder),
                preferred_model,
            )

    def test_model_folder_requires_explicit_path_if_weights_are_ambiguous(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            (folder / "first.pt").touch()
            (folder / "second.pt").touch()

            with self.assertRaisesRegex(ValueError, "Multiple .pt"):
                resolve_model_file(folder)

    def test_model_folder_without_weights_reports_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(FileNotFoundError, "No .pt"):
                resolve_model_file(temp_dir)


class AiModelIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_settings_save_loads_and_persists_ai_folder_path(self):
        class FakeController:
            camera_usage_enabled = True
            ai_model_path = ""
            ai_model_error = ""

            def set_camera_usage_button(self, _button):
                pass

            def set_camera_usage_enabled(self, _enabled):
                pass

            def set_nir_scan_delay(self, _delay_ms):
                pass

            def set_ai_model_path(self, model_path):
                self.configured_path = model_path
                return True

        controller = FakeController()
        page = SettingsPage(camera_controller=controller)
        page.ai_model_path_input.setText(r"C:\models\PHENO AI")
        save_button = page.findChild(AnimatedButton, "settings_save_button")

        with patch("GUI.settings.save_configured_ai_model_path") as save_path:
            save_button.click()

        self.assertEqual(controller.configured_path, r"C:\models\PHENO AI")
        save_path.assert_called_once_with(r"C:\models\PHENO AI")
        self.assertEqual(page.saved_ai_model_path, r"C:\models\PHENO AI")
        self.assertEqual(
            page.findChild(QLabel, "settings_save_state").text(),
            "Settings saved; AI model ready",
        )
        page.port_refresh_timer.stop()
        page.close()

    def test_dashboard_infers_and_renders_annotated_camera_frame(self):
        class FakeCapture:
            def isOpened(self):
                return True

            def read(self):
                return True, np.zeros((32, 32, 3), dtype=np.uint8)

            def release(self):
                pass

        class FakeResult:
            def __init__(self):
                self.plotted = False

            def plot(self, img=None):
                self.plotted = True
                return np.full((32, 32, 3), 255, dtype=np.uint8)

        class FakeModel:
            def __init__(self, result):
                self.result = result
                self.started = Event()
                self.resume = Event()

            def __call__(self, *_args, **kwargs):
                self.started.set()
                self.resume.wait(2)
                self.kwargs = kwargs
                return [self.result]

        result = FakeResult()
        model = FakeModel(result)
        with patch("GUI.dashboard.get_configured_ai_model_path", return_value=""):
            with patch.object(Dashboard, "update_arduino_status"):
                dashboard = Dashboard()
        with patch(
            "GUI.dashboard.load_yolo_model",
            return_value=(model, Path("PHENO AI") / "my_model.pt"),
        ):
            self.assertTrue(dashboard.set_ai_model_path("PHENO AI"))

        dashboard.camera_capture = FakeCapture()
        dashboard.camera_enabled = True
        dashboard.update_camera_feed()
        self.assertIsNotNone(dashboard.last_frame)
        self.assertIsNotNone(dashboard.camera_frame.pixmap())
        self.assertTrue(model.started.wait(1))
        self.assertTrue(dashboard.ai_inference_busy)
        model.resume.set()
        self.assertTrue(dashboard.ai_inference_pool.waitForDone(5000))
        self.application.processEvents()
        dashboard.update_camera_feed()

        self.assertTrue(result.plotted)
        self.assertEqual(model.kwargs, {"conf": 0.5, "verbose": False})
        self.assertIsNotNone(dashboard.camera_frame.pixmap())
        self.assertEqual(
            dashboard.last_ai_frame[0, 0].tolist(),
            [255, 255, 255],
        )
        dashboard.stop_camera()
        dashboard.arduino_timer.stop()
        dashboard.close()

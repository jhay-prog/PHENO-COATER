from pathlib import Path

from PySide6.QtCore import QSettings

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


def get_configured_ai_model_path():
    settings = QSettings("PhenoCoater", "PhenoCoater")
    return str(settings.value("ai/model_path", "") or "")


def save_configured_ai_model_path(model_path):
    settings = QSettings("PhenoCoater", "PhenoCoater")
    if model_path:
        settings.setValue("ai/model_path", model_path)
    else:
        settings.remove("ai/model_path")
    settings.sync()
    if settings.status() != QSettings.Status.NoError:
        raise OSError("Could not save the AI model path.")


def resolve_model_file(model_path):
    path = Path(model_path).expanduser()
    if path.is_file():
        return path
    if not path.is_dir():
        raise FileNotFoundError(f"AI model path does not exist: {path}")

    model_files = sorted(
        candidate
        for candidate in path.iterdir()
        if candidate.is_file() and candidate.suffix.lower() == ".pt"
    )
    for preferred_name in ("my_model.pt", "best.pt"):
        preferred_path = path / preferred_name
        if preferred_path.is_file():
            return preferred_path
    if len(model_files) == 1:
        return model_files[0]
    if not model_files:
        raise FileNotFoundError(
            f"No .pt model weights were found in the AI folder: {path}"
        )
    raise ValueError(
        f"Multiple .pt model files were found in {path}; enter the full path "
        "to the model file."
    )


def load_yolo_model(model_path):
    if YOLO is None:
        raise RuntimeError(
            "Ultralytics is not installed. Install the project requirements "
            "before loading an AI model."
        )

    model_file = resolve_model_file(model_path)
    try:
        return YOLO(str(model_file)), model_file
    except Exception as exc:
        raise RuntimeError(
            f"Could not load the AI model at {model_file}: {exc}"
        ) from exc

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import warnings

from NIR.as7265x import WAVELENGTHS


FEATURE_NAMES = tuple(f"{wavelength}nm" for wavelength in WAVELENGTHS)
SCANS_PER_BEAN = 3


@dataclass(frozen=True)
class NIRPrediction:
    label: str
    confidence: float


class NIRClassifier:
    def __init__(self, model):
        self.model = model
        model_features = getattr(model, "feature_names_in_", None)
        if model_features is not None:
            if tuple(str(feature) for feature in model_features) != FEATURE_NAMES:
                raise ValueError(
                    "The NIR model feature names do not match the AS7265X channels."
                )
        if not hasattr(model, "classes_"):
            raise ValueError("The NIR model does not expose its trained classes.")
        self.load_warnings = ()

    def predict(self, spectra):
        if len(spectra) != SCANS_PER_BEAN:
            raise ValueError(
                f"Expected {SCANS_PER_BEAN} NIR scans, received {len(spectra)}."
            )
        if any(len(scan) != len(FEATURE_NAMES) for scan in spectra):
            raise ValueError(
                f"Each NIR scan must contain {len(FEATURE_NAMES)} measurements."
            )

        averaged_values = []
        for channel in range(len(FEATURE_NAMES)):
            channel_values = [scan[channel] for scan in spectra]
            if not all(isfinite(value) for value in channel_values):
                raise ValueError("NIR scans must contain only finite measurements.")
            averaged_values.append(sum(channel_values) / SCANS_PER_BEAN)

        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError(
                "Pandas is required for NIR model inference. Install the project "
                "requirements."
            ) from exc

        features = pd.DataFrame([averaged_values], columns=FEATURE_NAMES)
        label = str(self.model.predict(features)[0]).strip()
        probabilities = self.model.predict_proba(features)[0]
        classes = list(self.model.classes_)
        if len(probabilities) != len(classes) or not classes:
            raise ValueError("The NIR model returned an invalid probability result.")
        if label not in {str(class_name) for class_name in classes}:
            raise ValueError(f"The NIR model returned an unknown class: {label}.")
        normalized_probabilities = [float(value) for value in probabilities]
        if any(
            not isfinite(value) or not 0.0 <= value <= 1.0
            for value in normalized_probabilities
        ):
            raise ValueError("The NIR model returned an invalid confidence score.")
        confidence = max(normalized_probabilities)
        return NIRPrediction(label=label, confidence=confidence)


def default_nir_model_path():
    return (
        Path(__file__).resolve().parents[1]
        / "NIR"
        / "models"
        / "svm_lda_nir_model.pkl"
    )


def load_nir_classifier(model_path=None):
    model_file = Path(model_path or default_nir_model_path()).expanduser()
    if not model_file.is_file():
        raise FileNotFoundError(f"NIR model file not found: {model_file}")
    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError(
            "Joblib and scikit-learn are required for NIR model inference. "
            "Install the project requirements."
        ) from exc

    try:
        with warnings.catch_warnings(record=True) as load_warnings:
            warnings.simplefilter("always")
            model = joblib.load(model_file)
        classifier = NIRClassifier(model)
        classifier.load_warnings = tuple(
            dict.fromkeys(str(warning.message) for warning in load_warnings)
        )
        return classifier, model_file
    except Exception as exc:
        raise RuntimeError(
            f"Could not load the NIR model at {model_file}: {exc}"
        ) from exc

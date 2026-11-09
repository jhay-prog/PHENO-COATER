import re


QUALITY_CATEGORIES = (
    "GOOD",
    "MOLDY",
    "GERMINATED",
    "INSECT-DAMAGED",
    "FLAT",
    "BROKEN",
    "DOUBLE",
)


def normalize_quality_category(raw_name):
    normalized = re.sub(
        r"\s*\([^)]*\)\s*$",
        "",
        str(raw_name).strip().upper(),
    )
    normalized = re.sub(r"[\s_]+", "-", normalized)
    normalized = re.sub(r"-BEANS?$", "", normalized)
    return normalized if normalized in QUALITY_CATEGORIES else None

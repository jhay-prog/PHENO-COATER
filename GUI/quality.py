import re


QUALITY_CATEGORIES = (
    "GOOD",
    "MOLDY",
    "SLATY",
    "GERMINATED",
    "INSECT-DAMAGED",
    "BLACK",
    "FLAT",
    "DOUBLE",
    "FOREIGN-OBJECT",
)


def normalize_quality_category(raw_name):
    normalized = re.sub(
        r"\s*\([^)]*\)\s*$",
        "",
        str(raw_name).strip().upper(),
    )
    normalized = re.sub(r"[\s_]+", "-", normalized)
    normalized = re.sub(r"-BEANS?$", "", normalized)
    normalized = {
        "SLANTY": "SLATY",
        "FOREIGN-OBJECTS": "FOREIGN-OBJECT",
    }.get(normalized, normalized)
    return normalized if normalized in QUALITY_CATEGORIES else None

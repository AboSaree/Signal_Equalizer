"""
mode_settings.py — Built-in equalizer modes & JSON persistence for custom modes.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_DIR = BASE_DIR / "settings_files"

# ── Built-in modes ───────────────────────────────────

DEFAULT_MODES = {
    "generic": {
        "name": "generic",
        "label": "Generic",
        "sliders": [
            {"id": "sub_bass",  "label": "Sub-Bass",    "gain": 1.0, "windows": [{"freq_min": 0,    "freq_max": 500}]},
            {"id": "bass",      "label": "Bass",        "gain": 1.0, "windows": [{"freq_min": 500,  "freq_max": 1000}]},
            {"id": "low_mid",   "label": "Low-Mid",     "gain": 1.0, "windows": [{"freq_min": 1000, "freq_max": 2000}]},
            {"id": "mid",       "label": "Mid",         "gain": 1.0, "windows": [{"freq_min": 2000, "freq_max": 4000}]},
            {"id": "high_mid",  "label": "High-Mid",    "gain": 1.0, "windows": [{"freq_min": 4000, "freq_max": 8000}]},
            {"id": "high",      "label": "High",        "gain": 1.0, "windows": [{"freq_min": 8000, "freq_max": 22050}]},
        ],
    },
    "musical_instruments": {
        "name": "musical_instruments",
        "label": "Musical Instruments",
        "sliders": [
            {"id": "bass_guitar", "label": "Bass Guitar",       "gain": 1.0, "windows": [{"freq_min": 40,   "freq_max": 300}]},
            {"id": "drums",       "label": "Drums / Percussion", "gain": 1.0, "windows": [{"freq_min": 20,   "freq_max": 200}, {"freq_min": 5000, "freq_max": 10000}]},
            {"id": "piano",       "label": "Piano",             "gain": 1.0, "windows": [{"freq_min": 27,   "freq_max": 4186}]},
            {"id": "violin",      "label": "Violin",            "gain": 1.0, "windows": [{"freq_min": 196,  "freq_max": 3136}]},
            {"id": "vocals",      "label": "Vocals",            "gain": 1.0, "windows": [{"freq_min": 80,   "freq_max": 1100}]},
        ],
    },
    "animal_sounds": {
        "name": "animal_sounds",
        "label": "Animal Sounds",
        "sliders": [
            {"id": "dog",   "label": "Dog",   "gain": 1.0, "windows": [{"freq_min": 40,   "freq_max": 2000}]},
            {"id": "cat",   "label": "Cat",   "gain": 1.0, "windows": [{"freq_min": 500,  "freq_max": 4000}]},
            {"id": "bird",  "label": "Bird",  "gain": 1.0, "windows": [{"freq_min": 1000, "freq_max": 8000}]},
            {"id": "frog",  "label": "Frog",  "gain": 1.0, "windows": [{"freq_min": 200,  "freq_max": 1500}]},
        ],
    },
    "human_voices": {
        "name": "human_voices",
        "label": "Human Voices",
        "sliders": [
            {"id": "male",    "label": "Male",    "gain": 1.0, "windows": [{"freq_min": 85,  "freq_max": 180}]},
            {"id": "female",  "label": "Female",  "gain": 1.0, "windows": [{"freq_min": 165, "freq_max": 255}]},
            {"id": "child",   "label": "Child",   "gain": 1.0, "windows": [{"freq_min": 250, "freq_max": 400}]},
            {"id": "elderly", "label": "Elderly", "gain": 1.0, "windows": [{"freq_min": 80,  "freq_max": 160}]},
        ],
    },
    "ecg": {
        "name": "ecg",
        "label": "ECG",
        "sliders": [
            {"id": "normal_sinus", "label": "Normal Sinus",          "gain": 1.0, "windows": [{"freq_min": 0.5, "freq_max": 40}]},
            {"id": "afib",         "label": "AFib",                  "gain": 1.0, "windows": [{"freq_min": 4,   "freq_max": 9}, {"freq_min": 40, "freq_max": 60}]},
            {"id": "vtach",        "label": "Ventricular Tachycardia", "gain": 1.0, "windows": [{"freq_min": 2,   "freq_max": 30}]},
            {"id": "noise",        "label": "Baseline Wander / Noise", "gain": 1.0, "windows": [{"freq_min": 0,   "freq_max": 0.5}, {"freq_min": 150, "freq_max": 500}]},
        ],
    },
}


def _ensure_dir():
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def list_modes():
    """Return list of available mode names (built-in + custom)."""
    modes = list(DEFAULT_MODES.keys())
    _ensure_dir()
    for f in SETTINGS_DIR.glob("*.json"):
        name = f.stem
        if name not in modes:
            modes.append(name)
    return modes


def load_mode(mode_name: str) -> dict:
    """Load a mode config — saved file takes precedence over built-in."""
    _ensure_dir()
    saved = SETTINGS_DIR / f"{mode_name}.json"
    if saved.exists():
        return json.loads(saved.read_text(encoding="utf-8"))
    if mode_name in DEFAULT_MODES:
        return DEFAULT_MODES[mode_name]
    raise KeyError(f"Mode '{mode_name}' not found")


def save_mode(mode_name: str, config: dict) -> dict:
    """Validate and save a custom mode config as JSON."""
    if "sliders" not in config:
        raise ValueError("Config must contain 'sliders' list")
    for s in config["sliders"]:
        if "windows" not in s or not s["windows"]:
            raise ValueError(f"Slider '{s.get('id', '?')}' must have at least one window")
    config.setdefault("name", mode_name)
    config.setdefault("label", mode_name.replace("_", " ").title())
    _ensure_dir()
    path = SETTINGS_DIR / f"{mode_name}.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config


def delete_mode(mode_name: str):
    """Delete a custom mode. Built-ins cannot be deleted."""
    if mode_name in DEFAULT_MODES:
        raise ValueError(f"Cannot delete built-in mode '{mode_name}'")
    _ensure_dir()
    path = SETTINGS_DIR / f"{mode_name}.json"
    if path.exists():
        path.unlink()
    else:
        raise KeyError(f"Custom mode '{mode_name}' not found")


def sliders_to_bands(sliders: list) -> list:
    """
    Flatten slider definitions into a flat list of
    {"freq_min", "freq_max", "gain"} dicts.
    """
    bands = []
    for s in sliders:
        gain = float(s.get("gain", 1.0))
        for w in s.get("windows", []):
            bands.append({
                "freq_min": float(w["freq_min"]),
                "freq_max": float(w["freq_max"]),
                "gain": gain,
            })
    return bands

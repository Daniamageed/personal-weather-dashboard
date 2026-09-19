"""
project.py
----------
CS50P entry point AND the "main flow" unit of the app.

IMPORTANT: This file is fully self-contained (no custom local imports)
because CS50P's submit50/check50 only evaluates project.py and
test_project.py in isolation. All the core, independently-testable
logic (temperature conversion, comfort score, validation, storage,
ASCII chart, weather emoji) is therefore defined directly here.

The full app (gui.py, api_client.py) imports these same functions FROM
this file, so there is still a single source of truth -- just inverted
from a typical "many small modules" layout.
"""

import json
import os
from datetime import datetime


# ---------------------------------------------------------------------------
# Temperature conversion
# ---------------------------------------------------------------------------

def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert a Celsius temperature to Fahrenheit, rounded to 1 decimal."""
    return round((celsius * 9 / 5) + 32, 1)


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """Convert a Fahrenheit temperature to Celsius, rounded to 1 decimal."""
    return round((fahrenheit - 32) * 5 / 9, 1)


# ---------------------------------------------------------------------------
# Weather Comfort Score  (0-100)  -- the mandatory custom feature
# ---------------------------------------------------------------------------
# Ideal temperature range : 20°C - 25°C
# Ideal humidity range    : 40%  - 60%
#
# temp_score      -> 100 inside the ideal range, drops 4 points per degree
#                    outside it (clamped 0-100).
# humidity_score  -> 100 inside the ideal range, drops 2 points per percent
#                    outside it (clamped 0-100).
# final score     -> 60% temperature + 40% humidity.
#
# Classification:
#   score >= 75                                -> "Comfortable"
#   score <  75 and temp above ideal range      -> "Hot"
#   score <  75 and temp below ideal range      -> "Cold"
#   score <  75 and humidity above ideal range  -> "Humid"
#   otherwise                                   -> "Uncomfortable"
# ---------------------------------------------------------------------------

IDEAL_TEMP_MIN, IDEAL_TEMP_MAX = 20, 25
IDEAL_HUMIDITY_MIN, IDEAL_HUMIDITY_MAX = 40, 60


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def calculate_comfort_score(temp_c: float, humidity: float) -> dict:
    """
    Calculate the Weather Comfort Score for a given temperature (Celsius)
    and relative humidity (%). Returns {"score": int, "classification": str}
    """
    if IDEAL_TEMP_MIN <= temp_c <= IDEAL_TEMP_MAX:
        temp_score = 100
    elif temp_c < IDEAL_TEMP_MIN:
        temp_score = _clamp(100 - (IDEAL_TEMP_MIN - temp_c) * 4)
    else:
        temp_score = _clamp(100 - (temp_c - IDEAL_TEMP_MAX) * 4)

    if IDEAL_HUMIDITY_MIN <= humidity <= IDEAL_HUMIDITY_MAX:
        humidity_score = 100
    elif humidity < IDEAL_HUMIDITY_MIN:
        humidity_score = _clamp(100 - (IDEAL_HUMIDITY_MIN - humidity) * 2)
    else:
        humidity_score = _clamp(100 - (humidity - IDEAL_HUMIDITY_MAX) * 2)

    final_score = round(_clamp(temp_score * 0.6 + humidity_score * 0.4))

    if final_score >= 75:
        classification = "Comfortable"
    elif temp_c > IDEAL_TEMP_MAX:
        classification = "Hot"
    elif temp_c < IDEAL_TEMP_MIN:
        classification = "Cold"
    elif humidity > IDEAL_HUMIDITY_MAX:
        classification = "Humid"
    else:
        classification = "Uncomfortable"

    return {"score": final_score, "classification": classification}


# ---------------------------------------------------------------------------
# Display formatting
# ---------------------------------------------------------------------------

def format_weather_display(weather: dict, unit: str = "C") -> str:
    """Build a multi-line, human-readable summary from a weather dict."""
    temp_c = weather["temperature_c"]
    feels_c = weather["feels_like_c"]

    if unit.upper() == "F":
        temp = celsius_to_fahrenheit(temp_c)
        feels = celsius_to_fahrenheit(feels_c)
        symbol = "°F"
    else:
        temp = temp_c
        feels = feels_c
        symbol = "°C"

    comfort = calculate_comfort_score(temp_c, weather["humidity"])

    lines = [
        f"City: {weather['city']}",
        f"Condition: {weather['description'].title()}",
        f"Temperature: {temp}{symbol}  (feels like {feels}{symbol})",
        f"Humidity: {weather['humidity']}%",
        f"Wind speed: {weather['wind_speed']} m/s",
        f"Comfort Score: {comfort['score']}/100 ({comfort['classification']})",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_city_name(city: str) -> bool:
    """A city name is valid if non-empty and only letters/spaces/-/'."""
    if not city or not city.strip():
        return False
    cleaned = city.strip()
    return all(ch.isalpha() or ch in " -'" for ch in cleaned)


# ---------------------------------------------------------------------------
# Bonus: Weather emoji
# ---------------------------------------------------------------------------

def get_weather_emoji(description: str) -> str:
    """Return a representative emoji for a weather description string."""
    description = description.lower()
    mapping = [
        (("clear",), "☀️"),
        (("few clouds", "scattered clouds"), "🌤️"),
        (("broken clouds", "overcast"), "☁️"),
        (("thunderstorm",), "⛈️"),
        (("snow",), "❄️"),
        (("mist", "fog", "haze"), "🌫️"),
        (("rain", "drizzle"), "🌧️"),
        (("clouds",), "☁️"),
    ]
    for keywords, emoji in mapping:
        if any(keyword in description for keyword in keywords):
            return emoji
    return "🌡️"


# ---------------------------------------------------------------------------
# Bonus: ASCII bar chart for a 5-day temperature forecast
# ---------------------------------------------------------------------------

def generate_ascii_chart(labels: list, values: list, unit_symbol: str = "°C",
                          max_bar_width: int = 25) -> str:
    """Build a simple horizontal ASCII bar chart from labels and values."""
    if not values:
        return "No data to display."

    min_val, max_val = min(values), max(values)
    value_range = (max_val - min_val) or 1

    lines = []
    for label, value in zip(labels, values):
        filled = int(((value - min_val) / value_range) * (max_bar_width - 1)) + 1
        bar = "█" * filled
        lines.append(f"{label:<12} {value:>5.1f}{unit_symbol} {bar}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Storage: Favorites  (Add / Remove / List)
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
MAX_HISTORY_ENTRIES = 10


def _ensure_file(path: str, default):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)


def _load_json(path: str, default):
    _ensure_file(path, default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default


def _save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_favorites(path: str = FAVORITES_FILE) -> list:
    return _load_json(path, [])


def add_favorite(city: str, path: str = FAVORITES_FILE) -> list:
    favorites = load_favorites(path)
    normalized = city.strip().title()
    if normalized and normalized not in favorites:
        favorites.append(normalized)
        _save_json(path, favorites)
    return favorites


def remove_favorite(city: str, path: str = FAVORITES_FILE) -> list:
    favorites = load_favorites(path)
    normalized = city.strip().title()
    favorites = [c for c in favorites if c != normalized]
    _save_json(path, favorites)
    return favorites


def list_favorites(path: str = FAVORITES_FILE) -> list:
    return load_favorites(path)


# ---------------------------------------------------------------------------
# Storage: Search history (last 10 searches)
# ---------------------------------------------------------------------------

def load_history(path: str = HISTORY_FILE) -> list:
    return _load_json(path, [])


def add_history_entry(city: str, path: str = HISTORY_FILE) -> list:
    history = load_history(path)
    entry = {
        "city": city.strip().title(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    history.insert(0, entry)
    history = history[:MAX_HISTORY_ENTRIES]
    _save_json(path, history)
    return history


def get_recent_history(limit: int = MAX_HISTORY_ENTRIES, path: str = HISTORY_FILE) -> list:
    return load_history(path)[:limit]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    """Launch the Tkinter weather application."""
    from gui import run_app
    run_app()


if __name__ == "__main__":
    main()


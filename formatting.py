"""
formatting.py
--------------
Unit responsible for: temperature conversion, Weather Comfort Score
calculation, and turning raw weather data into human-readable text.

This module has NO dependency on the network or on Tkinter, so every
function inside it can be unit-tested in isolation.
"""

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
# Weather Comfort Score  (0-100)
# ---------------------------------------------------------------------------
# Rules (documented again in README.md):
#
#   * Ideal temperature range  : 20°C - 25°C
#   * Ideal humidity range     : 40%  - 60%
#
#   temp_score      -> 100 inside the ideal range, and drops by 4 points
#                       for every degree away from the nearest edge of
#                       the ideal range (clamped between 0 and 100).
#
#   humidity_score  -> 100 inside the ideal range, and drops by 2 points
#                       for every percentage point away from the nearest
#                       edge of the ideal range (clamped between 0 and 100).
#
#   final score     -> weighted average: 60% temperature + 40% humidity
#                       (temperature affects how a person "feels" more
#                       than humidity does, hence the higher weight).
#
#   Classification (based on the final score AND which factor is driving
#   the discomfort):
#       score >= 75                                -> "Comfortable"
#       score <  75 and temp above ideal range      -> "Hot"
#       score <  75 and temp below ideal range      -> "Cold"
#       score <  75 and humidity above ideal range  -> "Humid"
#       otherwise                                   -> "Uncomfortable"
# ---------------------------------------------------------------------------

IDEAL_TEMP_MIN, IDEAL_TEMP_MAX = 20, 25
IDEAL_HUMIDITY_MIN, IDEAL_HUMIDITY_MAX = 40, 60


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def calculate_comfort_score(temp_c: float, humidity: float) -> dict:
    """
    Calculate the Weather Comfort Score for a given temperature (Celsius)
    and relative humidity (%).

    Returns a dict: {"score": int, "classification": str}
    """
    # --- temperature sub-score ---
    if IDEAL_TEMP_MIN <= temp_c <= IDEAL_TEMP_MAX:
        temp_score = 100
    elif temp_c < IDEAL_TEMP_MIN:
        temp_score = _clamp(100 - (IDEAL_TEMP_MIN - temp_c) * 4)
    else:
        temp_score = _clamp(100 - (temp_c - IDEAL_TEMP_MAX) * 4)

    # --- humidity sub-score ---
    if IDEAL_HUMIDITY_MIN <= humidity <= IDEAL_HUMIDITY_MAX:
        humidity_score = 100
    elif humidity < IDEAL_HUMIDITY_MIN:
        humidity_score = _clamp(100 - (IDEAL_HUMIDITY_MIN - humidity) * 2)
    else:
        humidity_score = _clamp(100 - (humidity - IDEAL_HUMIDITY_MAX) * 2)

    final_score = round(_clamp(temp_score * 0.6 + humidity_score * 0.4))

    # --- classification ---
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
    """
    Build a multi-line, human-readable summary from a weather dict
    produced by api_client.get_weather().

    unit: "C" or "F" -> which unit to display the temperatures in.
    """
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
    """
    A city name is considered valid if it is non-empty (after stripping
    whitespace) and contains only letters, spaces, hyphens or apostrophes.
    """
    if not city or not city.strip():
        return False
    cleaned = city.strip()
    return all(ch.isalpha() or ch in " -'" for ch in cleaned)


# ---------------------------------------------------------------------------
# Bonus #1: Weather emoji  (small helper used by the GUI)
# ---------------------------------------------------------------------------

def get_weather_emoji(description: str) -> str:
    """
    Return a representative emoji for a weather description string
    (e.g. "clear sky" -> "☀️", "light rain" -> "🌧️").
    Falls back to a generic cloud icon if nothing matches.
    """
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
# Bonus #2: ASCII bar chart for a 5-day temperature forecast
# ---------------------------------------------------------------------------

def generate_ascii_chart(labels: list, values: list, unit_symbol: str = "°C",
                          max_bar_width: int = 25) -> str:
    """
    Build a simple horizontal ASCII bar chart from parallel lists of
    labels (e.g. dates) and numeric values (e.g. temperatures).

    Example output:
        2026-09-02   31.0°C ████████████████████████
        2026-09-03   28.5°C ███████████████████
        ...

    Pure text/math logic only -> independently unit-testable.
    """
    if not values:
        return "No data to display."

    min_val, max_val = min(values), max(values)
    value_range = (max_val - min_val) or 1  # avoid division by zero

    lines = []
    for label, value in zip(labels, values):
        filled = int(((value - min_val) / value_range) * (max_bar_width - 1)) + 1
        bar = "█" * filled
        lines.append(f"{label:<12} {value:>5.1f}{unit_symbol} {bar}")
    return "\n".join(lines)
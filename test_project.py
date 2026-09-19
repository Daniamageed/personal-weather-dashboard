"""
test_project.py
----------------
Unit tests for project.py (CS50P requirement: run with `pytest`).

Covers:
    1. Unit conversion (Celsius <-> Fahrenheit)
    2. Comfort score evaluation
    3. City-name validation
    4. Favorites storage operations (add/remove/list)
    5. History storage operations (add + limit to 10)
"""

import os
import tempfile

from project import (
    celsius_to_fahrenheit,
    fahrenheit_to_celsius,
    calculate_comfort_score,
    validate_city_name,
    add_favorite,
    remove_favorite,
    list_favorites,
    add_history_entry,
    get_recent_history,
    get_weather_emoji,
    generate_ascii_chart,
)


# 1. Temperature conversion ------------------------------------------------

def test_celsius_to_fahrenheit():
    assert celsius_to_fahrenheit(0) == 32
    assert celsius_to_fahrenheit(25) == 77
    assert celsius_to_fahrenheit(-40) == -40


def test_fahrenheit_to_celsius():
    assert fahrenheit_to_celsius(32) == 0
    assert fahrenheit_to_celsius(77) == 25
    assert fahrenheit_to_celsius(-40) == -40


# 2. Comfort score -----------------------------------------------------

def test_calculate_comfort_score():
    ideal = calculate_comfort_score(22, 50)
    assert ideal["score"] == 100
    assert ideal["classification"] == "Comfortable"

    hot = calculate_comfort_score(38, 50)
    assert hot["classification"] == "Hot"
    assert hot["score"] < 75

    cold = calculate_comfort_score(0, 50)
    assert cold["classification"] == "Cold"
    assert cold["score"] < 75


# 3. Validation ----------------------------------------------------------

def test_validate_city_name():
    assert validate_city_name("Baghdad") is True
    assert validate_city_name("New York") is True
    assert validate_city_name("") is False
    assert validate_city_name("   ") is False
    assert validate_city_name("Baghdad123") is False


# 4. Favorites storage (uses a temp file so it never touches real data) ----

def test_favorites_add_remove_list():
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "favorites.json")

        assert list_favorites(path) == []

        add_favorite("baghdad", path)
        add_favorite("Erbil", path)
        favorites = list_favorites(path)
        assert "Baghdad" in favorites
        assert "Erbil" in favorites

        remove_favorite("Baghdad", path)
        favorites = list_favorites(path)
        assert "Baghdad" not in favorites
        assert "Erbil" in favorites


# 5. History storage (add + 10-entry limit) ------------------------------

def test_history_add_and_limit():
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "history.json")

        for i in range(12):
            add_history_entry(f"City{i}", path)

        history = get_recent_history(path=path)
        assert len(history) == 10
        # Most recent search should be first
        assert history[0]["city"] == "City11"


# 6. Bonus: weather emoji mapping ------------------------------------------

def test_get_weather_emoji():
    assert get_weather_emoji("clear sky") == "☀️"
    assert get_weather_emoji("light rain") == "🌧️"
    assert get_weather_emoji("heavy snow") == "❄️"
    assert get_weather_emoji("something unknown") == "🌡️"


# 7. Bonus: ASCII chart generation ------------------------------------------

def test_generate_ascii_chart():
    labels = ["Mon", "Tue", "Wed"]
    values = [20.0, 30.0, 25.0]
    chart = generate_ascii_chart(labels, values, unit_symbol="°C")

    # Every label should appear in the chart
    for label in labels:
        assert label in chart

    # The hottest day (Tue) should have the longest bar
    lines = chart.split("\n")
    bar_lengths = [line.count("█") for line in lines]
    assert bar_lengths[1] == max(bar_lengths)

    # Empty input should not crash
    assert generate_ascii_chart([], []) == "No data to display."


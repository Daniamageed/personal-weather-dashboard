"""
project.py
----------
CS50P entry point AND the "main flow" unit of the app.

This module re-exports the core, independently-testable functions from
formatting.py and storage.py (so test_project.py can simply do
`from project import ...`), and its main() launches the Tkinter GUI.

Modules in this project:
    api_client.py  -> talks to the Weather API
    storage.py     -> saves/loads favorites & history (JSON)
    formatting.py  -> unit conversion, comfort score, display text
    gui.py         -> Tkinter user interface
    project.py     -> this file: CS50P entry point / main flow
"""

from formatting import (
    celsius_to_fahrenheit,
    fahrenheit_to_celsius,
    calculate_comfort_score,
    validate_city_name,
    format_weather_display,
    get_weather_emoji,
    generate_ascii_chart,
)
from storage import (
    add_favorite,
    remove_favorite,
    list_favorites,
    add_history_entry,
    get_recent_history,
)


def main():
    """Launch the Tkinter weather application."""
    from gui import run_app
    run_app()


if __name__ == "__main__":
    main()
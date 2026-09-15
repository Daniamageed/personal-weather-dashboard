"""
storage.py
----------
Unit responsible for: persisting favorite cities and search history
to JSON files on disk. All functions take an optional path so tests
can point them at a temporary file instead of the real data files.
"""

import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

MAX_HISTORY_ENTRIES = 10


def _ensure_file(path: str, default):
    """Create the data directory / file with a default value if missing."""
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


# ---------------------------------------------------------------------------
# Favorites  (Add / Remove / List)
# ---------------------------------------------------------------------------

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
# Search history (last 10 searches)
# ---------------------------------------------------------------------------

def load_history(path: str = HISTORY_FILE) -> list:
    return _load_json(path, [])


def add_history_entry(city: str, path: str = HISTORY_FILE) -> list:
    """
    Add a new search entry (city + timestamp) to the history, keeping
    only the most recent MAX_HISTORY_ENTRIES entries.
    """
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

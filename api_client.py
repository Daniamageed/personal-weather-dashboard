"""
api_client.py
-------------
Unit responsible for: talking to the OpenWeatherMap "current weather"
API and turning the raw JSON response into a clean, predictable dict.

The API key is read from the environment (see .env.example) so it is
never hard-coded or pushed to GitHub.
"""

import os

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency fallback
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv()

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
REQUEST_TIMEOUT = 8  # seconds


class WeatherAPIError(Exception):
    """Base class for all weather-API related errors."""


class CityNotFoundError(WeatherAPIError):
    """Raised when the API cannot find the requested city."""


class NetworkError(WeatherAPIError):
    """Raised when there is no internet connection or a DNS failure."""


class APITimeoutError(WeatherAPIError):
    """Raised when the request takes too long to respond."""


class InvalidAPIResponseError(WeatherAPIError):
    """Raised when the API returns something we don't understand."""


def get_api_key() -> str:
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        raise WeatherAPIError(
            "لم يتم العثور على WEATHER_API_KEY. تأكد من إضافته في ملف .env"
        )
    return api_key


def get_weather(city: str, api_key: str | None = None) -> dict:
    """
    Fetch the current weather for `city` and return a normalized dict:

    {
        "city": str,
        "temperature_c": float,
        "feels_like_c": float,
        "humidity": int,
        "wind_speed": float,
        "description": str,
    }

    Raises CityNotFoundError, NetworkError, APITimeoutError or
    InvalidAPIResponseError on failure.
    """
    api_key = api_key or get_api_key()
    params = {
        "q": city.strip(),
        "appid": api_key,
        "units": "metric",  # always fetch in Celsius; convert later if needed
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        raise APITimeoutError(f"انتهت مهلة الاتصال أثناء البحث عن '{city}'.")
    except requests.exceptions.ConnectionError:
        raise NetworkError("تعذّر الاتصال بالإنترنت. تحقق من اتصالك وحاول مجددًا.")
    except requests.exceptions.RequestException as e:
        raise WeatherAPIError(f"حدث خطأ غير متوقع أثناء الاتصال بالـ API: {e}")

    if response.status_code == 404:
        raise CityNotFoundError(f"لم يتم العثور على مدينة باسم '{city}'.")

    if response.status_code == 401:
        raise WeatherAPIError("مفتاح الـ API غير صالح أو غير مفعّل بعد.")

    if response.status_code != 200:
        raise WeatherAPIError(f"استجابة غير متوقعة من الخادم (كود {response.status_code}).")

    try:
        data = response.json()
        return {
            "city": data["name"],
            "temperature_c": data["main"]["temp"],
            "feels_like_c": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "description": data["weather"][0]["description"],
        }
    except (KeyError, IndexError, ValueError) as e:
        raise InvalidAPIResponseError(f"رد الـ API غير مفهوم أو ناقص: {e}")


def get_forecast(city: str, api_key: str | None = None) -> list:
    """
    Fetch a 5-day forecast for `city` (Bonus feature).

    OpenWeatherMap's free "forecast" endpoint returns data in 3-hour steps
    for the next 5 days. This function reduces that to ONE representative
    entry per day (the reading closest to 12:00 noon) so the UI can show
    a clean 5-row table.

    Returns a list of dicts:
        [{"date": "2026-09-02", "temp_c": 31.0, "description": "clear sky"}, ...]

    Raises the same exceptions as get_weather().
    """
    api_key = api_key or get_api_key()
    params = {
        "q": city.strip(),
        "appid": api_key,
        "units": "metric",
    }

    try:
        response = requests.get(FORECAST_URL, params=params, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        raise APITimeoutError(f"انتهت مهلة الاتصال أثناء جلب توقعات '{city}'.")
    except requests.exceptions.ConnectionError:
        raise NetworkError("تعذّر الاتصال بالإنترنت. تحقق من اتصالك وحاول مجددًا.")
    except requests.exceptions.RequestException as e:
        raise WeatherAPIError(f"حدث خطأ غير متوقع أثناء الاتصال بالـ API: {e}")

    if response.status_code == 404:
        raise CityNotFoundError(f"لم يتم العثور على مدينة باسم '{city}'.")
    if response.status_code == 401:
        raise WeatherAPIError("مفتاح الـ API غير صالح أو غير مفعّل بعد.")
    if response.status_code != 200:
        raise WeatherAPIError(f"استجابة غير متوقعة من الخادم (كود {response.status_code}).")

    try:
        data = response.json()
        entries = data["list"]
    except (KeyError, ValueError) as e:
        raise InvalidAPIResponseError(f"رد الـ API غير مفهوم أو ناقص: {e}")

    return _reduce_to_daily(entries)


def _reduce_to_daily(entries: list) -> list:
    """
    Pick one 3-hour reading per day (closest to 12:00) from the raw
    forecast list, and return up to 5 days.
    """
    by_date = {}
    for item in entries:
        dt_txt = item.get("dt_txt", "")
        if not dt_txt:
            continue
        date_part, time_part = dt_txt.split(" ")
        hour = int(time_part.split(":")[0])

        if date_part not in by_date or abs(hour - 12) < by_date[date_part]["_hour_diff"]:
            by_date[date_part] = {
                "date": date_part,
                "temp_c": item["main"]["temp"],
                "description": item["weather"][0]["description"],
                "_hour_diff": abs(hour - 12),
            }

    daily = sorted(by_date.values(), key=lambda d: d["date"])
    for d in daily:
        d.pop("_hour_diff", None)
    return daily[:5]

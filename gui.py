"""
gui.py
------
Tkinter interface for the Weather App — styled to look like a real
desktop application (custom color palette, card-style panels, weather
emoji, and a 5-day forecast window with an ASCII temperature chart).

Layout:
  - Header banner with the app title
  - Search bar: city entry + °C/°F switch + Search button
  - Result card: emoji + condition + temperature + comfort score
  - Two side-by-side cards: Favorites | Last 10 searches
  - "5-Day Forecast" button opens a popup with a table + ASCII bar chart
"""

import tkinter as tk
from tkinter import ttk, messagebox

from project import (
    validate_city_name,
    calculate_comfort_score,
    celsius_to_fahrenheit,
    get_weather_emoji,
    generate_ascii_chart,
    add_favorite,
    remove_favorite,
    list_favorites,
    add_history_entry,
    get_recent_history,
)
from api_client import (
    get_weather,
    get_forecast,
    WeatherAPIError,
    CityNotFoundError,
    NetworkError,
    APITimeoutError,
    InvalidAPIResponseError,
)

# ---------------------------------------------------------------------------
# Color palette / theme constants
# ---------------------------------------------------------------------------
BG_MAIN = "#0F172A"       # deep navy background
BG_CARD = "#1E293B"       # slightly lighter card background
BG_ACCENT = "#38BDF8"     # sky-blue accent
TEXT_LIGHT = "#F1F5F9"
TEXT_MUTED = "#94A3B8"
FONT_FAMILY = "Segoe UI"


class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Weather App — Personal Weather Dashboard")
        self.geometry("620x620")
        self.resizable(False, False)
        self.configure(bg=BG_MAIN)

        self.unit_var = tk.StringVar(value="C")
        self.current_city_var = tk.StringVar(value="")
        self.current_weather = None  # cache of last successful fetch

        self._build_style()
        self._build_header()
        self._build_search_bar()
        self._build_result_card()
        self._build_lists_panel()

        self._refresh_favorites()
        self._refresh_history()

    # -- Theme / ttk styling --------------------------------------------

    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame", background=BG_MAIN)
        style.configure("Card.TFrame", background=BG_CARD)

        style.configure("TLabel", background=BG_MAIN, foreground=TEXT_LIGHT,
                         font=(FONT_FAMILY, 10))
        style.configure("Card.TLabel", background=BG_CARD, foreground=TEXT_LIGHT,
                         font=(FONT_FAMILY, 10))
        style.configure("Muted.TLabel", background=BG_CARD, foreground=TEXT_MUTED,
                         font=(FONT_FAMILY, 9))
        style.configure("Header.TLabel", background=BG_MAIN, foreground=TEXT_LIGHT,
                         font=(FONT_FAMILY, 18, "bold"))
        style.configure("Emoji.TLabel", background=BG_CARD, font=(FONT_FAMILY, 36))
        style.configure("Temp.TLabel", background=BG_CARD, foreground=BG_ACCENT,
                         font=(FONT_FAMILY, 28, "bold"))
        style.configure("Score.TLabel", background=BG_CARD, foreground=TEXT_LIGHT,
                         font=(FONT_FAMILY, 11, "bold"))

        style.configure("TLabelframe", background=BG_CARD, foreground=TEXT_LIGHT,
                         font=(FONT_FAMILY, 10, "bold"), bordercolor=BG_ACCENT)
        style.configure("TLabelframe.Label", background=BG_CARD, foreground=BG_ACCENT,
                         font=(FONT_FAMILY, 10, "bold"))

        style.configure("Accent.TButton", background=BG_ACCENT, foreground="#0F172A",
                         font=(FONT_FAMILY, 10, "bold"), padding=6, borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#0EA5E9")])

        style.configure("Ghost.TButton", background=BG_CARD, foreground=TEXT_LIGHT,
                         font=(FONT_FAMILY, 9), padding=5, borderwidth=1)
        style.map("Ghost.TButton", background=[("active", "#334155")])

        style.configure("TRadiobutton", background=BG_MAIN, foreground=TEXT_LIGHT,
                         font=(FONT_FAMILY, 10))
        style.map("TRadiobutton", background=[("active", BG_MAIN)])

        style.configure("TEntry", fieldbackground=BG_CARD, foreground=TEXT_LIGHT,
                         insertcolor=TEXT_LIGHT, padding=6)

        style.configure("Treeview", background=BG_CARD, fieldbackground=BG_CARD,
                         foreground=TEXT_LIGHT, rowheight=26, font=(FONT_FAMILY, 10))
        style.configure("Treeview.Heading", background="#334155", foreground=TEXT_LIGHT,
                         font=(FONT_FAMILY, 10, "bold"))

    # -- UI construction ----------------------------------------------

    def _build_header(self):
        header = ttk.Frame(self, padding=(20, 18, 20, 10))
        header.pack(fill="x")
        ttk.Label(header, text="🌦️  Personal Weather Dashboard", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header, text="Search any city to see current weather and forecast",
                  style="TLabel", foreground=TEXT_MUTED).pack(anchor="w", pady=(2, 0))

    def _build_search_bar(self):
        frame = ttk.Frame(self, padding=(20, 0, 20, 10))
        frame.pack(fill="x")

        self.city_entry = ttk.Entry(frame, width=26, font=(FONT_FAMILY, 11))
        self.city_entry.pack(side="left", ipady=3)
        self.city_entry.bind("<Return>", lambda event: self.on_search())
        self.city_entry.insert(0, "Enter city name...")
        self.city_entry.bind("<FocusIn>", self._clear_placeholder)

        unit_frame = ttk.Frame(frame)
        unit_frame.pack(side="left", padx=12)
        ttk.Radiobutton(unit_frame, text="°C", variable=self.unit_var, value="C",
                         command=self.on_unit_change).pack(side="left")
        ttk.Radiobutton(unit_frame, text="°F", variable=self.unit_var, value="F",
                         command=self.on_unit_change).pack(side="left", padx=(6, 0))

        ttk.Button(frame, text="🔍 Search", style="Accent.TButton",
                   command=self.on_search).pack(side="left", padx=8)

    def _clear_placeholder(self, event):
        if self.city_entry.get() == "Enter city name...":
            self.city_entry.delete(0, tk.END)

    def _build_result_card(self):
        outer = ttk.Frame(self, padding=(20, 0, 20, 10))
        outer.pack(fill="x")

        self.result_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        self.result_card.pack(fill="x")

        top_row = ttk.Frame(self.result_card, style="Card.TFrame")
        top_row.pack(fill="x")

        self.emoji_label = ttk.Label(top_row, text="🌍", style="Emoji.TLabel")
        self.emoji_label.pack(side="left", padx=(0, 15))

        info_col = ttk.Frame(top_row, style="Card.TFrame")
        info_col.pack(side="left", fill="both", expand=True)

        self.city_label = ttk.Label(info_col, text="No data yet",
                                     style="Card.TLabel", font=(FONT_FAMILY, 13, "bold"))
        self.city_label.pack(anchor="w")

        self.condition_label = ttk.Label(info_col, text="Search a city to get started",
                                          style="Muted.TLabel")
        self.condition_label.pack(anchor="w")

        self.temp_label = ttk.Label(top_row, text="--°", style="Temp.TLabel")
        self.temp_label.pack(side="right")

        details_row = ttk.Frame(self.result_card, style="Card.TFrame")
        details_row.pack(fill="x", pady=(12, 0))

        self.feels_label = ttk.Label(details_row, text="", style="Card.TLabel")
        self.feels_label.pack(side="left", padx=(0, 20))
        self.humidity_label = ttk.Label(details_row, text="", style="Card.TLabel")
        self.humidity_label.pack(side="left", padx=(0, 20))
        self.wind_label = ttk.Label(details_row, text="", style="Card.TLabel")
        self.wind_label.pack(side="left")

        self.comfort_label = ttk.Label(self.result_card, text="", style="Score.TLabel")
        self.comfort_label.pack(anchor="w", pady=(10, 0))

        buttons_row = ttk.Frame(self.result_card, style="Card.TFrame")
        buttons_row.pack(anchor="w", pady=(14, 0))
        ttk.Button(buttons_row, text="⭐ Add to favorites", style="Ghost.TButton",
                   command=self.on_add_favorite).pack(side="left", padx=(0, 8))
        ttk.Button(buttons_row, text="📅 5-Day Forecast", style="Ghost.TButton",
                   command=self.on_show_forecast).pack(side="left")

    def _build_lists_panel(self):
        container = ttk.Frame(self, padding=(20, 0, 20, 20))
        container.pack(fill="both", expand=True)

        fav_frame = ttk.LabelFrame(container, text="⭐ Favorites", padding=10)
        fav_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.fav_listbox = tk.Listbox(fav_frame, height=10, bg=BG_CARD, fg=TEXT_LIGHT,
                                       selectbackground=BG_ACCENT, selectforeground="#0F172A",
                                       borderwidth=0, highlightthickness=0,
                                       font=(FONT_FAMILY, 10))
        self.fav_listbox.pack(fill="both", expand=True)
        self.fav_listbox.bind("<Double-1>", self.on_favorite_double_click)

        ttk.Button(fav_frame, text="Remove selected", style="Ghost.TButton",
                   command=self.on_remove_favorite).pack(pady=(8, 0), fill="x")

        hist_frame = ttk.LabelFrame(container, text="🕓 Last 10 searches", padding=10)
        hist_frame.pack(side="left", fill="both", expand=True, padx=(6, 0))

        self.hist_listbox = tk.Listbox(hist_frame, height=10, bg=BG_CARD, fg=TEXT_LIGHT,
                                        selectbackground=BG_ACCENT, selectforeground="#0F172A",
                                        borderwidth=0, highlightthickness=0,
                                        font=(FONT_FAMILY, 10))
        self.hist_listbox.pack(fill="both", expand=True)
        self.hist_listbox.bind("<Double-1>", self.on_history_double_click)

    # -- Actions ---------------------------------------------------------

    def on_search(self):
        city = self.city_entry.get().strip()

        if not validate_city_name(city):
            messagebox.showerror("Error", "Please enter a valid city name.")
            return

        try:
            weather = get_weather(city)
        except CityNotFoundError as e:
            messagebox.showerror("City Not Found", str(e))
            return
        except NetworkError as e:
            messagebox.showerror("Connection Error", str(e))
            return
        except APITimeoutError as e:
            messagebox.showerror("Request Timed Out", str(e))
            return
        except InvalidAPIResponseError as e:
            messagebox.showerror("Unexpected Response", str(e))
            return
        except WeatherAPIError as e:
            messagebox.showerror("Error", str(e))
            return

        self.current_city_var.set(weather["city"])
        self.current_weather = weather
        self._display_weather(weather)

        add_history_entry(weather["city"])
        self._refresh_history()

    def on_unit_change(self):
        if self.current_weather:
            self._display_weather(self.current_weather)

    def on_add_favorite(self):
        city = self.current_city_var.get()
        if not city:
            messagebox.showinfo("Notice", "Please search for a city before adding it to favorites.")
            return
        add_favorite(city)
        self._refresh_favorites()

    def on_remove_favorite(self):
        selection = self.fav_listbox.curselection()
        if not selection:
            return
        city = self.fav_listbox.get(selection[0]).strip()
        remove_favorite(city)
        self._refresh_favorites()

    def on_favorite_double_click(self, event):
        selection = self.fav_listbox.curselection()
        if not selection:
            return
        city = self.fav_listbox.get(selection[0]).strip()
        self.city_entry.delete(0, tk.END)
        self.city_entry.insert(0, city)
        self.on_search()

    def on_history_double_click(self, event):
        selection = self.hist_listbox.curselection()
        if not selection:
            return
        text = self.hist_listbox.get(selection[0]).strip()
        city = text.split(" — ")[0]
        self.city_entry.delete(0, tk.END)
        self.city_entry.insert(0, city)
        self.on_search()

    def on_show_forecast(self):
        city = self.current_city_var.get()
        if not city:
            messagebox.showinfo("Notice", "Please search for a city before viewing the forecast.")
            return

        try:
            forecast = get_forecast(city)
        except CityNotFoundError as e:
            messagebox.showerror("City Not Found", str(e))
            return
        except NetworkError as e:
            messagebox.showerror("Connection Error", str(e))
            return
        except APITimeoutError as e:
            messagebox.showerror("Request Timed Out", str(e))
            return
        except InvalidAPIResponseError as e:
            messagebox.showerror("Unexpected Response", str(e))
            return
        except WeatherAPIError as e:
            messagebox.showerror("Error", str(e))
            return

        if not forecast:
            messagebox.showinfo("Notice", "No forecast data available for this city.")
            return

        self._open_forecast_window(city, forecast)

    # -- Popup windows -----------------------------------------------------

    def _open_forecast_window(self, city: str, forecast: list):
        window = tk.Toplevel(self)
        window.title(f"5-Day Forecast — {city}")
        window.geometry("480x420")
        window.resizable(False, False)
        window.configure(bg=BG_MAIN)

        unit = self.unit_var.get()
        symbol = "°F" if unit == "F" else "°C"

        ttk.Label(window, text=f"📅 5-Day Forecast — {city}",
                  style="Header.TLabel", font=(FONT_FAMILY, 13, "bold")).pack(
            anchor="w", padx=14, pady=(14, 8))

        columns = ("date", "temp", "description")
        tree = ttk.Treeview(window, columns=columns, show="headings", height=5)
        tree.heading("date", text="Date")
        tree.heading("temp", text=f"Temp ({symbol})")
        tree.heading("description", text="Condition")
        tree.column("date", width=110, anchor="center")
        tree.column("temp", width=90, anchor="center")
        tree.column("description", width=200, anchor="center")
        tree.pack(fill="x", padx=14, pady=(0, 10))

        display_temps = []
        for day in forecast:
            temp = day["temp_c"]
            if unit == "F":
                temp = celsius_to_fahrenheit(temp)
            display_temps.append(temp)
            emoji = get_weather_emoji(day["description"])
            tree.insert("", tk.END, values=(day["date"], temp,
                                             f"{emoji} {day['description'].title()}"))

        # Bonus: ASCII chart of the same data
        ttk.Label(window, text="📊 Temperature Chart (ASCII):", style="TLabel",
                  font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", padx=14)

        chart_text = generate_ascii_chart(
            labels=[d["date"] for d in forecast],
            values=display_temps,
            unit_symbol=symbol,
        )
        chart_box = tk.Text(window, height=8, bg=BG_CARD, fg=BG_ACCENT,
                             font=("Consolas", 10), borderwidth=0,
                             highlightthickness=0)
        chart_box.pack(fill="both", expand=True, padx=14, pady=(4, 14))
        chart_box.insert(tk.END, chart_text)
        chart_box.config(state="disabled")

    # -- Helpers -----------------------------------------------------------

    def _display_weather(self, weather: dict):
        unit = self.unit_var.get()
        symbol = "°F" if unit == "F" else "°C"

        temp = weather["temperature_c"]
        feels = weather["feels_like_c"]
        if unit == "F":
            temp = celsius_to_fahrenheit(temp)
            feels = celsius_to_fahrenheit(feels)

        comfort = calculate_comfort_score(weather["temperature_c"], weather["humidity"])
        emoji = get_weather_emoji(weather["description"])

        self.emoji_label.config(text=emoji)
        self.city_label.config(text=weather["city"])
        self.condition_label.config(text=weather["description"].title())
        self.temp_label.config(text=f"{temp}{symbol}")
        self.feels_label.config(text=f"🌡️ Feels like {feels}{symbol}")
        self.humidity_label.config(text=f"💧 {weather['humidity']}%")
        self.wind_label.config(text=f"💨 {weather['wind_speed']} m/s")
        self.comfort_label.config(
            text=f"🧭 Comfort Score: {comfort['score']}/100 — {comfort['classification']}"
        )

    def _refresh_favorites(self):
        self.fav_listbox.delete(0, tk.END)
        for city in list_favorites():
            self.fav_listbox.insert(tk.END, f"  {city}")

    def _refresh_history(self):
        self.hist_listbox.delete(0, tk.END)
        for entry in get_recent_history():
            self.hist_listbox.insert(tk.END, f"  {entry['city']} — {entry['timestamp']}")


def run_app():
    app = WeatherApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()


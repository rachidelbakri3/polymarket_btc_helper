
import requests
from datetime import datetime, timedelta, timezone
import pytz
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button

class BTCApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.up_price_label = Label(text="Current Up Price (Market):")
        self.up_price_input = TextInput(multiline=False, input_filter='float')
        self.result_label = Label(text="Results will appear here")
        self.calc_button = Button(text="Calculate", on_press=self.calculate)
        self.layout.add_widget(self.up_price_label)
        self.layout.add_widget(self.up_price_input)
        self.layout.add_widget(self.calc_button)
        self.layout.add_widget(self.result_label)
        return self.layout

    def get_btc_price(self):
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        try:
            r = requests.get(url, timeout=10); r.raise_for_status()
            return float(r.json()["price"])
        except: return None

    def get_hour_window_et(self):
        tz_et = pytz.timezone("America/New_York")
        now_et = datetime.now(timezone.utc).astimezone(tz_et)
        start_et = now_et.replace(minute=0, second=0, microsecond=0)
        end_et = start_et + timedelta(hours=1)
        minutes_left = int(max(0, min(60, (end_et - now_et).total_seconds() // 60)))
        return start_et, end_et, minutes_left

    def get_price_to_beat(self, start_et):
        start_utc = start_et.astimezone(timezone.utc)
        start_ms = int(start_utc.timestamp() * 1000)
        end_ms = start_ms + 60*60*1000
        url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={start_ms}&endTime={end_ms}&limit=1"
        try:
            r = requests.get(url, timeout=10); r.raise_for_status()
            data = r.json()
            if data: return float(data[0][1])  # open
        except: pass
        return None

    def get_volatility_per_min(self, minutes):
        lookback = minutes if minutes > 0 else 15
        limit = max(1, min(1000, lookback))
        url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit={limit}"
        try:
            r = requests.get(url, timeout=10); r.raise_for_status()
            data = r.json()
            highs = [float(c[2]) for c in data]; lows = [float(c[3]) for c in data]
            return (max(highs) - min(lows)) / max(1, lookback)
        except: return 5.0

    def calculate(self, _):
        current_price = self.get_btc_price()
        if not current_price:
            self.result_label.text = "Error fetching BTC price"; return
        try:
            up_market_price = float(self.up_price_input.text or "0.5")
        except:
            self.result_label.text = "Invalid input"; return

        start_et, end_et, minutes_left = self.get_hour_window_et()
        price_to_beat = self.get_price_to_beat(start_et) or current_price
        vol_per_min = self.get_volatility_per_min(minutes_left)
        expected_move = vol_per_min * max(1, minutes_left)

        gap_impact = (price_to_beat - current_price) / expected_move if expected_move else 0.0
        fair_up = max(0.0, min(1.0, 0.5 + (gap_impact / 100.0)))
        fair_down = 1.0 - fair_up
        fair_up_pct, fair_down_pct = round(fair_up*100,1), round(fair_down*100,1)

        diff = fair_up - up_market_price
        signal = "⚪ Neutral"
        if diff > 0.15: signal = "🟢 Buy Up"
        elif diff < -0.15: signal = "🔴 Sell Up"

        self.result_label.text = (
            f"ET hour start: {start_et.strftime('%Y-%m-%d %H:%M')}\n"
            f"Minutes Left: {minutes_left}\n"
            f"BTC Price: {round(current_price, 2)}\n"
            f"Price to Beat: {round(price_to_beat, 2)}\n"
            f"Volatility/min: {round(vol_per_min, 3)}\n"
            f"Expected Move: {round(expected_move, 3)}\n"
            f"Up: {fair_up_pct}%  |  Down: {fair_down_pct}%\n"
            f"Signal: {signal}"
        )

if __name__ == '__main__':
    BTCApp().run()

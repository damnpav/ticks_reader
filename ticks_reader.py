import MetaTrader5 as MT5
from datetime import datetime, timedelta, timezone

if not MT5.initialize():
    raise RuntimeError(f"MT5 initialize() failed, code={MT5.last_error()}")

print("Connected to MT5:", MT5.version())

symbol = "EURUSD"
if not MT5.symbol_select(symbol, True):
    raise RuntimeError(f"Cannot select symbol {symbol}, err={MT5.last_error()}")

utc_now = datetime.now(timezone.utc)
from_time = utc_now - timedelta(seconds=10)

ticks = MT5.copy_ticks_from(symbol, from_time, 10_000, MT5.COPY_TICKS_ALL)
print(f"Got {len(ticks)} ticks")

if len(ticks):
    print(ticks[-1])  # last tick snapshot


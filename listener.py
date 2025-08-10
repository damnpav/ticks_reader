import MetaTrader5 as MT5
import sqlite3
import time
from datetime import datetime, timezone

DB_FILE = "ticks.db"
SYMBOLS = ["BTCUSD", "ETHUSD"]
POLL_INTERVAL = 0.001  # seconds between polls

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS ticks (
    symbol TEXT,
    time INTEGER,        -- unix time in seconds
    bid REAL,
    ask REAL,
    last REAL,
    volume INTEGER,
    time_msc INTEGER,    -- unix time in milliseconds
    flags INTEGER,
    volume_real REAL,
    PRIMARY KEY (symbol, time_msc)
)
""")
conn.commit()

# --- Connect to MT5 ---
if not MT5.initialize():
    raise RuntimeError(f"MT5 initialize() failed, code={MT5.last_error()}")

print("Connected to MT5:", MT5.version())

for sym in SYMBOLS:
    if not MT5.symbol_select(sym, True):
        raise RuntimeError(f"Cannot select symbol {sym}, err={MT5.last_error()}")

last_time_msc = {sym: None for sym in SYMBOLS}

try:
    while True:
        for sym in SYMBOLS:
            tick = MT5.symbol_info_tick(sym)
            if tick and tick.time_msc != last_time_msc[sym]:
                last_time_msc[sym] = tick.time_msc

                cursor.execute("""
                    INSERT OR IGNORE INTO ticks
                    (symbol, time, bid, ask, last, volume, time_msc, flags, volume_real)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sym,
                    tick.time, tick.bid, tick.ask, tick.last, tick.volume,
                    tick.time_msc, tick.flags, tick.volume_real
                ))
                conn.commit()

                print(f"{sym} @ {datetime.fromtimestamp(tick.time, tz=timezone.utc)} "
                      f"bid={tick.bid} ask={tick.ask} last={tick.last}")

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print("\nStopped by user.")

finally:
    conn.close()
    MT5.shutdown()

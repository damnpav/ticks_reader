from datetime import datetime, timezone
import MetaTrader5 as MT5
import sqlite3
import time

DB_FILE = "ticks_v1.db"
SYMBOLS = ["BTCUSD", "ETHUSD", "EURUSD", "USDX", "VIX", "SP500"]
POLL_INTERVAL = 0.5

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS ticks (
    symbol TEXT,
    time INTEGER,
    bid REAL,
    ask REAL,
    last REAL,
    volume INTEGER,
    time_msc INTEGER,
    flags INTEGER,
    volume_real REAL,
    PRIMARY KEY (symbol, time_msc)
)
""")
conn.commit()

if not MT5.initialize():
    raise RuntimeError(f"MT5 init failed: {MT5.last_error()}")

print("Connected:", MT5.version())


for sym in SYMBOLS:
    MT5.symbol_select(sym, True)


last_time = {sym: datetime.now(timezone.utc) for sym in SYMBOLS}

try:
    while True:
        for sym in SYMBOLS:
            ticks = MT5.copy_ticks_from(sym, last_time[sym], 1000, MT5.COPY_TICKS_ALL)
            if len(ticks) > 0:
                newest_ms = ticks['time_msc'][-1]
                last_time[sym] = datetime.fromtimestamp(newest_ms / 1000, tz=timezone.utc)

                cursor.executemany("""
                    INSERT OR IGNORE INTO ticks
                    (symbol, time, bid, ask, last, volume, time_msc, flags, volume_real)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    (sym, t.time, t.bid, t.ask, t.last, t.volume,
                     t.time_msc, t.flags, t.volume_real)
                    for t in ticks
                ])
                conn.commit()

                print(f"{sym}: got {len(ticks)} ticks")

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print("Stopped.")

finally:
    conn.close()
    MT5.shutdown()

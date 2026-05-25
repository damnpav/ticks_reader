from datetime import datetime, timezone
import MetaTrader5 as MT5
import sqlite3
import time
import traceback
import sys

from config import INSTANCES, POLL_INTERVAL, TICK_BATCH, LOG_INTERVAL, SQL_FOLDER
from ver_2505.config import SQL_FOLDER

BROKER = sys.argv[1]
print(f'Started broker: {BROKER}')

CFG      = INSTANCES[BROKER]
DB_FILE  = CFG["db"]
SYMBOLS  = CFG["symbols"]
MT5_PATH = CFG["path"]

with open(SQL_FOLDER + 'create.sql', 'r') as f:
    create_sql = f.read()


# ── DB setup ─────────────────────────────────────────────────────────────────

conn   = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
cursor.executescript(create_sql)
conn.commit()


def log_health(status, symbols_ok, ticks_window, last_error, uptime_sec):
    cursor.execute("""
        INSERT INTO health_log (ts, status, symbols_ok, ticks_window, last_error, uptime_sec)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (int(time.time()), status, symbols_ok, ticks_window, last_error, int(uptime_sec)))
    conn.commit()


# ── MT5 connect ───────────────────────────────────────────────────────────────

if not MT5.initialize(path=MT5_PATH):
    err = str(MT5.last_error())
    log_health("error", 0, 0, f"MT5 init failed: {err}", 0)
    raise RuntimeError(f"MT5 init failed: {err}")

print(f"[{BROKER}] Connected: {MT5.version()}")

failed_syms = []
for sym in SYMBOLS:
    if not MT5.symbol_select(sym, True):
        print(f"[{BROKER}] WARN: cannot select {sym}")
        failed_syms.append(sym)
    else:
        print(f"[{BROKER}] OK: {sym}")

active_symbols = [s for s in SYMBOLS if s not in failed_syms]
last_time      = {sym: datetime.now(timezone.utc) for sym in active_symbols}


# ── Main loop ─────────────────────────────────────────────────────────────────

start_time     = time.time()
last_log_time  = start_time
window_ticks   = 0
window_syms_ok = set()
last_error     = None

print(f"[{BROKER}] Polling {len(active_symbols)} symbols every {POLL_INTERVAL}s ...")

try:
    while True:
        for sym in active_symbols:
            try:
                # drain all ticks in batches — fixes silent loss when >1000 ticks arrive
                while True:
                    ticks = MT5.copy_ticks_from(
                        sym, last_time[sym], TICK_BATCH, MT5.COPY_TICKS_ALL
                    )
                    if ticks is None or len(ticks) == 0:
                        break

                    last_time[sym] = datetime.fromtimestamp(
                        int(ticks['time_msc'][-1]) / 1000, tz=timezone.utc
                    )

                    cursor.executemany("""
                        INSERT OR IGNORE INTO ticks
                        (symbol, time, bid, ask, last, volume, time_msc, flags, volume_real)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        (sym,
                         int(t['time']), float(t['bid']), float(t['ask']),
                         float(t['last']), int(t['volume']), int(t['time_msc']),
                         int(t['flags']), float(t['volume_real']))
                        for t in ticks
                    ])
                    conn.commit()

                    window_ticks += len(ticks)
                    window_syms_ok.add(sym)
                    print(f"[{BROKER}] {sym}: +{len(ticks)} ticks")

                    if len(ticks) < TICK_BATCH:
                        break

            except Exception as e:
                last_error = f"{sym}: {e}"
                print(f"[{BROKER}] ERROR {last_error}")

        # periodic health snapshot
        now = time.time()
        if now - last_log_time >= LOG_INTERVAL:
            uptime = now - start_time
            log_health("alive", len(window_syms_ok), window_ticks, last_error, uptime)
            print(
                f"[{BROKER}] HEALTH | uptime: {int(uptime)}s | "
                f"active syms: {len(window_syms_ok)}/{len(active_symbols)} | "
                f"ticks last {LOG_INTERVAL}s: {window_ticks}"
            )
            window_ticks   = 0
            window_syms_ok = set()
            last_error     = None
            last_log_time  = now

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print(f"\n[{BROKER}] Stopped by user.")

except Exception as e:
    last_error = traceback.format_exc()
    print(f"[{BROKER}] FATAL:\n{last_error}")
    log_health("error", len(window_syms_ok), window_ticks, last_error, time.time() - start_time)

finally:
    log_health("shutdown", len(window_syms_ok), window_ticks, last_error, time.time() - start_time)
    conn.close()
    MT5.shutdown()
    print(f"[{BROKER}] Shutdown complete.")
CREATE TABLE IF NOT EXISTS ticks (
    symbol      TEXT,
    time        INTEGER,
    bid         REAL,
    ask         REAL,
    last        REAL,
    volume      INTEGER,
    time_msc    INTEGER,
    flags       INTEGER,
    volume_real REAL,
    PRIMARY KEY (symbol, time_msc)
);

CREATE TABLE IF NOT EXISTS health_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            INTEGER NOT NULL,
    status        TEXT    NOT NULL,
    symbols_ok    INTEGER,
    ticks_window  INTEGER,
    last_error    TEXT,
    uptime_sec    INTEGER
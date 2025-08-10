import MetaTrader5 as MT5
from datetime import datetime

if not MT5.initialize():
    raise RuntimeError(f"MT5 init failed: {MT5.last_error()}")

tradeable_now = []
for s in MT5.symbols_get("*"):
    info = MT5.symbol_info(s.name)
    if not info:
        continue
    if info.trade_mode != MT5.SYMBOL_TRADE_MODE_DISABLED and info.session_trade:
        tradeable_now.append(s.name)

with open(f'tradeable.txt', 'w') as f:
    f.write('\n'.join(tradeable_now))

print(f"Currently tradeable symbols: {len(tradeable_now)}")

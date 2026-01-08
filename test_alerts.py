from fetch import fetch_trades
from detector import detect_insider
from alerts import format_alert

trades = fetch_trades(10)

if not trades:
    print("No trades fetched")
    exit()

for t in trades:
    if detect_insider(t):
        print(format_alert(t, signals=["large_trade"]))
        break
else:
    print("No insider trades detected")

from dotenv import load_dotenv
load_dotenv()

from pybit.unified_trading import HTTP
from os import environ

# Bybit 세션 준비
BYBIT_API_KEY = environ.get('BYBIT_API_KEY')
BYBIT_API_SECRET = environ.get('BYBIT_API_SECRET')
session = HTTP(
    testnet=True,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

def get_tick_size(symbol, session):
    try:
        res = session.get_instruments_info(category="linear", symbol=symbol)
        tick_size = float(res['result']['list'][0]['priceFilter']['tickSize'])
        return tick_size
    except Exception as e:
        print("틱사이즈 조회 실패:", e)
        return 1.0

def get_recent_lows(symbol, session, interval="15"):
    try:
        res = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=6
        )
        klines = res['result']['list']
        print(klines)
        klines = sorted(klines, key=lambda x: int(x[0]))
        lows = [float(k[3]) for k in klines[:-1]]
        return lows
    except Exception as e:
        print("OHLCV(캔들) 조회 실패:", e)
        return []

def get_current_price(symbol, session):
    try:
        ticker = session.get_tickers(category="linear", symbol=symbol)
        return float(ticker['result']['list'][0]['lastPrice'])
    except Exception as e:
        print("현재가 조회 실패:", e)
        return None

# ========== 테스트 실행 ==========

symbol = "ETHUSDT"
tick_offset = 5
fallback_pct = 0.01  # 1%

tick_size = get_tick_size(symbol, session)
print(f"[{symbol}] 틱사이즈: {tick_size}")

lows = get_recent_lows(symbol, session, interval="15")
print("최근 5개 저점(15분봉):", lows)

entry_price = get_current_price(symbol, session)
print("실시간 진입가격:", entry_price)

# 1. 진입가격보다 낮은 저점(지지선 후보) 중복 제거
support_candidates = list(set([low for low in lows if low < entry_price]))

# 2. 진입가와의 차이 기준(진입가 - 저점) 오름차순 정렬
support_candidates_sorted = sorted(support_candidates, key=lambda x: abs(entry_price - x))

print("진입가격보다 낮은 저점(지지선 후보, 중복제거):", support_candidates_sorted)

# 3. 1차/2차 지지선 안내 (가까운 순서대로!)
if len(support_candidates_sorted) >= 2:
    print(f"1차 지지선: {support_candidates_sorted[0]}, 2차 지지선: {support_candidates_sorted[1]}")
elif len(support_candidates_sorted) == 1:
    print(f"1차 지지선만 존재: {support_candidates_sorted[0]} (2차 지지선은 없음)")
else:
    print("진입가격보다 낮은 저점(지지선)이 존재하지 않습니다.")

# 4. 손절값 계산
if len(support_candidates_sorted) >= 2:
    stop_loss = support_candidates_sorted[1] - tick_size * tick_offset
    # 1% 손절보다 더 깊으면 1% 고정 손절
    one_pct_below = entry_price * (1 - fallback_pct)
    if stop_loss < one_pct_below:
        stop_loss = round(one_pct_below, 8)
        print(f"2차 지지선({support_candidates_sorted[1]}) - 5틱 손절값이 진입가 대비 1% 아래로 내려가 1% 고정 손절이 적용됩니다.")
    else:
        print(f"손절값: 2차 지지선({support_candidates_sorted[1]}) - 5틱 = {stop_loss} 입니다")
elif len(support_candidates_sorted) == 1:
    stop_loss = round(entry_price * (1 - fallback_pct), 8)
    print(f"손절값: 1차 지지선만 있으므로 1% 고정 손절({stop_loss})입니다")
else:
    stop_loss = round(entry_price * (1 - fallback_pct), 8)
    print(f"손절값: 진입가가 최저가여서 1% 고정 손절({stop_loss})입니다")

# 5. 손절값이 진입가 대비 몇 %인지 안내
if stop_loss and entry_price:
    stop_pct = (entry_price - stop_loss) / entry_price * 100
    print(f"손절값은 {stop_loss}로, 진입가격 대비 약 {stop_pct:.2f}% 입니다.")

import os
from pybit.unified_trading import HTTP

# 1. 환경변수에서 API 키 불러오기
api_key = os.environ.get("BYBIT_API_KEY")
api_secret = os.environ.get("BYBIT_API_SECRET")

# 2. pybit 세션 생성 (테스트넷)
session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

# 3. 현재가 조회 함수
def get_price(symbol="BTCUSDT"):
    """
    지정한 심볼(기본 BTCUSDT)의 현재가(마지막 체결가)를 조회
    """
    try:
        ticker = session.get_tickers(category="linear", symbol=symbol)
        return float(ticker['result']['list'][0]['lastPrice'])
    except Exception as e:
        return f"현재가조회 에러: {e}"

# 4. 결과 출력
if __name__ == "__main__":
    symbol = "BTCUSDT"   # 여기서 원하는 심볼로 변경 가능 (예: ETHUSDT)
    price = get_price(symbol)
    print(f"{symbol} 현재가:", price)

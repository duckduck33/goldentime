from dotenv import load_dotenv
load_dotenv()

import os
from pybit.unified_trading import HTTP

# 1. 환경변수에서 API 키/시크릿 불러오기
api_key = os.environ.get("BYBIT_API_KEY")
api_secret = os.environ.get("BYBIT_API_SECRET")

# 2. pybit 세션 생성 (테스트넷)
session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

# 3. 시장가 포지션 진입(롱/숏)
def open_position(symbol, side, qty):
    """
    지정 심볼/방향/수량으로 시장가 주문 (롱=Buy, 숏=Sell)
    side: "Buy" (롱), "Sell" (숏)
    """
    try:
        order = session.place_order(
            category="linear",        # 선물(USDT-Perp)
            symbol=symbol,            # 예: "BTCUSDT"
            side=side,                # "Buy" 또는 "Sell"
            orderType="Market",       # 시장가 주문
            qty=qty,                  # 주문 수량
            reduceOnly=False          # 신규 진입
        )
        return order
    except Exception as e:
        return f"시장가주문 에러: {e}"

# 4. 포지션 전량 청산(시장가)
def close_position(symbol, side, qty):
    """
    진입방향 반대 side로 reduceOnly=True 시장가 주문 (포지션 청산)
    """
    try:
        close_side = "Sell" if side == "Buy" else "Buy"
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=close_side,
            orderType="Market",
            qty=qty,
            reduceOnly=True
        )
        return order
    except Exception as e:
        return f"청산 에러: {e}"

# 5. 테스트 실행부
if __name__ == "__main__":
    symbol = "BTCUSDT"     # 거래할 티커
    qty = 0.01             # 수량 (테스트넷이므로 소량)
    direction = "Buy"      # "Buy"=롱, "Sell"=숏

    # 1) 롱(매수) 진입
    print(f"[1] {symbol} 시장가 {direction} 진입 ({qty}개)")
    order = open_position(symbol, direction, qty)
    print("주문 결과:", order)

    # 2) 청산(반대 포지션 시장가 전량 종료)
    input("\n청산하려면 엔터를 누르세요...")
    print(f"[2] {symbol} 시장가 청산 ({qty}개)")
    close_result = close_position(symbol, direction, qty)
    print("청산 결과:", close_result)

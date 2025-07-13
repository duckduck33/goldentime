from dotenv import load_dotenv
load_dotenv()

import os
import time
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

def open_position(symbol, side, qty):
    """
    지정 심볼/방향/수량으로 시장가 주문 (롱=Buy, 숏=Sell)
    에러 발생 시 에러 메시지(str) 반환
    """
    try:
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
            reduceOnly=False
        )
        return order
    except Exception as e:
        return f"시장가주문 에러: {e}"

if __name__ == "__main__":
    symbol = "AXSUSDT"     # 거래할 티커
    qty = 111            # 수량 (테스트넷)
    direction = "Sell"      # "Buy"=롱, "Sell"=숏

    # 1) 롱(매수) 진입
    print(f"[1] {symbol} 시장가 {direction} 진입 ({qty}개)")
    order = open_position(symbol, direction, qty)
    print("주문 결과:", order)

    # order가 dict(정상 응답)인지, str(에러)인지 타입 체크
    if not isinstance(order, dict):
        print("→ 주문이 정상적으로 생성되지 않았습니다. (에러 발생)")
        # 에러 상황에서는 이후 로직 실행하지 않고 종료
    else:
        # 주문ID 추출
        order_id = order.get('result', {}).get('orderId')
        if order_id:
            # 주문 체결내역을 여러 번 재조회 (최대 5초, 0.5초 간격)
            avg_price = None
            for _ in range(10):  # 최대 10번(5초) 반복
                order_info = session.get_order_history(
                    category="linear",
                    symbol=symbol,
                    orderId=order_id
                )
                # 'list'가 비어있지 않을 때만 체결가격 추출
                if (
                    order_info
                    and 'result' in order_info
                    and 'list' in order_info['result']
                    and len(order_info['result']['list']) > 0
                ):
                    avg_price = order_info['result']['list'][0].get('avgPrice')
                    break
                time.sleep(0.5)  # 0.5초 대기 후 재시도

            if avg_price:
                print(f"→ [체결가격] 진입가: {avg_price} USDT")
            else:
                print("→ 체결가격 정보를 찾을 수 없습니다. (주문 체결 지연)")
        else:
            print("→ 주문ID 없음, 체결가격 조회 불가")

from dotenv import load_dotenv
load_dotenv()

import os
import time
from pybit.unified_trading import HTTP

# 1. 환경변수에서 API 키/시크릿 불러오기 (.env 파일에 미리 세팅 필요)
api_key = os.environ.get("BYBIT_API_KEY")
api_secret = os.environ.get("BYBIT_API_SECRET")

# 2. pybit 세션 생성 (테스트넷=True)
session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

def open_position(symbol, side, qty):
    """
    지정 심볼/방향/수량으로 시장가 주문 (롱=Buy, 숏=Sell)
    체결가격까지 반환
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
        # 주문ID 추출
        order_id = order.get('result', {}).get('orderId')
        if not order_id:
            return order, None
        # 체결가격 조회 (최대 5초 대기)
        avg_price = None
        for _ in range(10):
            order_info = session.get_order_history(
                category="linear",
                symbol=symbol,
                orderId=order_id
            )
            if (
                order_info
                and 'result' in order_info
                and 'list' in order_info['result']
                and len(order_info['result']['list']) > 0
            ):
                avg_price = order_info['result']['list'][0].get('avgPrice')
                break
            time.sleep(0.5)
        return order, float(avg_price) if avg_price else None
    except Exception as e:
        return f"시장가주문 에러: {e}", None

def place_tp_limit_order(symbol, entry_price, side, qty, tp_ratio=0.01):
    """
    익절(수익실현) 주문을 지정가(리밋)로 절반 수량만 예약
    """
    # 익절 가격 및 수량 계산 (롱: 위, 숏: 아래)
    if side == "Buy":
        tp_price = round(entry_price * (1 + tp_ratio), 2)
        close_side = "Sell"
    else:
        tp_price = round(entry_price * (1 - tp_ratio), 2)
        close_side = "Buy"
    tp_qty = round(qty / 2, 4)  # 절반 수량, 소수점 4자리

    try:
        tp_order = session.place_order(
            category="linear",
            symbol=symbol,
            side=close_side,
            orderType="Limit",           # 지정가(리밋) 주문
            price=str(tp_price),         # 익절가
            qty=tp_qty,                  # 익절 수량(절반)
            reduceOnly=True,             # 포지션 청산 전용
            timeInForce="GTC"            # 기본 GTC
        )
        print(f"[익절 지정가 주문] 가격: {tp_price}, 수량: {tp_qty}, 결과: {tp_order}")
        return tp_order
    except Exception as e:
        print(f"익절 지정가 주문 에러: {e}")
        return None

def place_stop_loss(symbol, entry_price, side, qty, sl_ratio=0.005):
    """
    손절(Stop Loss) 주문을 set_trading_stop으로 전체 포지션 예약
    """
    # 손절가 계산 (롱: 아래, 숏: 위)
    if side == "Buy":
        sl_price = round(entry_price * (1 - sl_ratio), 2)
    else:
        sl_price = round(entry_price * (1 + sl_ratio), 2)
    try:
        sl_result = session.set_trading_stop(
            category="linear",
            symbol=symbol,
            stopLoss=str(sl_price),
            slTriggerBy="LastPrice"
        )
        print(f"[손절 예약] 손절가: {sl_price}, 결과: {sl_result}")
        return sl_result
    except Exception as e:
        print(f"손절 예약 에러: {e}")
        return None

if __name__ == "__main__":
    symbol = "AXSUSDT"     # 거래할 티커
    qty = 111            # 수량 (테스트넷)
    direction = "Sell"      # "Buy"=롱, "Sell"=숏
    # 1) 시장가 진입 (체결가 확인)
    print(f"[1] {symbol} 시장가 {direction} 진입 ({qty}개)")
    order, entry_price = open_position(symbol, direction, qty)
    print("주문 결과:", order)
    if not isinstance(order, dict) or entry_price is None:
        print("→ 주문 실패 혹은 체결가격 없음. TP/SL 예약 미실행.")
    else:
        print(f"→ [체결가격] 진입가: {entry_price} USDT")

        # 2) 익절 주문: 지정가(리밋)로 절반 수량만 예약 (익절가 1% 위/아래)
        place_tp_limit_order(symbol, entry_price, direction, qty, tp_ratio=0.01)
        # 3) 손절 예약: set_trading_stop으로 전량 (손절가 0.5% 아래/위)
        place_stop_loss(symbol, entry_price, direction, qty, sl_ratio=0.005)

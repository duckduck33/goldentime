# trade_worker.py (interval "30"으로만 수정, 나머지는 원본 그대로!)

from dotenv import load_dotenv
load_dotenv()

import os
import time
import math
import logging
from datetime import datetime
from pybit.unified_trading import HTTP
import threading

from stop_loss_calc import get_long_stop_loss, get_short_stop_loss

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("log.txt", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

BYBIT_API_KEY = os.environ.get('BYBIT_API_KEY')
BYBIT_API_SECRET = os.environ.get('BYBIT_API_SECRET')

session = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,   # 실제 API 키 문자열
    api_secret=BYBIT_API_SECRET
)

trade_status = {
    "running": False,
    "info": {},
    "error": None
}

def get_balance(coin: str = "USDT"):
    try:
        res = session.get_wallet_balance(accountType="UNIFIED", coin=coin)
        return res['result']['list'][0]['totalEquity']
    except Exception as e:
        logging.error(f"잔고조회 에러: {e}")
        return f"잔고조회 에러: {e}"

def get_price(symbol):
    try:
        ticker = session.get_tickers(category="linear", symbol=symbol)
        return float(ticker['result']['list'][0]['lastPrice'])
    except Exception as e:
        logging.error(f"가격조회 에러: {e}")
        return None

def open_position(symbol, side, qty):
    try:
        res = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
            reduceOnly=False
        )
        return res
    except Exception as e:
        logging.error(f"진입실패: {e}")
        return f"진입실패: {e}"

def close_position(symbol, side, qty):
    try:
        close_side = "Sell" if side == "Buy" else "Buy"
        res = session.place_order(
            category="linear",
            symbol=symbol,
            side=close_side,
            orderType="Market",
            qty=qty,
            reduceOnly=True
        )
        return res
    except Exception as e:
        logging.error(f"청산실패: {e}")
        return f"청산실패: {e}"

def get_tick_size(symbol):
    try:
        res = session.get_instruments_info(category="linear", symbol=symbol)
        tick_size = float(res['result']['list'][0]['priceFilter']['tickSize'])
        return tick_size
    except Exception as e:
        logging.error(f"틱사이즈 조회 실패: {e}")
        return 1.0

def get_min_qty(symbol):
    try:
        res = session.get_instruments_info(category="linear", symbol=symbol)
        min_qty = float(res['result']['list'][0]['lotSizeFilter']['minOrderQty'])
        return min_qty
    except Exception as e:
        logging.error(f"최소 주문수량 조회 실패: {e}")
        return 0.001

def get_qty_step(symbol):
    try:
        res = session.get_instruments_info(category="linear", symbol=symbol)
        step = float(res['result']['list'][0]['lotSizeFilter']['qtyStep'])
        return step
    except Exception as e:
        logging.error(f"수량 스텝 조회 실패: {e}")
        return 0.001

def adjust_qty_by_lot_size(symbol, qty):
    min_qty = get_min_qty(symbol)
    step = get_qty_step(symbol)
    qty = max(qty, min_qty)
    adjusted_qty = math.floor(qty / step) * step
    return round(adjusted_qty, 8)

# ✅ 여기가 30분봉 5캔들로 바뀐 부분!
def get_recent_lows(symbol, session, interval="30"):
    try:
        res = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=6
        )
        klines = res['result']['list']
        klines = sorted(klines, key=lambda x: int(x[0]))
        lows = [float(k[3]) for k in klines[:-1]]
        return lows
    except Exception as e:
        logging.error(f"OHLCV(캔들) 조회 실패: {e}")
        return []

def get_recent_highs(symbol, session, interval="30"):
    try:
        res = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=6
        )
        klines = res['result']['list']
        klines = sorted(klines, key=lambda x: int(x[0]))
        highs = [float(k[2]) for k in klines[:-1]]
        return highs
    except Exception as e:
        logging.error(f"OHLCV(캔들) 조회 실패: {e}")
        return []

def get_position_size(symbol):
    try:
        res = session.get_positions(
            category="linear",
            symbol=symbol
        )
        pos_list = res['result']['list']
        if not pos_list:
            return 0.0
        pos = pos_list[0]
        return float(pos['size'])
    except Exception as e:
        logging.error(f"포지션 조회 실패: {e}")
        return 0.0

def place_tp_limit_order(symbol, side, qty, tp_price):
    close_side = "Sell" if side == "Buy" else "Buy"
    tp_qty = adjust_qty_by_lot_size(symbol, qty / 2)
    try:
        tp_order = session.place_order(
            category="linear",
            symbol=symbol,
            side=close_side,
            orderType="Limit",
            price=str(tp_price),
            qty=tp_qty,
            reduceOnly=True,
            timeInForce="GTC"
        )
        logging.info(f"[익절 지정가 주문] 가격: {tp_price}, 수량: {tp_qty}, 결과: {tp_order}")
        tp_order_id = tp_order['result'].get('orderId') if tp_order and 'result' in tp_order and 'orderId' in tp_order['result'] else None
        return tp_order, tp_order_id
    except Exception as e:
        logging.error(f"익절 지정가 주문 에러: {e}")
        return None, None

def place_stop_loss(symbol, side, sl_price):
    try:
        sl_result = session.set_trading_stop(
            category="linear",
            symbol=symbol,
            stopLoss=str(sl_price),
            slTriggerBy="LastPrice"
        )
        logging.info(f"[손절 예약] 손절가: {sl_price}, 결과: {sl_result}")
        sl_order_id = sl_result['result'].get('orderId') if sl_result and 'result' in sl_result and 'orderId' in sl_result['result'] else None
        return sl_result, sl_order_id
    except Exception as e:
        logging.error(f"손절 예약 에러: {e}")
        return None, None

def cancel_order(symbol, order_id):
    if not order_id:
        return
    try:
        res = session.cancel_order(
            category="linear",
            symbol=symbol,
            orderId=order_id
        )
        logging.info(f"[주문취소] 주문ID: {order_id}, 결과: {res}")
    except Exception as e:
        logging.error(f"[주문취소 에러] {e}")

def trade_worker(
    position_type, symbol, fixed_loss, entry_time, exit_time,
    take_profit=None, stop_loss=None,
    immediate=False
):
    """
    고정손실액 입력 -> 자동 진입수량 계산(최소수량/틱 자동 보정) -> 주문/감시
    강제중단 시 포지션 청산 + 예약주문 취소까지 포함
    """
    trade_status['running'] = True
    trade_status['info'] = {
        "position_type": position_type,
        "symbol": symbol,
        "fixed_loss": fixed_loss,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "entry_price": None,
        "exit_price": None,
        "entry_order": None,
        "tp_order": None,
        "sl_order": None,
        "tp_order_id": None,
        "sl_order_id": None,
        "tp_price": None,
        "sl_price": None,
        "stop_loss_msg": None,
        "exit_at": None,
        "immediate": immediate
    }
    try:
        entry_dt = datetime.strptime(entry_time, "%Y-%m-%d %H:%M")
        exit_dt = datetime.strptime(exit_time, "%Y-%m-%d %H:%M")
        entry_fired = False
        logging.info(f"골든타임매매봇 시작합니다.")
        while not entry_fired:
            if not trade_status["running"]:
                break
            now = datetime.now()
            if immediate or now >= entry_dt:
                side = "Buy" if position_type == "long" else "Sell"

                # 1) 진입가(현재가) 조회
                executed_price = get_price(symbol)

                # 2) 손절가 자동계산
                tick_size = get_tick_size(symbol)
                interval = "30"   # ✅ 여기만 30분봉으로!
                tp_ratio = 0.02
                if position_type == "long":
                    lows = get_recent_lows(symbol, session, interval=interval)
                    sl_price, scenario_msg, stop_pct = get_long_stop_loss(
                        lows=lows,
                        entry_price=executed_price,
                        tick_size=tick_size,
                        tick_offset=5,
                        fallback_pct=0.01,
                        take_profit_ratio=tp_ratio
                    )
                    logging.info(f"[손절/익절 시나리오]\n{scenario_msg}")
                else:
                    highs = get_recent_highs(symbol, session, interval=interval)
                    sl_price, scenario_msg, stop_pct = get_short_stop_loss(
                        highs=highs,
                        entry_price=executed_price,
                        tick_size=tick_size,
                        tick_offset=5,
                        fallback_pct=0.01,
                        take_profit_ratio=tp_ratio
                    )
                    logging.info(f"[손절/익절 시나리오]\n{scenario_msg}")

                # 3) 고정손실액으로 권장 진입수량 계산 & minQty/틱 자동보정
                loss_amount = float(fixed_loss)
                raw_qty = loss_amount / abs(executed_price - sl_price)
                qty = adjust_qty_by_lot_size(symbol, raw_qty)
                logging.info(f"[고정손실] {loss_amount}$, 진입가:{executed_price}, 손절가:{sl_price} → 권장수량(보정): {qty}")

                # 4) 시장가 진입
                entry_order = open_position(symbol, side, qty)
                trade_status['info']['entry_order'] = entry_order
                trade_status['info']['entry_at'] = now.strftime("%Y-%m-%d %H:%M:%S")
                trade_status['info']['entry_price'] = executed_price

                # 5) 익절/손절 예약 + 주문ID 저장
                if take_profit not in [None, ""]:
                    tp_price = float(take_profit)
                else:
                    tp_price = round(executed_price * (1 + tp_ratio), 8) if position_type == "long" else round(executed_price * (1 - tp_ratio), 8)

                tp_result, tp_order_id = place_tp_limit_order(symbol, side, qty, tp_price)
                sl_result, sl_order_id = place_stop_loss(symbol, side, sl_price)
                trade_status['info']['tp_order'] = tp_result
                trade_status['info']['sl_order'] = sl_result
                trade_status['info']['tp_order_id'] = tp_order_id
                trade_status['info']['sl_order_id'] = sl_order_id
                trade_status['info']['tp_price'] = tp_price
                trade_status['info']['sl_price'] = sl_price

                entry_fired = True
                logging.info(f"[포지션진입, 익절, 손절주문 등록완료] 진입가: {executed_price}, 수량: {qty}")
                break
            time.sleep(1)

        close_fired = False
        position_closed = False

        # ✅ 강제중단 신호 체크 루프 (최상단에서 무조건 우선)
        while True:
            # 1) 강제중단 신호 최우선 체크
            if not trade_status['running']:
                # 1. 포지션 있으면 시장가로 청산
                qty = get_position_size(symbol)
                if qty > 0:
                    close_side = "Buy" if position_type == "short" else "Sell"
                    close_position(symbol, close_side, qty)
                    logging.info("[강제중단] 남은 포지션을 시장가로 강제 청산함.")
                # 2. 예약 주문 취소
                tp_order_id = trade_status['info'].get('tp_order_id')
                sl_order_id = trade_status['info'].get('sl_order_id')
                cancel_order(symbol, tp_order_id)
                cancel_order(symbol, sl_order_id)
                logging.info("[강제중단] 익절/손절 예약주문 자동 취소 완료.")
                break

            now = datetime.now()
            # 2) 종료시간 도달하면 시장가 청산
            if now >= exit_dt and not close_fired:
                side = "Buy" if position_type == "long" else "Sell"
                close_order = close_position(symbol, side, qty)
                trade_status['info']['exit_order'] = close_order
                trade_status['info']['exit_price'] = get_price(symbol)
                trade_status['info']['exit_at'] = now.strftime("%Y-%m-%d %H:%M:%S")
                logging.info("[포지션 청산] 매도시간 도달하여 포지션을 종료했습니다.")
                close_fired = True
                break

            pos_size = get_position_size(symbol)
            if pos_size == 0 and not position_closed:
                exit_price = get_price(symbol)
                trade_status['info']['exit_price'] = exit_price
                logging.info(f"[체결] 포지션 종료 (체결가: {exit_price})")
                trade_status['info']['exit_at'] = now.strftime("%Y-%m-%d %H:%M:%S")
                position_closed = True
                break

            time.sleep(2)

    except Exception as e:
        logging.exception(f"[trade_worker 전체 에러] {e}")
        trade_status['error'] = str(e)
    finally:
        trade_status['running'] = False

def start_trade_thread(**kwargs):
    if trade_status["running"]:
        return False, "이미 매매 중입니다."
    th = threading.Thread(target=trade_worker, kwargs=kwargs)
    th.daemon = True
    th.start()
    return True, "매매 시작됨"

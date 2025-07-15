import os
import time
import math
import logging
from datetime import datetime
import pytz
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

# === 공통 pybit 유틸리티 함수들 ===

def get_balance(api_key, api_secret, coin: str = "USDT"):
    session = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)
    try:
        res = session.get_wallet_balance(accountType="UNIFIED", coin=coin)
        return res['result']['list'][0]['totalEquity']
    except Exception as e:
        logging.error(f"잔고조회 에러: {e}")
        return f"잔고조회 에러: {e}"

def get_price(session, symbol):
    try:
        ticker = session.get_tickers(category="linear", symbol=symbol)
        return float(ticker['result']['list'][0]['lastPrice'])
    except Exception as e:
        logging.error(f"가격조회 에러: {e}")
        return None

def open_position(session, symbol, side, qty):
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

def close_position(session, symbol, side, qty):
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

def get_tick_size(session, symbol):
    try:
        res = session.get_instruments_info(category="linear", symbol=symbol)
        tick_size = float(res['result']['list'][0]['priceFilter']['tickSize'])
        return tick_size
    except Exception as e:
        logging.error(f"틱사이즈 조회 실패: {e}")
        return 1.0

def get_min_qty(session, symbol):
    try:
        res = session.get_instruments_info(category="linear", symbol=symbol)
        min_qty = float(res['result']['list'][0]['lotSizeFilter']['minOrderQty'])
        return min_qty
    except Exception as e:
        logging.error(f"최소 주문수량 조회 실패: {e}")
        return 0.001

def get_qty_step(session, symbol):
    try:
        res = session.get_instruments_info(category="linear", symbol=symbol)
        step = float(res['result']['list'][0]['lotSizeFilter']['qtyStep'])
        return step
    except Exception as e:
        logging.error(f"수량 스텝 조회 실패: {e}")
        return 0.001

def adjust_qty_by_lot_size(session, symbol, qty):
    min_qty = get_min_qty(session, symbol)
    step = get_qty_step(session, symbol)
    qty = max(qty, min_qty)
    adjusted_qty = math.floor(qty / step) * step
    return round(adjusted_qty, 8)

def get_recent_lows(session, symbol, interval="30"):
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

def get_recent_highs(session, symbol, interval="30"):
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

def get_position_size(session, symbol):
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

def place_tp_limit_order(session, symbol, side, qty, tp_price):
    close_side = "Sell" if side == "Buy" else "Buy"
    tp_qty = adjust_qty_by_lot_size(session, symbol, qty / 2)
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

def place_stop_loss(session, symbol, side, sl_price):
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

def cancel_order(session, symbol, order_id):
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

# === 강제 청산/주문취소 ===
def force_exit_position(user_id, symbol, position_type, api_key, api_secret, trade_statuses):
    """
    - 포지션 시장가 강제 청산
    - TP/SL 예약주문 모두 취소
    """
    try:
        session = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)
        side = "Buy" if position_type == "long" else "Sell"
        qty = get_position_size(session, symbol)

        if qty > 0:
            close_order = close_position(session, symbol, side, qty)
            # trade_statuses[user_id]['info']['exit_order'] = close_order
            # trade_statuses[user_id]['info']['exit_price'] = get_price(session, symbol)
            # trade_statuses[user_id]['info']['exit_at'] = now_kst.strftime("%Y-%m-%d %H:%M:%S")
        # TP/SL 예약주문 취소도 반드시
        tp_order_id = trade_statuses[user_id]['info'].get('tp_order_id')
        sl_order_id = trade_statuses[user_id]['info'].get('sl_order_id')
        cancel_order(session, symbol, tp_order_id)
        cancel_order(session, symbol, sl_order_id)
        close_fired = True

    except Exception as e:
        logging.error(f"[강제종료 오류] {e}")

# === 실제 매매 쓰레드 ===
def trade_worker(
    user_id, trade_statuses,
    api_key, api_secret,
    position_type, symbol, fixed_loss, entry_time, exit_time,
    take_profit=None, stop_loss=None,
    immediate=False
):
    """
    사용자별 trade_statuses[user_id]에만 상태 기록/조회
    """
    session = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)
    kst = pytz.timezone("Asia/Seoul")
    try:
        # 유저별 상태 딕셔너리 생성/초기화
        trade_statuses[user_id] = {
            "running": True,
            "info": {
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
            },
            "error": None
        }

        entry_fired = False
        entry_dt_kst = kst.localize(datetime.strptime(entry_time, "%Y-%m-%d %H:%M"))
        exit_dt_kst = kst.localize(datetime.strptime(exit_time, "%Y-%m-%d %H:%M"))
        entry_dt_utc = entry_dt_kst.astimezone(pytz.utc)
        exit_dt_utc = exit_dt_kst.astimezone(pytz.utc)

        while not entry_fired:
            if not trade_statuses[user_id]["running"]:
                break

            now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)

            if immediate or now_utc >= entry_dt_utc:
                side = "Buy" if position_type == "long" else "Sell"
                executed_price = get_price(session, symbol)
                tick_size = get_tick_size(session, symbol)
                interval = "30"
                tp_ratio = 0.02

                if position_type == "long":
                    lows = get_recent_lows(session, symbol, interval=interval)
                    sl_price, scenario_msg, stop_pct = get_long_stop_loss(
                        lows=lows,
                        entry_price=executed_price,
                        tick_size=tick_size,
                        tick_offset=5,
                        fallback_pct=0.01,
                        take_profit_ratio=tp_ratio
                    )
                else:
                    highs = get_recent_highs(session, symbol, interval=interval)
                    sl_price, scenario_msg, stop_pct = get_short_stop_loss(
                        highs=highs,
                        entry_price=executed_price,
                        tick_size=tick_size,
                        tick_offset=5,
                        fallback_pct=0.01,
                        take_profit_ratio=tp_ratio
                    )

                loss_amount = float(fixed_loss)
                raw_qty = loss_amount / abs(executed_price - sl_price)
                qty = adjust_qty_by_lot_size(session, symbol, raw_qty)

                entry_order = open_position(session, symbol, side, qty)
                trade_statuses[user_id]['info']['entry_order'] = entry_order
                trade_statuses[user_id]['info']['entry_at'] = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
                trade_statuses[user_id]['info']['entry_price'] = executed_price

                if take_profit not in [None, ""]:
                    tp_price = float(take_profit)
                else:
                    tp_price = round(executed_price * (1 + tp_ratio), 8) if position_type == "long" else round(executed_price * (1 - tp_ratio), 8)

                tp_result, tp_order_id = place_tp_limit_order(session, symbol, side, qty, tp_price)
                sl_result, sl_order_id = place_stop_loss(session, symbol, side, sl_price)
                trade_statuses[user_id]['info']['tp_order'] = tp_result
                trade_statuses[user_id]['info']['sl_order'] = sl_result
                trade_statuses[user_id]['info']['tp_order_id'] = tp_order_id
                trade_statuses[user_id]['info']['sl_order_id'] = sl_order_id
                trade_statuses[user_id]['info']['tp_price'] = tp_price
                trade_statuses[user_id]['info']['sl_price'] = sl_price

                entry_fired = True
                break

            time.sleep(1)

        close_fired = False
        position_closed = False

        while True:
            # 1) 매매 중단 요청(강제종료) 시 모든 포지션/주문 일괄 종료
            if not trade_statuses[user_id]['running']:
                force_exit_position(user_id, symbol, position_type, api_key, api_secret, trade_statuses)

                # side = "Buy" if position_type == "long" else "Sell"
                # qty = get_position_size(session, symbol)
                # if qty > 0:
                #     close_order = close_position(session, symbol, side, qty)
                #     trade_statuses[user_id]['info']['exit_order'] = close_order
                #     trade_statuses[user_id]['info']['exit_price'] = get_price(session, symbol)
                #     trade_statuses[user_id]['info']['exit_at'] = now_kst.strftime("%Y-%m-%d %H:%M:%S")
                # # TP/SL 예약주문 취소도 반드시
                # tp_order_id = trade_statuses[user_id]['info'].get('tp_order_id')
                # sl_order_id = trade_statuses[user_id]['info'].get('sl_order_id')
                # cancel_order(session, symbol, tp_order_id)
                # cancel_order(session, symbol, sl_order_id)
                # close_fired = True
                break
            
            now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
            now_kst = now_utc.astimezone(kst)

            # 2) 지정 종료시간 도달 시 자동 종료
            if now_utc >= exit_dt_utc and not close_fired:
                force_exit_position(user_id, symbol, position_type, api_key, api_secret, trade_statuses)

                # side = "Buy" if position_type == "long" else "Sell"
                # qty = get_position_size(session, symbol)
                # if qty > 0:
                #     close_order = close_position(session, symbol, side, qty)
                #     trade_statuses[user_id]['info']['exit_order'] = close_order
                #     trade_statuses[user_id]['info']['exit_price'] = get_price(session, symbol)
                #     trade_statuses[user_id]['info']['exit_at'] = now_kst.strftime("%Y-%m-%d %H:%M:%S")
                # # TP/SL 예약주문 취소도 반드시
                # tp_order_id = trade_statuses[user_id]['info'].get('tp_order_id')
                # sl_order_id = trade_statuses[user_id]['info'].get('sl_order_id')
                # cancel_order(session, symbol, tp_order_id)
                # cancel_order(session, symbol, sl_order_id)
                # close_fired = True
                break

            # 3) 포지션이 사라지면(청산됨) 기록 후 종료
            pos_size = get_position_size(session, symbol)
            if pos_size == 0 and not position_closed:
                exit_price = get_price(session, symbol)
                trade_statuses[user_id]['info']['exit_price'] = exit_price
                trade_statuses[user_id]['info']['exit_at'] = now_kst.strftime("%Y-%m-%d %H:%M:%S")
                position_closed = True
                break

            time.sleep(2)

    except Exception as e:
        logging.exception(f"[trade_worker 전체 에러] {e}")
        trade_statuses[user_id]['error'] = str(e)
    finally:
        # 남아있는 포지션/주문 강제종료(꼬임 방지)
        if trade_statuses[user_id]['running']:
            force_exit_position(user_id, symbol, position_type, api_key, api_secret, trade_statuses)
        trade_statuses[user_id]['running'] = False

# === 스레드 실행 함수: user_id, trade_statuses 필수 ===
def start_trade_thread(**kwargs):
    user_id = kwargs.get("user_id")
    trade_statuses = kwargs.get("trade_statuses")
    if user_id in trade_statuses and trade_statuses[user_id].get("running"):
        return False, "이미 매매 중입니다."
    th = threading.Thread(target=trade_worker, kwargs=kwargs)
    th.daemon = True
    th.start()
    return True, "매매 시작됨"

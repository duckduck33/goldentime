from dotenv import load_dotenv
load_dotenv()

import os
import time
from datetime import datetime
from pybit.unified_trading import HTTP
import threading

from stop_loss_calc import get_long_stop_loss, get_short_stop_loss

BYBIT_API_KEY = os.environ.get('BYBIT_API_KEY')
BYBIT_API_SECRET = os.environ.get('BYBIT_API_SECRET')

session = HTTP(
    testnet=True,
    api_key=BYBIT_API_KEY,
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
        return f"잔고조회 에러: {e}"

def get_price(symbol):
    try:
        ticker = session.get_tickers(category="linear", symbol=symbol)
        return float(ticker['result']['list'][0]['lastPrice'])
    except Exception as e:
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
        return f"청산실패: {e}"

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
        klines = sorted(klines, key=lambda x: int(x[0]))
        lows = [float(k[3]) for k in klines[:-1]]
        return lows
    except Exception as e:
        print("OHLCV(캔들) 조회 실패:", e)
        return []

def get_recent_highs(symbol, session, interval="15"):
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
        print("OHLCV(캔들) 조회 실패:", e)
        return []

def place_trigger_order(symbol, side, qty, trigger_price, direction):
    try:
        res = session.place_conditional_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
            triggerDirection=direction,
            triggerPrice=trigger_price,
            reduceOnly=True
        )
        return res
    except Exception as e:
        print(f"트리거주문 실패: {e}")
        return None

def cancel_conditional_order(symbol, order_id):
    try:
        res = session.cancel_conditional_order(
            category="linear",
            symbol=symbol,
            orderId=order_id
        )
        return res
    except Exception as e:
        print(f"조건부 주문 취소 실패: {e}")
        return None

def get_conditional_order_status(symbol, order_id):
    try:
        res = session.get_conditional_orders(
            category="linear",
            symbol=symbol,
            orderId=order_id
        )
        if res['result']['list']:
            order_info = res['result']['list'][0]
            return order_info.get('orderStatus')
        else:
            return None
    except Exception as e:
        print("조건부 주문 조회 실패:", e)
        return None

def trade_worker(
    position_type, symbol, qty, entry_time, exit_time,
    take_profit=None, stop_loss=None
):
    trade_status['running'] = True
    trade_status['info'] = {
        "position_type": position_type,
        "symbol": symbol,
        "qty": qty,
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
        "entry_at": None,
        "tp_price": None,
        "sl_price": None,
        "stop_loss_msg": None
    }
    try:
        entry_dt = datetime.strptime(entry_time, "%Y-%m-%d %H:%M")
        exit_dt = datetime.strptime(exit_time, "%Y-%m-%d %H:%M")
        entry_fired = False

        while not entry_fired:
            if not trade_status["running"]:
                break
            now = datetime.now()
            if now >= entry_dt:
                side = "Buy" if position_type == "long" else "Sell"
                entry_order = open_position(symbol, side, qty)
                trade_status['info']['entry_order'] = entry_order
                trade_status['info']['entry_at'] = now.strftime("%Y-%m-%d %H:%M:%S")

                executed_price = None
                if isinstance(entry_order, dict) and 'result' in entry_order:
                    executed_price = entry_order['result'].get('avgPrice')
                    if executed_price is None:
                        executed_price = entry_order['result'].get('price')
                    if executed_price is not None:
                        executed_price = float(executed_price)
                if executed_price is None:
                    executed_price = get_price(symbol)
                trade_status['info']['entry_price'] = executed_price

                tick_size = get_tick_size(symbol, session)
                interval = "15"
                if stop_loss is None:
                    if position_type == "long":
                        lows = get_recent_lows(symbol, session, interval=interval)
                        stop_loss, stop_msg, stop_pct = get_long_stop_loss(
                            lows=lows,
                            entry_price=executed_price,
                            tick_size=tick_size,
                            tick_offset=5,
                            fallback_pct=0.01
                        )
                        loss_gap = executed_price - stop_loss
                        take_profit = round(executed_price + loss_gap * 2, 8)
                        trade_status['info']['tp_price'] = take_profit
                    else:
                        highs = get_recent_highs(symbol, session, interval=interval)
                        stop_loss, stop_msg, stop_pct = get_short_stop_loss(
                            highs=highs,
                            entry_price=executed_price,
                            tick_size=tick_size,
                            tick_offset=5,
                            fallback_pct=0.01
                        )
                        loss_gap = stop_loss - executed_price
                        take_profit = round(executed_price - loss_gap * 2, 8)
                        trade_status['info']['tp_price'] = take_profit
                    print(stop_msg)
                    trade_status['info']['stop_loss'] = stop_loss
                    trade_status['info']['stop_loss_msg'] = stop_msg
                else:
                    stop_msg = f"사용자 지정 손절값({stop_loss})이 적용됩니다."
                    trade_status['info']['stop_loss_msg'] = stop_msg
                    if take_profit is None:
                        if position_type == "long":
                            loss_gap = executed_price - stop_loss
                            take_profit = round(executed_price + loss_gap * 2, 8)
                            trade_status['info']['tp_price'] = take_profit
                        else:
                            loss_gap = stop_loss - executed_price
                            take_profit = round(executed_price - loss_gap * 2, 8)
                            trade_status['info']['tp_price'] = take_profit

                if position_type == "long":
                    tp_direction = 1
                    sl_direction = 2
                    close_side = "Sell"
                else:
                    tp_direction = 2
                    sl_direction = 1
                    close_side = "Buy"

                tp_order, sl_order = None, None
                tp_order_id, sl_order_id = None, None
                if take_profit is not None:
                    tp_order = place_trigger_order(
                        symbol, close_side, qty, take_profit, tp_direction
                    )
                    if tp_order and 'result' in tp_order:
                        tp_order_id = tp_order['result'].get('orderId')
                        trade_status['info']['tp_order_id'] = tp_order_id
                    trade_status['info']['tp_order'] = tp_order
                    trade_status['info']['tp_price'] = take_profit
                if stop_loss is not None:
                    sl_order = place_trigger_order(
                        symbol, close_side, qty, stop_loss, sl_direction
                    )
                    if sl_order and 'result' in sl_order:
                        sl_order_id = sl_order['result'].get('orderId')
                        trade_status['info']['sl_order_id'] = sl_order_id
                    trade_status['info']['sl_order'] = sl_order
                    trade_status['info']['sl_price'] = stop_loss

                entry_fired = True
                print(f"[트리거주문 등록완료] 익절: {take_profit}, 손절: {stop_loss}")
                break
            time.sleep(1)

        tp_filled = False
        sl_filled = False
        close_fired = False
        symbol = trade_status['info']['symbol']
        tp_order_id = trade_status['info'].get('tp_order_id')
        sl_order_id = trade_status['info'].get('sl_order_id')

        while trade_status['running']:
            now = datetime.now()

            if now >= exit_dt and not close_fired:
                side = "Buy" if position_type == "long" else "Sell"
                close_order = close_position(symbol, side, qty)
                trade_status['info']['exit_order'] = close_order
                trade_status['info']['exit_price'] = get_price(symbol)
                trade_status['info']['exit_at'] = now.strftime("%Y-%m-%d %H:%M:%S")
                if tp_order_id:
                    cancel_conditional_order(symbol, tp_order_id)
                    print("[알림] 남은 익절 트리거주문 자동취소됨.")
                if sl_order_id:
                    cancel_conditional_order(symbol, sl_order_id)
                    print("[알림] 남은 손절 트리거주문 자동취소됨.")
                print("[포지션 청산] 매도시간 도달하여 포지션을 종료했습니다.")
                close_fired = True
                break

            if tp_order_id and not tp_filled:
                tp_status = get_conditional_order_status(symbol, tp_order_id)
                if tp_status == "Filled":
                    print("[체결] 익절주문이 체결되었습니다.")
                    tp_filled = True
                    if sl_order_id:
                        cancel_conditional_order(symbol, sl_order_id)
                        print("[알림] 남은 손절 트리거주문 자동취소됨.")
                    break

            if sl_order_id and not sl_filled:
                sl_status = get_conditional_order_status(symbol, sl_order_id)
                if sl_status == "Filled":
                    print("[체결] 손절주문이 체결되었습니다.")
                    sl_filled = True
                    if tp_order_id:
                        cancel_conditional_order(symbol, tp_order_id)
                        print("[알림] 남은 익절 트리거주문 자동취소됨.")
                    break

            time.sleep(2)

    except Exception as e:
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

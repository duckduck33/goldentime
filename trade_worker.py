from dotenv import load_dotenv
load_dotenv()

import os
import time
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
        logging.StreamHandler()  # 터미널에도 동시에 찍고 싶으면 포함
    ]
)


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

def get_tick_size(symbol, session):
    try:
        res = session.get_instruments_info(category="linear", symbol=symbol)
        tick_size = float(res['result']['list'][0]['priceFilter']['tickSize'])
        return tick_size
    except Exception as e:
        logging.error(f"틱사이즈 조회 실패: {e}")
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
        logging.error(f"OHLCV(캔들) 조회 실패: {e}")
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
        logging.error(f"OHLCV(캔들) 조회 실패: {e}")
        return []

def round_qty(qty):
    """익절 수량을 소수점 4자리로 반올림 (거래소 정책에 맞춤)"""
    return round(qty, 4)

def get_position_size(symbol):
    """
    현재 심볼의 포지션 보유 수량 조회 (없으면 0)
    """
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
    """
    익절(수익실현) 주문을 지정가(리밋)로 절반 수량만 예약
    """
    close_side = "Sell" if side == "Buy" else "Buy"
    tp_qty = round(qty / 2, 4)
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
        return tp_order
    except Exception as e:
        logging.error(f"익절 지정가 주문 에러: {e}")
        return None

def place_stop_loss(symbol, side, sl_price):
    """
    손절(Stop Loss) 예약(set_trading_stop) - sl_price를 직접 사용
    """
    try:
        sl_result = session.set_trading_stop(
            category="linear",
            symbol=symbol,
            stopLoss=str(sl_price),
            slTriggerBy="LastPrice"
        )
        logging.info(f"[손절 예약] 손절가: {sl_price}, 결과: {sl_result}")
        return sl_result
    except Exception as e:
        logging.error(f"손절 예약 에러: {e}")
        return None

def trade_worker(
    position_type, symbol, qty, entry_time, exit_time,
    take_profit=None, stop_loss=None,
    immediate=False
):
    """
    immediate=True: 진입 시간 조건 무시하고 바로 진입
    immediate=False: 기존처럼 entry_time, exit_time 사용
    """
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
                entry_order = open_position(symbol, side, qty)
                trade_status['info']['entry_order'] = entry_order
                trade_status['info']['entry_at'] = now.strftime("%Y-%m-%d %H:%M:%S")

                # 진입 체결가 조회 (없으면 현재가로 대체)
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
                logging.info(f"{symbol} {position_type}포지션 진입가: {executed_price} 입니다")

                # 손절가 분기 (자동/수동 + 안내 메시지)
                tp_ratio = 0.02   # 익절 비율 (예시: 2%)
                if stop_loss is not None and stop_loss != "":
                    sl_price = float(stop_loss)
                    stop_msg = f"사용자 지정 손절값({sl_price})이 적용됩니다."
                    tp_price = float(take_profit) if take_profit not in [None, ""] else (
                        round(executed_price * (1 + tp_ratio), 8) if position_type == "long" else round(executed_price * (1 - tp_ratio), 8)
                    )
                else:
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
                        # 로그: 손절 시나리오 전체 안내문(1차,2차 지지선+손절+익절)
                        logging.info(f"[손절/익절 시나리오]\n{scenario_msg}")
                        # 익절가도 안내문에서 사용(자동)
                        tp_price = round(executed_price * (1 + tp_ratio), 8)
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
                        tp_price = round(executed_price * (1 - tp_ratio), 8)

                # 익절가(수동 지정시)
                if take_profit is not None and take_profit != "":
                    tp_price = float(take_profit)

                logging.info(f"[익절/손절 결정] 익절가: {tp_price}, 손절가: {sl_price}")

                # 주문 실행
                tp_result = place_tp_limit_order(symbol, side, qty, tp_price)
                sl_result = place_stop_loss(symbol, side, sl_price)
                trade_status['info']['tp_order'] = tp_result
                trade_status['info']['sl_order'] = sl_result
                trade_status['info']['tp_price'] = tp_price
                trade_status['info']['sl_price'] = sl_price

                entry_fired = True
                logging.info(f"[골든타임봇이 포지션진입, 손절주문, 익절주문 완료했습니다.매매종료까지 감시모드입니다.")
                break
            time.sleep(1)

        close_fired = False
        position_closed = False

        while trade_status['running']:
            now = datetime.now()

            # 청산시간 도달시 시장가로 강제청산 (전량)
            if now >= exit_dt and not close_fired:
                side = "Buy" if position_type == "long" else "Sell"
                close_order = close_position(symbol, side, qty)
                trade_status['info']['exit_order'] = close_order
                trade_status['info']['exit_price'] = get_price(symbol)
                trade_status['info']['exit_at'] = now.strftime("%Y-%m-%d %H:%M:%S")
                logging.info("[포지션 청산] 매도시간 도달하여 포지션을 종료했습니다.")
                close_fired = True
                break

            # 실시간 포지션 감시 - 포지션이 0이면 종료(익절·손절 등)
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

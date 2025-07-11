from dotenv import load_dotenv
load_dotenv()

import os
import time
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

# 1. 환경변수에서 API키 불러오기 (.env 사용)
BYBIT_API_KEY = os.environ.get('BYBIT_API_KEY')
BYBIT_API_SECRET = os.environ.get('BYBIT_API_SECRET')
BYBIT_API_URL = "https://api-testnet.bybit.com"

# 2. pybit 세션 연결 (테스트넷)
session = HTTP(
    testnet=True,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# 3. Flask 앱 및 매매 상태 관리
app = Flask(__name__)
trade_status = {
    "running": False,
    "info": {},
    "error": None
}

@app.route('/')
def home():
    return "골든타임 자동매매 서버가 정상 실행 중입니다."


# 4. 잔고조회
def get_balance(coin="USDT"):
    try:
        res = session.get_wallet_balance(accountType="UNIFIED", coin=coin)
        return res['result']['list'][0]['totalEquity']
    except Exception as e:
        return f"잔고조회 에러: {e}"

# 5. 현재가조회
def get_price(symbol):
    try:
        ticker = session.get_tickers(category="linear", symbol=symbol)
        return float(ticker['result']['list'][0]['lastPrice'])
    except Exception as e:
        return None

# 6. 시장가 진입
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

# 7. 시장가 청산
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

# 8. while True로 예약매매 + 조건 체크 (업계 실전 패턴)
def trade_worker(
    position_type, symbol, qty, entry_time, exit_time,
    entry_price_cond=None, take_profit=None, stop_loss=None
):
    """
    - position_type: 'long' 또는 'short'
    - symbol: 예) 'BTCUSDT'
    - qty: 주문수량
    - entry_time: 예약진입시간 (str, "YYYY-MM-DD HH:MM")
    - exit_time: 예약종료시간 (str, "YYYY-MM-DD HH:MM")
    - entry_price_cond: 예약 진입가격(조건), None이면 시간만 대기
    - take_profit: 익절가격, None이면 미적용
    - stop_loss: 손절가격, None이면 미적용
    """

    trade_status['running'] = True
    trade_status['info'] = {
        "position_type": position_type,
        "symbol": symbol,
        "qty": qty,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry_price_cond": entry_price_cond,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "entry_price": None,
        "exit_price": None,
        "entry_order": None,
        "exit_order": None,
        "entry_at": None,
        "exit_at": None
    }

    try:
        # 1. 진입 전까지 while True로 실시간 대기/체크
        entry_dt = datetime.strptime(entry_time, "%Y-%m-%d %H:%M")
        entry_fired = False

        while not entry_fired:
            now = datetime.now()
            cur_price = get_price(symbol)

            # 1) 진입 예약시간 도달 시 진입
            if now >= entry_dt:
                if entry_price_cond is None or (cur_price is not None and (
                    (position_type == "long" and cur_price <= entry_price_cond) or
                    (position_type == "short" and cur_price >= entry_price_cond)
                )):
                    # 진입조건(시간+가격) 만족하면 진입
                    side = "Buy" if position_type == "long" else "Sell"
                    entry_order = open_position(symbol, side, qty)
                    trade_status['info']['entry_order'] = entry_order
                    trade_status['info']['entry_price'] = cur_price
                    trade_status['info']['entry_at'] = now.strftime("%Y-%m-%d %H:%M:%S")
                    entry_fired = True
                    break

            # 2) 진입 예약시간 전, 가격조건이 있다면 조건 달성시 바로 진입
            if entry_price_cond is not None and cur_price is not None:
                if (position_type == "long" and cur_price <= entry_price_cond) or \
                   (position_type == "short" and cur_price >= entry_price_cond):
                    side = "Buy" if position_type == "long" else "Sell"
                    entry_order = open_position(symbol, side, qty)
                    trade_status['info']['entry_order'] = entry_order
                    trade_status['info']['entry_price'] = cur_price
                    trade_status['info']['entry_at'] = now.strftime("%Y-%m-%d %H:%M:%S")
                    entry_fired = True
                    break

            # 3) 1초마다 반복 체크
            time.sleep(1)

        # 2. 진입 이후, 익절/손절/종료시간까지 실시간 감시
        exit_dt = datetime.strptime(exit_time, "%Y-%m-%d %H:%M")
        side = "Buy" if position_type == "long" else "Sell"
        exit_fired = False

        while not exit_fired:
            now = datetime.now()
            cur_price = get_price(symbol)

            # 익절(수익실현) 조건 도달
            if take_profit is not None and cur_price is not None:
                if (position_type == "long" and cur_price >= take_profit) or \
                   (position_type == "short" and cur_price <= take_profit):
                    exit_order = close_position(symbol, side, qty)
                    trade_status['info']['exit_order'] = exit_order
                    trade_status['info']['exit_price'] = cur_price
                    trade_status['info']['exit_at'] = now.strftime("%Y-%m-%d %H:%M:%S")
                    exit_fired = True
                    break

            # 손절(손실컷) 조건 도달
            if stop_loss is not None and cur_price is not None:
                if (position_type == "long" and cur_price <= stop_loss) or \
                   (position_type == "short" and cur_price >= stop_loss):
                    exit_order = close_position(symbol, side, qty)
                    trade_status['info']['exit_order'] = exit_order
                    trade_status['info']['exit_price'] = cur_price
                    trade_status['info']['exit_at'] = now.strftime("%Y-%m-%d %H:%M:%S")
                    exit_fired = True
                    break

            # 종료시간 도달시 자동 청산
            if now >= exit_dt:
                exit_order = close_position(symbol, side, qty)
                trade_status['info']['exit_order'] = exit_order
                trade_status['info']['exit_price'] = cur_price
                trade_status['info']['exit_at'] = now.strftime("%Y-%m-%d %H:%M:%S")
                exit_fired = True
                break

            time.sleep(1)

    except Exception as e:
        trade_status['error'] = str(e)
    finally:
        trade_status['running'] = False

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

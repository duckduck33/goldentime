from dotenv import load_dotenv
load_dotenv()

import os
import time
from datetime import datetime
from pybit.unified_trading import HTTP
import threading

# 환경변수 읽기
BYBIT_API_KEY = os.environ.get('BYBIT_API_KEY')
BYBIT_API_SECRET = os.environ.get('BYBIT_API_SECRET')

# 바이비트 테스트넷 세션
session = HTTP(
    testnet=True,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# 매매 상태 전역 변수 (단일 스레드 기준)
trade_status = {
    "running": False,
    "info": {},
    "error": None
}

# 함수 정의들 (잔고조회, 현재가, 주문, 청산)

def get_balance(coin="USDT"):
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

def trade_worker(
    position_type, symbol, qty, entry_time, exit_time,
    entry_price_cond=None, take_profit=None, stop_loss=None
):
    # trade_status 초기화, 예약 매매 로직 (while 루프, 조건 체크 등)
    # 코드 생략 (이전에 작성한 것과 동일)
    pass

def start_trade_thread(**kwargs):
    """
    trade_worker를 새 스레드에서 실행
    """
    if trade_status["running"]:
        return False, "이미 매매 중입니다."
    th = threading.Thread(target=trade_worker, kwargs=kwargs)
    th.daemon = True
    th.start()
    return True, "매매 시작됨"

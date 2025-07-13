import streamlit as st
import requests
from datetime import datetime

st.title("자동매매 대시보드")

# 1. 티커명 드롭다운
symbol = st.selectbox("거래 코인(심볼)", ["BTCUSDT", "ETHUSDT", "XRPUSDT", "DOGEUSDT", "SOLUSDT"])

# 2. 포지션 유형
position_type = st.radio("포지션", ["long", "short"])

# 3. 수량 입력
qty = st.number_input("수량", min_value=0.0001, value=0.001, step=0.0001, format="%.4f")

# 4. 시간 선택 드롭다운 (1~24시)
today = datetime.now().strftime("%Y-%m-%d")
entry_hour = st.selectbox("진입(시작) 시간(시)", list(range(1, 25)))
exit_hour = st.selectbox("종료(청산) 시간(시)", list(range(1, 25)))
entry_time = f"{today} {entry_hour:02d}:00"
exit_time = f"{today} {exit_hour:02d}:00"

# 5. 손절/익절 입력 (None 입력시 자동계산)
stop_loss = st.text_input("손절값(미입력시 자동계산)", "")
take_profit = st.text_input("익절값(미입력시 자동계산)", "")

st.write("잔고 확인:", requests.get("http://localhost:8000/get_balance").json())

if st.button("매매 시작"):
    req_data = {
        "position_type": position_type,
        "symbol": symbol,
        "qty": qty,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "take_profit": float(take_profit) if take_profit else None,
        "stop_loss": float(stop_loss) if stop_loss else None
    }
    res = requests.post("http://localhost:8000/start_trade", json=req_data).json()
    st.write(res)

if st.button("매매 상태 확인"):
    st.write(requests.get("http://localhost:8000/trade_status").json())

if st.button("매매 강제 중단"):
    st.write(requests.post("http://localhost:8000/stop_trade").json())

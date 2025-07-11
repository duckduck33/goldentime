# streamlit_front.py
import streamlit as st
import requests
from datetime import datetime, timedelta

# --- 서버 주소(본인 환경 맞게 수정, 로컬 서버면 아래처럼) ---
API_BASE = "http://localhost:8000"

# --- 1. 매매 주문 입력 폼 ---
st.title("골든타임 자동매매 (테스트넷)")

with st.form("trade_form"):
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("심볼 (예: BTCUSDT)", "BTCUSDT")
        qty = st.number_input("주문 수량", value=0.01)
        position_type = st.selectbox("포지션", ["long", "short"])
    with col2:
        entry_time = st.text_input("진입예약시간 (YYYY-MM-DD HH:MM)", 
            (datetime.now() + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M"))
        exit_time = st.text_input("청산예약시간 (YYYY-MM-DD HH:MM)", 
            (datetime.now() + timedelta(minutes=6)).strftime("%Y-%m-%d %H:%M"))
    entry_price_cond = st.text_input("진입조건가격 (미입력시 예약시간만 대기)", "")
    take_profit = st.text_input("익절가격 (미입력시 미적용)", "")
    stop_loss = st.text_input("손절가격 (미입력시 미적용)", "")
    submitted = st.form_submit_button("매매시작 (주문)")

# --- 2. 매매 주문 제출 ---
if submitted:
    payload = {
        "position_type": position_type,
        "symbol": symbol,
        "qty": qty,
        "entry_time": entry_time,
        "exit_time": exit_time,
    }
    if entry_price_cond: payload["entry_price_cond"] = float(entry_price_cond)
    if take_profit: payload["take_profit"] = float(take_profit)
    if stop_loss: payload["stop_loss"] = float(stop_loss)

    try:
        res = requests.post(f"{API_BASE}/start_trade", json=payload, timeout=5)
        st.success(f"응답: {res.json()}")
    except Exception as e:
        st.error(f"매매요청 실패: {e}")

st.divider()

# --- 3. 잔고/상태/현재가 조회 섹션 ---
st.subheader("실시간 상태/잔고/현재가 조회")

col1, col2, col3 = st.columns(3)

with col1:
    coin = st.text_input("잔고 조회 코인", "USDT", key="bal_coin")
    if st.button("잔고조회"):
        try:
            r = requests.get(f"{API_BASE}/balance", params={"coin": coin}, timeout=5)
            st.write(f"잔고: {r.json()['balance']}")
        except Exception as e:
            st.error(f"잔고조회 실패: {e}")

with col2:
    if st.button("매매상태 조회"):
        try:
            r = requests.get(f"{API_BASE}/trade_status", timeout=5)
            st.json(r.json())
        except Exception as e:
            st.error(f"상태조회 실패: {e}")

with col3:
    symbol_price = st.text_input("심볼(현재가)", "BTCUSDT", key="prc_sym")
    if st.button("현재가 조회"):
        try:
            r = requests.get(f"{API_BASE}/price", params={"symbol": symbol_price}, timeout=5)
            st.write(f"현재가: {r.json()['price']}")
        except Exception as e:
            st.error(f"현재가조회 실패: {e}")

st.divider()

# --- 4. 매매 중지(강제 종료) ---
if st.button("매매 중지 (강제 중단)"):
    try:
        r = requests.post(f"{API_BASE}/stop_trade", timeout=5)
        st.success(f"응답: {r.json()}")
    except Exception as e:
        st.error(f"매매중지 실패: {e}")


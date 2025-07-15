import streamlit as st
import requests
from datetime import datetime
import uuid

# ================================
# 1. API 서버 주소
# ================================
API_BASE_URL = "https://goldentime-production.up.railway.app"

# ================================
# 2. user_id(고유식별자) 생성 및 세션에 저장
# ================================
if "user_id" not in st.session_state:
    # 최초 접속 시 UUID 생성, 세션에 저장
    st.session_state["user_id"] = str(uuid.uuid4())
user_id = st.session_state["user_id"]

# ================================
# 3. BYBIT API 키/시크릿 입력 UI
# ================================
with st.sidebar:
    st.subheader("Bybit API 키 입력")
    api_key = st.text_input("BYBIT API KEY", value=st.session_state.get("api_key", ""), key="api_key")
    api_secret = st.text_input("BYBIT API SECRET", value=st.session_state.get("api_secret", ""), key="api_secret", type="password")
    if not api_key or not api_secret:
        st.warning("API 키와 시크릿을 모두 입력해야 매매 기능 사용 가능!")

# ================================
# 4. 탭 메뉴 정의
# ================================
tab_list = [
    "골든타임매매봇",
    "거래소공지사항매매봇",
    "김프매매봇",
    "펀딩비매매봇",
    "호가창매매봇"
]
tabs = st.tabs(tab_list)

# ================================
# 5. 골든타임 자동매매봇 탭 (메인)
# ================================
with tabs[0]:
    st.subheader("골든타임 자동매매봇")
    st.info("※ BYBIT API KEY/SECRET 미입력시 매매 기능을 쓸 수 없습니다.")

    symbol = st.text_input("거래 코인(심볼)", value="BTCUSDT")
    position_type = st.radio("포지션", ["long", "short"], horizontal=True)
    fixed_loss = st.number_input("고정 손실액(USDT)", min_value=0.01, value=2.0, step=0.01, format="%.2f")

    today = datetime.now().strftime("%Y-%m-%d")
    entry_time_raw = st.text_input("진입(시작) 시간", value=f"{today} 09:00")
    exit_time_raw = st.text_input("종료(청산) 시간", value=f"{today} 23:00")
    stop_loss = st.text_input("손절값(미입력시 자동계산)", "")
    take_profit = st.text_input("익절값(미입력시 자동계산)", "")
    immediate = st.checkbox("즉시 매매 (체크시 입력된 시간과 무관하게 즉시 진입)")

    # ----- 매매 시작 버튼 -----
    if st.button("매매 시작"):
        if not api_key or not api_secret:
            st.error("API 키와 시크릿을 모두 입력하세요.")
        else:
            req_data = {
                "user_id": user_id,             # ← user_id 항상 포함
                "position_type": position_type,
                "symbol": symbol,
                "fixed_loss": fixed_loss,
                "entry_time": entry_time_raw,
                "exit_time": exit_time_raw,
                "take_profit": float(take_profit) if take_profit else None,
                "stop_loss": float(stop_loss) if stop_loss else None,
                "immediate": immediate,
                "api_key": api_key,
                "api_secret": api_secret
            }
            try:
                res = requests.post(f"{API_BASE_URL}/start_trade", json=req_data)
                if res.ok and res.json().get("success"):
                    st.success("골든타임매매봇 동작 시작!")
                else:
                    st.error(f"매매 시작 실패: {res.json().get('msg')}")
            except Exception as e:
                st.error(f"서버 연결 오류!\n{e}")

    # ----- 매매 상태 확인 버튼 -----
    if st.button("매매 상태 확인"):
        if not api_key or not api_secret:
            st.error("API 키와 시크릿을 모두 입력하세요.")
        else:
            try:
                params = {
                    "user_id": user_id,         # ← user_id 항상 포함
                    "api_key": api_key,
                    "api_secret": api_secret
                }
                res = requests.get(f"{API_BASE_URL}/trade_status", params=params).json()
                running = res.get("running")
                st.info("매매 진행중" if running else "대기중")
            except Exception as e:
                st.error(f"서버 연결 오류!\n{e}")

    # ----- 매매 강제 중단 버튼 -----
    if st.button("매매 강제 중단"):
        if not api_key or not api_secret:
            st.error("API 키와 시크릿을 모두 입력하세요.")
        else:
            try:
                req_data = {
                    "user_id": user_id,         # ← user_id 항상 포함
                    "api_key": api_key,
                    "api_secret": api_secret
                }
                _ = requests.post(f"{API_BASE_URL}/stop_trade", json=req_data)
                st.warning("골든타임매매봇이 중단됩니다")
            except Exception as e:
                st.error(f"서버 연결 오류!\n{e}")

    # ----- 잔고 확인 -----
    if st.checkbox("잔고 확인"):
        if not api_key or not api_secret:
            st.error("API 키와 시크릿을 모두 입력하세요.")
        else:
            try:
                params = {
                    "user_id": user_id,         # ← user_id 항상 포함
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "coin": "USDT"
                }
                res = requests.get(f"{API_BASE_URL}/get_balance", params=params).json()
                st.write(f"코인: {res.get('coin')} / 잔고: {res.get('balance')}")
            except Exception as e:
                st.error(f"서버 연결 오류!\n{e}")

# ================================
# 6. 나머지 탭(준비중/안내)
# ================================
with tabs[1]:
    st.subheader("거래소 공지사항 자동매매봇")
    st.info("※ 신규상장/입출금 재개 등 공지사항 실시간 감지 후 즉시 매매 자동화. (준비중)")
    st.write("거래소 공지사항 감시 기능은 준비 중입니다.")

with tabs[2]:
    st.subheader("김프 자동매매봇")
    st.info("※ 업비트-해외 가격차이 자동감지/매매. (준비중)")
    st.write("김프 자동매매 기능은 준비 중입니다.")

with tabs[3]:
    st.subheader("펀딩비 자동매매봇")
    st.info("※ 펀딩비+스왑시장 실시간 분석/자동매매. (준비중)")
    st.write("펀딩비 자동매매 기능은 준비 중입니다.")

with tabs[4]:
    st.subheader("호가창 분석 자동매매봇")
    st.info("※ 실시간 호가잔량, 체결강도 기반 AI 자동매매. (준비중)")
    st.write("호가창 분석 자동매매 기능은 준비 중입니다.")

# --- END ---

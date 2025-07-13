import streamlit as st
import requests
from datetime import datetime

# --------- 상단 로고 + 앱 설명 --------- #
col1, col2 = st.columns([1, 8])
with col1:
    st.image("logo.png", width=56)    # logo.png 파일을 같은 폴더에 넣으세요 (AI 심볼 추천)
with col2:
    st.markdown("<h2 style='color:#FFD600;margin-bottom:0;'>골든타임 매매 플랫폼</h2>", unsafe_allow_html=True)
    st.caption("AI 자동매매, 다양한 퀀트 전략을 한곳에서 - 초보도 쉽게, 전문가도 강력하게")

st.write("---")

# --------- 상단 탭 메뉴 --------- #
tab_list = [
    "골든타임매매봇",
    "거래소공지사항매매봇",
    "김프매매봇",
    "펀딩비매매봇",
    "호가창매매봇"
]
tabs = st.tabs(tab_list)

# --------- 골든타임매매봇 (메인 탭) --------- #
with tabs[0]:
    st.subheader("골든타임 자동매매봇")
    st.info("※ 변동성 돌파, 타임메타 등 다양한 전략을 테스트넷 환경에서 실전처럼 체험하세요.")

    # 기본 입력 폼
    # symbol = st.selectbox("거래 코인(심볼)", ["BTCUSDT", "ETHUSDT", "XRPUSDT", "DOGEUSDT", "SOLUSDT"])
    
    symbol = st.text_input("거래 코인(심볼)", value="AXSUSDT")
    position_type = st.radio("포지션", ["long", "short"], horizontal=True)
    qty = st.number_input("수량", min_value=0.0001, value=100.0, step=0.0001, format="%.4f")
    today = datetime.now().strftime("%Y-%m-%d")
    entry_time_raw = st.text_input("진입(시작) 시간", value=f"{today} 09:00")
    exit_time_raw = st.text_input("종료(청산) 시간", value=f"{today} 23:00")
    stop_loss = st.text_input("손절값(미입력시 자동계산)", "")
    take_profit = st.text_input("익절값(미입력시 자동계산)", "")
    # ★ 즉시매매 체크박스 추가
    immediate = st.checkbox("즉시 매매 (체크시 입력된 시간과 무관하게 즉시 진입)")

    # 실행 버튼들
    if st.button("매매 시작"):
        req_data = {
            "position_type": position_type,
            "symbol": symbol,
            "qty": qty,
            "entry_time": entry_time_raw,
            "exit_time": exit_time_raw,
            "take_profit": float(take_profit) if take_profit else None,
            "stop_loss": float(stop_loss) if stop_loss else None,
            "immediate": immediate    # ★ 즉시매매 옵션 추가!
        }
        try:
            _ = requests.post("http://localhost:8000/start_trade", json=req_data)
            st.success("골든타임매매봇 동작합니다")
        except Exception:
            st.error("서버 연결 오류!")

    if st.button("매매 상태 확인"):
        try:
            res = requests.get("http://localhost:8000/trade_status").json()
            running = res.get("running")
            st.info("매매 진행중" if running else "대기중")
        except Exception:
            st.error("서버 연결 오류!")

    if st.button("매매 강제 중단"):
        try:
            _ = requests.post("http://localhost:8000/stop_trade")
            st.warning("골든타임매매봇이 중단됩니다")
        except Exception:
            st.error("서버 연결 오류!")

    # 잔고확인(체크박스)
    if st.checkbox("잔고 확인"):
        try:
            res = requests.get("http://localhost:8000/get_balance").json()
            st.write(f"코인: {res.get('coin')} / 잔고: {res.get('balance')}")
        except Exception:
            st.error("서버 연결 오류!")

# --------- 거래소공지사항매매봇 --------- #
with tabs[1]:
    st.subheader("거래소 공지사항 자동매매봇")
    st.info("※ 신규상장/입출금 재개 등 공지사항 실시간 감지 후 즉시 매매 자동화.\n빠른 속도, 자동알림, 조건부 자동거래까지 지원 (준비중)")

# --------- 김프매매봇 --------- #
with tabs[2]:
    st.subheader("김프 자동매매봇")
    st.info("※ 업비트-해외 가격차이(김치프리미엄) 자동감지/매매. 실전 연동 및 테스트넷 지원 (준비중)")

# --------- 펀딩비매매봇 --------- #
with tabs[3]:
    st.subheader("펀딩비 자동매매봇")
    st.info("※ 펀딩비+스왑시장 정보 실시간 분석/자동매매. 주요 거래소 지원 (준비중)")

# --------- 호가창매매봇 --------- #
with tabs[4]:
    st.subheader("호가창 분석 자동매매봇")
    st.info("※ 실시간 호가잔량, 체결강도 기반 AI 자동매매. 고빈도/마이크로트렌드 전략 탑재 (준비중)")

# --------- 하단 스타일/컬러/버튼 등은 streamlit 테마/설정에 맞게 자동 적용됩니다 --------- #

# (필요시 더 세련된 CSS/아이콘/배경 등 추가 가능)

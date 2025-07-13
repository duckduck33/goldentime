import streamlit as st
import time
import os
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="골든타임 매매 로그", layout="wide")
st.title("골든타임 매매 로그 (터미널 스타일)")

# 2초마다 자동 새로고침 (2000ms)
st_autorefresh(interval=2000, key="logrefresh")

log_box = st.empty()
LOG_PATH = "log.txt"

def read_latest_logs(log_path, n=50):
    if not os.path.exists(log_path):
        return ["아직 로그가 없습니다. 매매가 시작되면 이곳에 자동으로 기록됩니다."]
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return lines[-n:] if lines else ["아직 로그가 없습니다."]

# 새로고침마다 최근 로그 읽어와 표시
logs = read_latest_logs(LOG_PATH, n=50)
log_box.code("".join(logs), language="")

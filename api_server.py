from flask import Flask, request, jsonify
from datetime import datetime
import pytz
import threading
import time

app = Flask(__name__)

trade_status = {"running": False, "info": {}, "error": None}

# ────────
# 서버 실행시 현재 시간 체크 (UTC, KST 모두)
# ────────
kst = pytz.timezone('Asia/Seoul')
now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
now_kst = datetime.now(kst)
print("=== [서버 시작:07150403 배포체크용] ===")
print("서버 현재 UTC 시간:", now_utc)
print("서버 현재 KST 시간:", now_kst)
print("==================")

def trade_worker(entry_time_kst, symbol, position_type, immediate):
    kst = pytz.timezone('Asia/Seoul')

    # 1. entry_time_kst(한국시간 문자열)를 KST datetime으로 파싱
    try:
        dt_kst = kst.localize(datetime.strptime(entry_time_kst, "%Y-%m-%d %H:%M"))
    except Exception as e:
        print("[ERROR] entry_time 파싱 실패:", entry_time_kst, e)
        trade_status["error"] = f"entry_time 파싱 실패: {e}"
        trade_status["running"] = False
        return

    # 2. KST datetime → UTC로 변환
    entry_dt = dt_kst.astimezone(pytz.utc)

    print("\n[LOG] 매매 예약 시작")
    print("[LOG] entry_time 파라미터(KST):", entry_time_kst)
    print("[LOG] 파싱된 KST datetime:", dt_kst)
    print("[LOG] 변환된 entry_dt (UTC):", entry_dt)
    print("[LOG] immediate 값:", immediate)
    print("===============================")

    trade_status["running"] = True
    trade_status["info"] = {
        "symbol": symbol,
        "position_type": position_type,
        "entry_time_kst": entry_time_kst,
        "entry_time_utc": entry_dt.strftime("%Y-%m-%d %H:%M"),
        "entry_at": None,
        "immediate": immediate
    }

    entry_fired = False
    while not entry_fired:
        if not trade_status["running"]:
            print("[LOG] 매매 중단 신호 감지! 스레드 종료")
            break

        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        print("[LOG] 현재 서버 시간(now, UTC):", now)
        print("[LOG] 예약 진입 시간(entry_dt, UTC):", entry_dt)

        if immediate or now >= entry_dt:
            print("[LOG] 진입 조건 만족! 매매 진입 (now >= entry_dt or immediate=True)")
            trade_status["info"]["entry_at"] = now.strftime("%Y-%m-%d %H:%M")
            entry_fired = True
            break
        else:
            print("[LOG] 아직 진입 시간 아님! 대기 중 (now < entry_dt)")

        time.sleep(5)

    trade_status["running"] = False
    print("[LOG] 매매 스레드 종료\n")

def start_trade_thread(**kwargs):
    if trade_status["running"]:
        return False, "이미 매매 중입니다."
    th = threading.Thread(target=trade_worker, kwargs=kwargs)
    th.daemon = True
    th.start()
    return True, "매매 시작됨"

@app.route("/start_trade", methods=["POST"])
def start_trade():
    data = request.json
    symbol = data.get("symbol", "BTCUSDT")
    position_type = data.get("position_type", "long")
    entry_time_kst = data.get("entry_time_kst")  # 예: "2024-08-14 09:00"
    immediate = data.get("immediate", False)

    if not entry_time_kst:
        return jsonify({"success": False, "msg": "entry_time_kst를 입력하세요."})

    ok, msg = start_trade_thread(
        entry_time_kst=entry_time_kst,
        symbol=symbol,
        position_type=position_type,
        immediate=immediate
    )
    return jsonify({"success": ok, "msg": msg, "info": trade_status["info"]})

@app.route("/trade_status")
def get_trade_status():
    return jsonify({
        "running": trade_status["running"],
        "info": trade_status["info"],
        "error": trade_status["error"]
    })

@app.route("/stop_trade", methods=["POST"])
def stop_trade():
    trade_status["running"] = False
    return jsonify({"success": True, "msg": "매매 중단 요청됨."})

@app.route("/server_time")
def server_time():
    kst = pytz.timezone('Asia/Seoul')
    now_utc = datetime.utcnow()
    now_kst = datetime.now(kst)
    return {
        "utc_now": now_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "kst_now": now_kst.strftime("%Y-%m-%d %H:%M:%S")
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

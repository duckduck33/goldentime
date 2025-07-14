from flask import Flask, request, jsonify
from datetime import datetime as dt
import pytz
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logging.info("[VERSION] api_server.py 2025-07-15 05:15 %s", dt.utcnow())

app = Flask(__name__)

# ... trade_status 등 기타 전역 변수 ...

@app.route("/start_trade", methods=["POST"])
def start_trade():
    data = request.json
    symbol = data.get("symbol", "BTCUSDT")
    position_type = data.get("position_type", "long")
    entry_time_kst = data.get("entry_time_kst")  # 예: "2024-08-14 09:00"
    immediate = data.get("immediate", False)

    logging.info("[LOG] /start_trade 호출됨. entry_time_kst: %s, immediate: %s", entry_time_kst, immediate)

    if not entry_time_kst:
        logging.info("[LOG] entry_time_kst 누락!")
        return jsonify({"success": False, "msg": "entry_time_kst를 입력하세요."})

    ok, msg = start_trade_thread(
        entry_time_kst=entry_time_kst,
        symbol=symbol,
        position_type=position_type,
        immediate=immediate
    )
    logging.info("[LOG] 매매 쓰레드 시작 결과: %s, info: %s", msg, trade_status["info"])
    return jsonify({"success": ok, "msg": msg, "info": trade_status["info"]})

@app.route("/trade_status")
def get_trade_status():
    logging.info("[LOG] /trade_status 호출됨")
    return jsonify({
        "running": trade_status["running"],
        "info": trade_status["info"],
        "error": trade_status["error"]
    })

@app.route("/stop_trade", methods=["POST"])
def stop_trade():
    logging.info("[LOG] /stop_trade 호출됨")
    trade_status["running"] = False
    return jsonify({"success": True, "msg": "매매 중단 요청됨."})

@app.route("/server_time")
def server_time():
    kst = pytz.timezone('Asia/Seoul')
    now_utc = dt.utcnow()
    now_kst = dt.now(kst)
    logging.info("[LOG] /server_time 호출됨 (UTC: %s, KST: %s)", now_utc, now_kst)
    return {
        "utc_now": now_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "kst_now": now_kst.strftime("%Y-%m-%d %H:%M:%S")
    }

if __name__ == "__main__":
    logging.info("[LOG] api_server 실행 시작 (main)")
    app.run(host="0.0.0.0", port=8000)

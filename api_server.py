from flask import Flask, request, jsonify
import trade_worker
import logging

app = Flask(__name__)

# ==============================
# 1. 사용자별 매매 상태 딕셔너리
# ==============================
trade_statuses = {}

# ==============================
# 2. 매매 시작 API (POST)
# ==============================
@app.route("/start_trade", methods=["POST"])
def start_trade():
    data = request.json

    user_id = data.get("user_id")
    api_key = data.get("api_key")
    api_secret = data.get("api_secret")
    if not user_id or not api_key or not api_secret:
        return jsonify({"success": False, "msg": "user_id, API 키/시크릿 입력 필요"})

    position_type = data.get("position_type")
    symbol = data.get("symbol")
    fixed_loss = data.get("fixed_loss")
    entry_time = data.get("entry_time")
    exit_time = data.get("exit_time")
    take_profit = data.get("take_profit")
    stop_loss = data.get("stop_loss")
    immediate = data.get("immediate", False)

    # 이미 해당 user_id로 매매 중이면 거부
    if trade_statuses.get(user_id, {}).get("running"):
        return jsonify({"success": False, "msg": "이미 매매 중입니다.", "info": trade_statuses[user_id]["info"]})

    # 쓰레드 시작시 user_id, trade_statuses 전체 딕셔너리 전달
    ok, msg = trade_worker.start_trade_thread(
        user_id=user_id,
        trade_statuses=trade_statuses,
        api_key=api_key,
        api_secret=api_secret,
        position_type=position_type,
        symbol=symbol,
        fixed_loss=fixed_loss,
        entry_time=entry_time,
        exit_time=exit_time,
        take_profit=take_profit,
        stop_loss=stop_loss,
        immediate=immediate
    )
    return jsonify({"success": ok, "msg": msg, "info": trade_statuses.get(user_id, {}).get("info", {})})

# ==============================
# 3. 매매 상태 확인 API (GET)
# ==============================
@app.route("/trade_status")
def get_trade_status():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"success": False, "msg": "user_id 필요"})

    user_status = trade_statuses.get(user_id, {})
    return jsonify({
        "running": user_status.get("running"),
        "info": user_status.get("info"),
        "error": user_status.get("error")
    })

# ==============================
# 4. 잔고 조회 API (GET)
# ==============================
@app.route("/get_balance")
def get_balance():
    user_id = request.args.get("user_id")
    api_key = request.args.get("api_key")
    api_secret = request.args.get("api_secret")
    coin = request.args.get("coin", "USDT")
    if not user_id or not api_key or not api_secret:
        return jsonify({"success": False, "msg": "user_id, API 키/시크릿 입력 필요"})
    balance = trade_worker.get_balance(api_key, api_secret, coin)
    return jsonify({"coin": coin, "balance": balance})

# ==============================
# 5. 매매 강제 중단 API (POST)
# ==============================
@app.route("/stop_trade", methods=["POST"])
def stop_trade():
    data = request.json or {}
    user_id = data.get("user_id")
    api_key = data.get("api_key")
    api_secret = data.get("api_secret")
    logging.info(f"[LOG] /stop_trade 호출됨 (user_id={user_id})")

    # 해당 유저의 상태만 변경
    if user_id in trade_statuses:
        trade_statuses[user_id]["running"] = False

        # try:
        #     symbol = trade_statuses[user_id]["info"].get("symbol")
        #     position_type = trade_statuses[user_id]["info"].get("position_type")
        #     if symbol and position_type and api_key and api_secret:
        #         trade_worker.force_exit_position(user_id, symbol, position_type, api_key, api_secret, trade_statuses)
        # except Exception as e:
        #     logging.error(f"[stop_trade 강제종료 실패] {e}")

    return jsonify({"success": True, "msg": "매매 중단 및 포지션 강제 종료 요청됨."})

# ==============================
# 6. 메인
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

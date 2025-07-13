from dotenv import load_dotenv            # .env 파일 자동 로드
load_dotenv()

from flask import Flask, request, jsonify
import trade_worker                       # trade_worker.py 모듈 임포트

app = Flask(__name__)

@app.route("/start_trade", methods=["POST"])
def start_trade():
    data = request.json
    position_type = data.get("position_type")
    symbol = data.get("symbol")
    qty = data.get("qty")
    entry_time = data.get("entry_time")
    exit_time = data.get("exit_time")
    take_profit = data.get("take_profit")
    stop_loss = data.get("stop_loss")

    if trade_worker.trade_status["running"]:
        return jsonify({"success": False, "msg": "이미 매매 중입니다.", "info": trade_worker.trade_status["info"]})

    ok, msg = trade_worker.start_trade_thread(
        position_type=position_type,
        symbol=symbol,
        qty=qty,
        entry_time=entry_time,
        exit_time=exit_time,
        take_profit=take_profit,
        stop_loss=stop_loss
    )
    return jsonify({"success": ok, "msg": msg, "info": trade_worker.trade_status["info"]})

@app.route("/trade_status")
def get_trade_status():
    return jsonify({
        "running": trade_worker.trade_status["running"],
        "info": trade_worker.trade_status["info"],
        "error": trade_worker.trade_status["error"]
    })

@app.route("/get_balance")
def get_balance():
    coin = request.args.get("coin", "USDT")
    balance = trade_worker.get_balance(coin)
    return jsonify({"coin": coin, "balance": balance})

@app.route("/stop_trade", methods=["POST"])
def stop_trade():
    trade_worker.trade_status["running"] = False
    return jsonify({"success": True, "msg": "매매 중단 요청됨."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

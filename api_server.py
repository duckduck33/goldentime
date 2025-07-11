from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
import trade_worker  # trade_worker.py 모듈 임포트

app = Flask(__name__)

@app.route('/')
def home():
    return "골든타임 자동매매 서버가 정상 실행 중입니다."

@app.route('/start_trade', methods=['POST'])
def start_trade():
    data = request.json
    success, msg = trade_worker.start_trade_thread(
        position_type=data['position_type'],
        symbol=data['symbol'],
        qty=data['qty'],
        entry_time=data['entry_time'],
        exit_time=data['exit_time'],
        entry_price_cond=data.get('entry_price_cond'),
        take_profit=data.get('take_profit'),
        stop_loss=data.get('stop_loss')
    )
    status_code = 200 if success else 400
    return jsonify({"status": "ok" if success else "error", "msg": msg}), status_code

@app.route('/trade_status', methods=['GET'])
def get_trade_status():
    return jsonify(trade_worker.trade_status)

@app.route('/balance', methods=['GET'])
def balance():
    coin = request.args.get("coin", "USDT")
    return jsonify({"balance": trade_worker.get_balance(coin)})

@app.route('/price', methods=['GET'])
def price():
    symbol = request.args.get("symbol", "BTCUSDT")
    return jsonify({"price": trade_worker.get_price(symbol)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

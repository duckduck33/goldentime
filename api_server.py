from dotenv import load_dotenv            # .env 파일 자동 로드
load_dotenv()

from flask import Flask, request, jsonify
import trade_worker                       # trade_worker.py 모듈 임포트

# 1. Flask 앱 생성
app = Flask(__name__)

# 2. 홈(기본) 라우트: 서버 실행 확인용
@app.route('/')
def home():
    return "골든타임 자동매매 API 서버 정상 실행 중입니다."

# 3. 매매 시작 API
@app.route('/start_trade', methods=['POST'])
def start_trade():
    """
    POST JSON 몸체 예시:
    {
      "position_type": "long" or "short",
      "symbol": "BTCUSDT",
      "qty": 0.01,
      "entry_time": "2025-07-13 17:30",
      "exit_time": "2025-07-13 17:40",
      "entry_price_cond": 65200,  # 선택
      "take_profit": 65500,       # 선택
      "stop_loss": 64900          # 선택
    }
    """
    data = request.get_json()

    # 이미 매매 중이면 에러 반환
    if trade_worker.trade_status["running"]:
        return jsonify({"status": "error", "msg": "이미 매매 중입니다."}), 400

    # trade_worker 모듈의 start_trade_thread 호출
    success, msg = trade_worker.start_trade_thread(
        position_type   = data['position_type'],
        symbol          = data['symbol'],
        qty             = data['qty'],
        entry_time      = data['entry_time'],
        exit_time       = data['exit_time'],
        entry_price_cond= data.get('entry_price_cond'),
        take_profit     = data.get('take_profit'),
        stop_loss       = data.get('stop_loss')
    )

    code = 200 if success else 400
    return jsonify({"status": "ok" if success else "error", "msg": msg}), code

# 4. 매매 중지 API
@app.route('/stop_trade', methods=['POST'])
def stop_trade():
    """
    매매 중지 요청.
    trade_worker 내부에서 running=False로 표시하면
    while 루프가 즉시 탈출하여 쓰레드가 종료됩니다.
    """
    if not trade_worker.trade_status["running"]:
        return jsonify({"status": "error", "msg": "매매가 실행 중이 아닙니다."}), 400

    # 중지 플래그 세팅
    trade_worker.trade_status["running"] = False
    return jsonify({"status": "ok", "msg": "매매 중지 요청 완료"}), 200

# 5. 매매 상태 조회 API
@app.route('/trade_status', methods=['GET'])
def get_trade_status():
    """
    현재 매매 상태, 진행 정보, 에러 메시지 등을 반환
    """
    return jsonify(trade_worker.trade_status), 200

# 6. 잔고 조회 API
@app.route('/balance', methods=['GET'])
def balance():
    """
    GET 파라미터:
      coin (기본 "USDT")
    """
    coin = request.args.get("coin", "USDT")
    bal = trade_worker.get_balance(coin)
    return jsonify({"balance": bal}), 200

# 7. 현재가 조회 API
@app.route('/price', methods=['GET'])
def price():
    """
    GET 파라미터:
      symbol (기본 "BTCUSDT")
    """
    symbol = request.args.get("symbol", "BTCUSDT")
    price = trade_worker.get_price(symbol)
    return jsonify({"price": price}), 200

# 8. 서버 실행부
if __name__ == "__main__":
    # 호스트 0.0.0.0:8000에서 대기
    app.run(host="0.0.0.0", port=8000)

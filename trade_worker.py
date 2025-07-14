from datetime import datetime as dt
import pytz
import time
import logging

print("[VERSION] trade_worker.py 2025-07-15 04:55", dt.utcnow())

# trade_status 전역변수는 기존대로 유지
trade_status = {
    "running": False,
    "info": {},
    "error": None
}

def trade_worker(
    position_type,
    symbol,
    fixed_loss,
    entry_time,
    exit_time,
    take_profit=None,
    stop_loss=None,
    immediate=False
):
    kst = pytz.timezone('Asia/Seoul')

    print("[LOG] entry_time 파라미터:", entry_time)
    print("[LOG] exit_time 파라미터:", exit_time)
    print("[LOG] immediate:", immediate)

    try:
        # 기존처럼 entry_time/exit_time은 문자열(KST)로 들어온다고 가정
        dt_kst_entry = kst.localize(dt.strptime(entry_time, "%Y-%m-%d %H:%M"))
        dt_kst_exit = kst.localize(dt.strptime(exit_time, "%Y-%m-%d %H:%M"))

        # 반드시 UTC로 변환
        entry_dt = dt_kst_entry.astimezone(pytz.utc)
        exit_dt = dt_kst_exit.astimezone(pytz.utc)

        print("[LOG] 변환된 entry_dt(UTC):", entry_dt)
        print("[LOG] 변환된 exit_dt(UTC):", exit_dt)

        entry_fired = False
        logging.info("골든타임매매봇 시작합니다.")

        while not entry_fired:
            if not trade_status["running"]:
                print("[LOG] 매매 중단 감지! 반복문 탈출")
                break

            now = dt.utcnow().replace(tzinfo=pytz.utc)
            print("[LOG] 현재 서버 시간(now, UTC):", now)
            print("[LOG] 예약 진입 시간(entry_dt, UTC):", entry_dt)
            print("[LOG] 즉시매매(immediate):", immediate)

            if immediate or now >= entry_dt:
                print("[LOG] 진입 조건 만족! 매매 진입 (now >= entry_dt or immediate=True)")
                # ===> 기존 포지션 진입 코드가 여기에 위치 === #
                entry_fired = True
                break
            else:
                print("[LOG] 아직 진입 시간 전! 대기 중 (now < entry_dt)")

            time.sleep(5)

        # 이후 청산 등 추가 로직이 있으면 아래에...

        print("[LOG] 매매 스레드 종료")

    except Exception as e:
        print("[ERROR] 진입시간 파싱/비교 오류:", e)
        trade_status["running"] = False
        trade_status["error"] = str(e)
        return

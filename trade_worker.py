from datetime import datetime as dt
import pytz
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logging.info("[VERSION] trade_worker.py 2025-07-15 05:10 %s", dt.utcnow())

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

    logging.info("[LOG] entry_time 파라미터: %s", entry_time)
    logging.info("[LOG] exit_time 파라미터: %s", exit_time)
    logging.info("[LOG] immediate: %s", immediate)

    try:
        dt_kst_entry = kst.localize(dt.strptime(entry_time, "%Y-%m-%d %H:%M"))
        dt_kst_exit = kst.localize(dt.strptime(exit_time, "%Y-%m-%d %H:%M"))

        entry_dt = dt_kst_entry.astimezone(pytz.utc)
        exit_dt = dt_kst_exit.astimezone(pytz.utc)

        logging.info("[LOG] 변환된 entry_dt(UTC): %s", entry_dt)
        logging.info("[LOG] 변환된 exit_dt(UTC): %s", exit_dt)

        entry_fired = False
        logging.info("골든타임매매봇 시작합니다111.")

        while not entry_fired:
            if not trade_status["running"]:
                logging.info("[LOG] 매매 중단 감지! 반복문 탈출")
                break

            now = dt.utcnow().replace(tzinfo=pytz.utc)
            logging.info("[LOG] 현재 서버 시간(now, UTC): %s", now)
            logging.info("[LOG] 예약 진입 시간(entry_dt, UTC): %s", entry_dt)
            logging.info("[LOG] 즉시매매(immediate): %s", immediate)

            if immediate or now >= entry_dt:
                logging.info("[LOG] 진입 조건 만족! 매매 진입 (now >= entry_dt or immediate=True)")
                # 진입 로직
                entry_fired = True
                break
            else:
                logging.info("[LOG] 아직 진입 시간 전! 대기 중 (now < entry_dt)")

            time.sleep(5)

        logging.info("[LOG] 매매 스레드 종료")

    except Exception as e:
        logging.error("[ERROR] 진입시간 파싱/비교 오류: %s", e)
        trade_status["running"] = False
        trade_status["error"] = str(e)
        return

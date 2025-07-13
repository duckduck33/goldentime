# stop_loss_calc.py
"""
롱/숏 포지션별 손절값 계산 함수 모음
- 모든 함수는 최근 N개 봉의 저점/고점, 진입가격, 틱사이즈, 틱오프셋, 고정손절비율을 입력받음
"""

def get_long_stop_loss(
    lows: list,
    entry_price: float,
    tick_size: float = 1.0,
    tick_offset: int = 5,
    fallback_pct: float = 0.01
):
    """
    롱포지션 손절값 계산
    - 최근 N개 저점(lows) 중 진입가격보다 낮은 저점만 후보로 사용
    - 중복 제거, 진입가와의 거리순으로 1차/2차 지지선 선정
    - 2차 지지선-5틱이 1% 고정손절 아래면 1% 고정손절
    - 1차 지지선만 있으면 1% 고정손절
    - 지지선 없으면 1% 고정손절

    반환값: (손절값, 안내문, 퍼센트)
    """
    if not lows or entry_price is None:
        return None, "데이터 부족", None

    # 진입가격보다 낮은 저점 후보(중복 제거)
    support_candidates = list(set([low for low in lows if low < entry_price]))
    # 진입가와의 거리 기준 정렬(가까운 순)
    support_candidates_sorted = sorted(support_candidates, key=lambda x: abs(entry_price - x))

    if len(support_candidates_sorted) >= 2:
        one_pct_below = entry_price * (1 - fallback_pct)
        stop_loss = support_candidates_sorted[1] - tick_size * tick_offset
        if stop_loss < one_pct_below:
            stop_loss = round(one_pct_below, 8)
            msg = f"2차 지지선({support_candidates_sorted[1]}) - 5틱 손절값이 진입가 대비 1% 아래로 내려가 1% 고정 손절이 적용됩니다."
        else:
            msg = f"손절값: 2차 지지선({support_candidates_sorted[1]}) - 5틱 = {stop_loss} 입니다"
    elif len(support_candidates_sorted) == 1:
        stop_loss = round(entry_price * (1 - fallback_pct), 8)
        msg = f"손절값: 1차 지지선만 있으므로 1% 고정 손절({stop_loss})입니다"
    else:
        stop_loss = round(entry_price * (1 - fallback_pct), 8)
        msg = f"손절값: 진입가가 최저가여서 1% 고정 손절({stop_loss})입니다"

    # 손절값이 진입가 대비 몇 %인지
    stop_pct = None
    if stop_loss and entry_price:
        stop_pct = (entry_price - stop_loss) / entry_price * 100
        msg += f"\n손절값은 {stop_loss}로, 진입가격 대비 약 {stop_pct:.2f}% 입니다."

    return stop_loss, msg, stop_pct

def get_short_stop_loss(
    highs: list,
    entry_price: float,
    tick_size: float = 1.0,
    tick_offset: int = 5,
    fallback_pct: float = 0.01
):
    """
    숏포지션 손절값 계산
    - 최근 N개 고점(highs) 중 진입가격보다 높은 고점만 후보로 사용
    - 중복 제거, 진입가와의 거리순으로 1차/2차 저항선 선정
    - 2차 저항선+5틱이 1% 고정손절 위면 1% 고정손절
    - 1차 저항선만 있으면 1% 고정손절
    - 저항선 없으면 1% 고정손절

    반환값: (손절값, 안내문, 퍼센트)
    """
    if not highs or entry_price is None:
        return None, "데이터 부족", None

    # 진입가격보다 높은 고점 후보(중복 제거)
    resistance_candidates = list(set([high for high in highs if high > entry_price]))
    # 진입가와의 거리 기준 정렬(가까운 순)
    resistance_candidates_sorted = sorted(resistance_candidates, key=lambda x: abs(entry_price - x))

    if len(resistance_candidates_sorted) >= 2:
        one_pct_above = entry_price * (1 + fallback_pct)
        stop_loss = resistance_candidates_sorted[1] + tick_size * tick_offset
        if stop_loss > one_pct_above:
            stop_loss = round(one_pct_above, 8)
            msg = f"2차 저항선({resistance_candidates_sorted[1]}) + 5틱 손절값이 진입가 대비 1% 위로 올라가 1% 고정 손절이 적용됩니다."
        else:
            msg = f"손절값: 2차 저항선({resistance_candidates_sorted[1]}) + 5틱 = {stop_loss} 입니다"
    elif len(resistance_candidates_sorted) == 1:
        stop_loss = round(entry_price * (1 + fallback_pct), 8)
        msg = f"손절값: 1차 저항선만 있으므로 1% 고정 손절({stop_loss})입니다"
    else:
        stop_loss = round(entry_price * (1 + fallback_pct), 8)
        msg = f"손절값: 진입가가 최고가여서 1% 고정 손절({stop_loss})입니다"

    # 손절값이 진입가 대비 몇 %인지
    stop_pct = None
    if stop_loss and entry_price:
        stop_pct = (stop_loss - entry_price) / entry_price * 100
        msg += f"\n손절값은 {stop_loss}로, 진입가격 대비 약 {stop_pct:.2f}% 입니다."

    return stop_loss, msg, stop_pct

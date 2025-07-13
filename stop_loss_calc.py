def get_long_stop_loss(
    lows: list,
    entry_price: float,
    tick_size: float = 1.0,
    tick_offset: int = 5,
    fallback_pct: float = 0.01,
    take_profit_ratio: float = 0.02  # 익절 퍼센트 (ex: 2%)
):
    """
    롱포지션 손절값 자동 계산 + 시나리오 메시지
    """
    if not lows or entry_price is None:
        return None, "데이터 부족", None

    support_candidates_sorted = sorted(set([low for low in lows if low < entry_price]), reverse=True)

    # 1) 1차/2차 지지선 출력
    first_support = f"{support_candidates_sorted[0]}" if len(support_candidates_sorted) >= 1 else "없음"
    second_support = f"{support_candidates_sorted[1]}" if len(support_candidates_sorted) >= 2 else "없음"
    support_msg = f"1차 지지선: {first_support}, 2차 지지선: {second_support}"

    # 2) 손절값 계산 및 설명
    if len(support_candidates_sorted) >= 2:
        one_pct_below = entry_price * (1 - fallback_pct)
        stop_loss = support_candidates_sorted[1] - tick_size * tick_offset
        if stop_loss < one_pct_below:
            stop_loss = round(one_pct_below, 8)
            detail_msg = f"손절값: 2차 지지선({support_candidates_sorted[1]}) - 5틱 손절값이 진입가 대비 1% 아래로 내려가 1% 고정 손절이 적용됩니다."
        else:
            detail_msg = f"손절값: 2차 지지선({support_candidates_sorted[1]}) - 5틱 = {stop_loss} 입니다"
    elif len(support_candidates_sorted) == 1:
        stop_loss = round(entry_price * (1 - fallback_pct), 8)
        detail_msg = f"손절값: 1차 지지선만 있으므로 1% 고정 손절({stop_loss})입니다"
    else:
        stop_loss = round(entry_price * (1 - fallback_pct), 8)
        detail_msg = f"손절값: 진입가가 최저가여서 1% 고정 손절({stop_loss})입니다"

    # 3) 손절 퍼센트 안내
    stop_pct = (entry_price - stop_loss) / entry_price * 100 if stop_loss and entry_price else None
    pct_msg = f"손절값은 {stop_loss}로, 진입가격 대비 약 {stop_pct:.2f}% 입니다." if stop_pct is not None else ""

    # 4) 익절 안내
    take_profit = round(entry_price * (1 + take_profit_ratio), 8)
    tp_pct = take_profit_ratio * 100
    tp_msg = f"익절값은 {take_profit}으로 진입가격대비 {tp_pct:.2f}%입니다."

    # 전체 메시지 조립
    full_msg = f"{support_msg}\n{detail_msg}\n{pct_msg}\n{tp_msg}"
    return stop_loss, full_msg, stop_pct
def get_short_stop_loss(
    highs: list,
    entry_price: float,
    tick_size: float = 1.0,
    tick_offset: int = 5,
    fallback_pct: float = 0.01,
    take_profit_ratio: float = 0.02  # 익절 퍼센트 (ex: 2%)
):
    """
    숏포지션 손절값 자동 계산 + 시나리오 메시지
    """
    if not highs or entry_price is None:
        return None, "데이터 부족", None

    resistance_candidates_sorted = sorted(set([high for high in highs if high > entry_price]))

    # 1) 1차/2차 저항선 출력
    first_res = f"{resistance_candidates_sorted[0]}" if len(resistance_candidates_sorted) >= 1 else "없음"
    second_res = f"{resistance_candidates_sorted[1]}" if len(resistance_candidates_sorted) >= 2 else "없음"
    resistance_msg = f"1차 저항선: {first_res}, 2차 저항선: {second_res}"

    # 2) 손절값 계산 및 설명
    if len(resistance_candidates_sorted) >= 2:
        one_pct_above = entry_price * (1 + fallback_pct)
        stop_loss = resistance_candidates_sorted[1] + tick_size * tick_offset
        if stop_loss > one_pct_above:
            stop_loss = round(one_pct_above, 8)
            detail_msg = f"손절값: 2차 저항선({resistance_candidates_sorted[1]}) + 5틱 손절값이 진입가 대비 1% 위로 올라가 1% 고정 손절이 적용됩니다."
        else:
            detail_msg = f"손절값: 2차 저항선({resistance_candidates_sorted[1]}) + 5틱 = {stop_loss} 입니다"
    elif len(resistance_candidates_sorted) == 1:
        stop_loss = round(entry_price * (1 + fallback_pct), 8)
        detail_msg = f"손절값: 1차 저항선만 있으므로 1% 고정 손절({stop_loss})입니다"
    else:
        stop_loss = round(entry_price * (1 + fallback_pct), 8)
        detail_msg = f"손절값: 진입가가 최고가여서 1% 고정 손절({stop_loss})입니다"

    # 3) 손절 퍼센트 안내
    stop_pct = (stop_loss - entry_price) / entry_price * 100 if stop_loss and entry_price else None
    pct_msg = f"손절값은 {stop_loss}로, 진입가격 대비 약 {stop_pct:.2f}% 입니다." if stop_pct is not None else ""

    # 4) 익절 안내
    take_profit = round(entry_price * (1 - take_profit_ratio), 8)
    tp_pct = take_profit_ratio * 100
    tp_msg = f"익절값은 {take_profit}으로 진입가격대비 {tp_pct:.2f}%입니다."

    # 전체 메시지 조립
    full_msg = f"{resistance_msg}\n{detail_msg}\n{pct_msg}\n{tp_msg}"
    return stop_loss, full_msg, stop_pct

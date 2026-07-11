from state import state, state_lock


def fmt_wan(token_count):
    return f"{token_count / 10000:.2f} 万"


def build_detail_text(data):
    lot = data["currentLot"]
    estimate = data.get("estimate", {})

    remaining = lot["remainingToken"]
    total = lot["totalToken"]
    consumed = lot["consumedToken"]
    ratio = lot["consumedRatio"] * 100
    remain_days = lot["remainSeconds"] // 86400
    remain_hours = (lot["remainSeconds"] % 86400) // 3600

    lines = [
        f"Token 剩余：{fmt_wan(remaining)}  （共 {fmt_wan(total)}）",
        f"已消耗：{fmt_wan(consumed)}  （{ratio:.2f}%）",
        f"有效期至：{lot['expireTime']}",
        f"距离过期：{remain_days} 天 {remain_hours} 小时",
        "",
        f"近 {estimate.get('windowDays', '-')} 天日均消耗：{fmt_wan(estimate.get('dailyAverageToken', 0))}",
        f"按当前速率预计还可用：{estimate.get('exhaustedAfterDays', '-')} 天",
    ]

    other_lots = data.get("otherLots") or []
    if other_lots:
        lines.append("")
        lines.append(f"另有 {len(other_lots)} 个未激活/排队中的资源包")

    with state_lock:
        last_update = state["last_update"]
    if last_update:
        lines.append("")
        lines.append(f"数据更新于：{last_update.strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)

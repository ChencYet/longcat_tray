import logging
import os
import sys

import pystray

from config import CONFIG_PATH, config, save_config
from formatter import build_detail_text, fmt_wan
from state import (
    detail_dialog_open,
    force_refresh_event,
    cookie_notify_done,
    state,
    state_lock,
    stop_event,
)
from utils import is_autostart_enabled, set_autostart, show_message


def open_config_in_notepad():
    try:
        os.startfile(CONFIG_PATH)
    except Exception as e:
        logging.error(f"打开配置文件失败: {e}")
        show_message("打开失败", f"无法打开配置文件：{e}\n\n路径：{CONFIG_PATH}", is_warning=True)


def action_refresh_now(icon, item):
    from config import load_config
    try:
        new_cfg = load_config()
        config.clear()
        config.update(new_cfg)
    except Exception as e:
        logging.error(f"刷新时重载配置失败: {e}")
    force_refresh_event.set()


def action_show_details(icon, item):
    if detail_dialog_open.is_set():
        return
    detail_dialog_open.set()
    try:
        with state_lock:
            data = state["last_data"]
            error = state["last_error"]

        if data:
            show_message("LongCat 用量详情", build_detail_text(data))
        else:
            show_message(
                "LongCat 用量详情",
                f"暂无数据。\n\n{error or '尚未成功获取过数据，请稍后重试或检查 Cookie 是否有效。'}",
                is_warning=True,
            )
    finally:
        detail_dialog_open.clear()


def make_interval_setter(minutes):
    def _setter(icon, item):
        config["refresh_interval_minutes"] = minutes
        save_config(config)
        force_refresh_event.set()
    return _setter


def is_interval_checked(minutes):
    def _checker(item):
        return config.get("refresh_interval_minutes", 0) == minutes
    return _checker


def action_exit(icon, item):
    stop_event.set()
    icon.stop()


def action_auto_cookie(icon, item):
    from utils import fetch_cookie_in_browser
    import threading
    threading.Thread(target=fetch_cookie_in_browser, daemon=True).start()


def action_edit_cookie(icon, item):
    open_config_in_notepad()



def action_toggle_autostart(icon, item):
    if is_autostart_enabled():
        set_autostart(False)
    else:
        set_autostart(True)


def is_autostart_checked(item):
    return is_autostart_enabled()


def build_menu():
    interval_options = [
        ("仅手动刷新", 0),
        ("1 分钟", 1),
        ("5 分钟", 5),
        ("15 分钟", 15),
        ("30 分钟", 30),
        ("60 分钟", 60),
    ]
    interval_menu = pystray.Menu(
        *[
            pystray.MenuItem(
                label,
                make_interval_setter(minutes),
                checked=is_interval_checked(minutes),
                radio=True,
            )
            for label, minutes in interval_options
        ]
    )

    detail_lines = []
    with state_lock:
        data = state["last_data"]
        error = state["last_error"]
    if data:
        lot = data["currentLot"]
        estimate = data.get("estimate", {})
        remaining = lot["remainingToken"]
        total = lot["totalToken"]
        consumed = lot["consumedToken"]
        ratio = lot["consumedRatio"] * 100
        remain_days = lot["remainSeconds"] // 86400
        remain_hours = (lot["remainSeconds"] % 86400) // 3600
        last_update = state["last_update"]
        update_time = last_update.strftime("%H:%M:%S") if last_update else "--:--:--"
        detail_lines = [
            f"剩余 {fmt_wan(remaining)} / {fmt_wan(total)}",
            f"已消耗 {fmt_wan(consumed)} ({ratio:.1f}%)",
            f"有效期 {lot['expireTime']}",
            f"剩余 {remain_days}天{remain_hours}小时",
            f"日均 {fmt_wan(estimate.get('dailyAverageToken', 0))}",
            f"预计 {estimate.get('exhaustedAfterDays', '-')} 天后用尽",
            f"刷新 {update_time}",
        ]
    elif error:
        detail_lines = [f"获取失败: {error}"]
    else:
        detail_lines = ["正在加载..."]

    detail_items = [pystray.MenuItem(line, None, enabled=False) for line in detail_lines]

    return pystray.Menu(
        *detail_items,
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("立即刷新", action_refresh_now),
        pystray.MenuItem("自动获取 Cookie", action_auto_cookie),
        pystray.MenuItem("编辑 Cookie（记事本）", action_edit_cookie),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("刷新间隔", interval_menu),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("开机自启", action_toggle_autostart, checked=is_autostart_checked),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", action_exit),
    )

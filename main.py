import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime

import pystray

from api import fetch_usage
from config import config
from formatter import fmt_wan
from icon import create_icon_image
from state import (
    cookie_notify_done,
    force_refresh_event,
    icon_ref,
    low_quota_notified,
    state,
    state_lock,
    stop_event,
)
from tray_menu import build_menu, open_config_in_notepad
from utils import show_message

_log_dir = os.path.join(os.path.expanduser("~"), ".longcat_tray")
os.makedirs(_log_dir, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(_log_dir, "error.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
logging.info("=== 程序启动 ===")


def _handle_fetch_error(msg):
    with state_lock:
        state["last_error"] = msg
    if icon_ref:
        icon_ref.icon = create_icon_image(0, error=True)
        icon_ref.title = f"LongCat 用量获取失败\n{msg}"
        icon_ref.menu = build_menu()
        if not cookie_notify_done.is_set():
            cookie_notify_done.set()
            try:
                icon_ref.notify(msg, title="LongCat 用量监控")
            except Exception:
                pass


def do_refresh():
    ok, result = fetch_usage(config)

    if not ok:
        _handle_fetch_error(result)
        return False

    try:
        lot = result["currentLot"]
        total = lot["totalToken"]
        percent_remaining = lot["remainingToken"] / total * 100 if total else 0
        estimate = result.get("estimate", {})
    except (KeyError, TypeError, ZeroDivisionError) as e:
        logging.error(f"数据解析失败: {e}\n原始数据: {result}")
        _handle_fetch_error(f"接口返回数据格式异常：{e}")
        return False

    cookie_notify_done.clear()
    low_quota_notified.clear()

    with state_lock:
        state["last_data"] = result
        state["last_update"] = datetime.now()
        state["last_error"] = None

    _update_icon(percent_remaining, lot, estimate)
    return True


def _update_icon(percent_remaining, lot, estimate):
    if not icon_ref:
        return

    icon_ref.icon = create_icon_image(percent_remaining)
    icon_ref.title = (
        f"LongCat 剩余 {percent_remaining:.1f}%\n"
        f"已消耗 {fmt_wan(lot['consumedToken'])} / {fmt_wan(lot['totalToken'])}\n"
        f"预计 {estimate.get('exhaustedAfterDays', '-')} 天后用尽"
    )
    icon_ref.menu = build_menu()

    threshold = config.get("low_quota_threshold_percent", 20)
    if percent_remaining < threshold:
        if not low_quota_notified.is_set():
            low_quota_notified.set()
            try:
                icon_ref.notify(
                    f"Token 剩余仅 {percent_remaining:.1f}%，注意及时续购",
                    title="LongCat 用量预警",
                )
            except Exception:
                pass


def refresh_loop():
    while not stop_event.is_set():
        try:
            do_refresh()
        except Exception:
            logging.critical(f"do_refresh 未捕获异常:\n{traceback.format_exc()}")

        elapsed = 0
        while not stop_event.is_set():
            time.sleep(1)
            elapsed += 1

            if force_refresh_event.is_set():
                force_refresh_event.clear()
                break

            interval_minutes = config.get("refresh_interval_minutes", 0)
            if interval_minutes and elapsed >= interval_minutes * 60:
                break


def main():
    global icon_ref

    has_cookie = bool(config.get("cookie"))
    if has_cookie:
        logging.info("Cookie 已就绪，启动托盘")
    else:
        logging.info("未配置 Cookie，以空状态启动托盘")

    initial_image = create_icon_image(0, error=True)
    icon_ref = pystray.Icon(
        "longcat_usage",
        initial_image,
        "LongCat 用量监控\n正在加载...\n\n右键 → 自动获取 Cookie",
        menu=build_menu(),
    )

    t = threading.Thread(target=refresh_loop, daemon=True)
    t.start()

    icon_ref.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"程序异常退出: {e}\n{traceback.format_exc()}")
        show_message(
            "程序异常",
            f"程序启动失败:\n\n{e}\n\n详情见日志: {_log_dir}\\error.log",
            is_warning=True,
        )
        sys.exit(1)

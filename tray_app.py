# -*- coding: utf-8 -*-
"""
LongCat 用量监控托盘小工具
功能：
  - 定时/手动调用 LongCat 用量接口，获取 Token 剩余、消耗比例等信息
  - 托盘图标根据剩余比例变色（绿/橙/红）
  - 右键菜单查看详情、立即刷新、设置刷新间隔、退出
"""

import ctypes
import json
import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont
import pystray

# ------------------------------------------------------------------
# 启动错误日志（打包后诊断用）
# ------------------------------------------------------------------
_log_dir = os.path.join(os.path.expanduser("~"), ".longcat_tray")
os.makedirs(_log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(_log_dir, "error.log"),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
logging.info("=== 程序启动 ===")

# ------------------------------------------------------------------
# tkinter 弹窗（解决原生MessageBox卡死问题）
# ------------------------------------------------------------------
import tkinter as tk
from tkinter import messagebox

def show_message(title, text, is_warning=False):
    def show():
        try:
            root = tk.Tk()
            root.withdraw()
            root.lift()
            root.attributes('-topmost', True)
            root.after_idle(root.attributes, '-topmost', False)
            if is_warning:
                messagebox.showwarning(title, text, parent=root)
            else:
                messagebox.showinfo(title, text, parent=root)
            root.destroy()
        except Exception as e:
            print(f"弹窗显示失败: {e}")

    # 确保在主线程执行
    if threading.current_thread() is threading.main_thread():
        show()
    else:
        # 从其他线程调用时，延迟一点扔到主线程
        threading.Timer(0.05, show).start()


# ------------------------------------------------------------------
# 基础路径与配置读写
# ------------------------------------------------------------------

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
logging.info(f"BASE_DIR={BASE_DIR}, CONFIG_PATH={CONFIG_PATH}")

DEFAULT_CONFIG = {
    "api_url": "https://longcat.chat/api/pay/quota/metering/token-packs/summary",
    "cookie": "",
    "refresh_interval_minutes": 5,
    "low_quota_threshold_percent": 20,
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


config = load_config()


# ------------------------------------------------------------------
# Cookie 自动获取
# ------------------------------------------------------------------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin():
    exe = sys.executable
    params = " ".join([f'"{a}"' for a in sys.argv])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    sys.exit(0)


def fetch_browser_cookie():
    try:
        import browser_cookie3
    except ImportError:
        logging.error("browser_cookie3 not installed")
        return ""

    browsers = [
        ("Chrome", browser_cookie3.chrome),
        ("Edge", browser_cookie3.edge),
    ]

    for name, loader in browsers:
        try:
            cookies = loader(domain_name="longcat.chat")
            cookie_list = list(cookies)
            if cookie_list:
                seen = set()
                parts = []
                for c in cookie_list:
                    if c.name not in seen:
                        seen.add(c.name)
                        parts.append(f"{c.name}={c.value}")
                cookie_str = "; ".join(parts)
                logging.info(f"Got cookie from {name}: {len(parts)} cookies")
                return cookie_str
        except Exception as e:
            logging.warning(f"Failed to read {name} cookies: {e}")
    return ""


def auto_acquire_cookie():
    if config.get("cookie"):
        return True
    if not is_admin():
        logging.info("No cookie, relaunching as admin to fetch from Chrome")
        return False
    logging.info("Admin mode, attempting to read Chrome cookies")
    cookie_str = fetch_browser_cookie()
    if cookie_str:
        config["cookie"] = cookie_str
        save_config(config)
        logging.info("Cookie saved to config.json")
        return True
    logging.error("Failed to read Chrome cookies even as admin")
    return False


# 运行期共享状态
state_lock = threading.Lock()
state = {
    "last_data": None,
    "last_update": None,
    "last_error": None,
}

stop_event = threading.Event()
force_refresh_event = threading.Event()
detail_dialog_open = threading.Event()
cookie_notify_done = threading.Event()

icon_ref = None


# ------------------------------------------------------------------
# 接口请求
# ------------------------------------------------------------------

def fetch_usage():
    headers = {
        "Cookie": config["cookie"],
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://longcat.chat/platform/usage",
        "Origin": "https://longcat.chat",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(config["api_url"], headers=headers, json={}, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        return False, f"请求失败：{e}"

    if payload.get("code") != 0:
        return False, f"接口返回异常（Cookie 可能已失效）：{payload.get('msg')}"

    return True, payload.get("data")


# ------------------------------------------------------------------
# 图标绘制
# ------------------------------------------------------------------

def get_font(size):
    candidates = ["arialbd.ttf", "msyhbd.ttc", "arial.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def create_icon_image(percent_remaining, error=False):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if error:
        color = (120, 120, 120, 255)
        text = "!"
    else:
        if percent_remaining >= 50:
            color = (67, 160, 71, 255)
        elif percent_remaining >= 20:
            color = (255, 152, 0, 255)
        else:
            color = (229, 57, 53, 255)
        text = str(int(round(percent_remaining)))

    draw.ellipse((2, 2, size - 2, size - 2), fill=color)

    font = get_font(26 if len(text) <= 2 else 20)
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]),
        text,
        fill="white",
        font=font,
    )
    return img


# ------------------------------------------------------------------
# 数据格式化
# ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# 刷新与图标更新
# ------------------------------------------------------------------

def do_refresh():
    ok, result = fetch_usage()

    if not ok:
        with state_lock:
            state["last_error"] = result
        if icon_ref:
            icon_ref.icon = create_icon_image(0, error=True)
            icon_ref.title = f"LongCat 用量获取失败\n{result}"
            icon_ref.menu = build_menu()
            if not cookie_notify_done.is_set():
                cookie_notify_done.set()
                try:
                    icon_ref.notify(
                        "数据获取失败，可能是 Cookie 已失效。\n请在浏览器重新登录 longcat.chat。",
                        title="LongCat 用量监控",
                    )
                except Exception:
                    pass
        return False

    cookie_notify_done.clear()

    with state_lock:
        state["last_data"] = result
        state["last_update"] = datetime.now()
        state["last_error"] = None

    lot = result["currentLot"]
    percent_remaining = lot["remainingToken"] / lot["totalToken"] * 100
    estimate = result.get("estimate", {})

    if icon_ref:
        icon_ref.icon = create_icon_image(percent_remaining)
        icon_ref.title = (
            f"LongCat 剩余 {percent_remaining:.1f}%\n"
            f"已消耗 {fmt_wan(lot['consumedToken'])} / {fmt_wan(lot['totalToken'])}\n"
            f"预计 {estimate.get('exhaustedAfterDays', '-')} 天后用尽"
        )
        icon_ref.menu = build_menu()

        threshold = config.get("low_quota_threshold_percent", 20)
        if percent_remaining < threshold:
            try:
                icon_ref.notify(
                    f"Token 剩余仅 {percent_remaining:.1f}%，注意及时续购",
                    title="LongCat 用量预警",
                )
            except Exception:
                pass

    return True


def refresh_loop():
    do_refresh()
    elapsed = 0
    while not stop_event.is_set():
        time.sleep(1)
        elapsed += 1

        if force_refresh_event.is_set():
            force_refresh_event.clear()
            do_refresh()
            elapsed = 0
            continue

        interval_minutes = config.get("refresh_interval_minutes", 0)
        if interval_minutes and elapsed >= interval_minutes * 60:
            do_refresh()
            elapsed = 0


# ------------------------------------------------------------------
# 菜单动作
# ------------------------------------------------------------------

def action_refresh_now(icon, item):
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


# ------------------------------------------------------------------
# 主程序
# ------------------------------------------------------------------

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
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("刷新间隔", interval_menu),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", action_exit),
    )


def main():
    global icon_ref

    if not auto_acquire_cookie():
        show_message(
            "正在获取 Cookie",
            "首次启动需要从浏览器读取 Cookie。\n\n即将弹出 UAC 授权，请点击「是」允许。",
        )
        relaunch_as_admin()
        return

    logging.info("Cookie 已就绪，启动托盘")
    initial_image = create_icon_image(0, error=True)
    icon_ref = pystray.Icon(
        "longcat_usage",
        initial_image,
        "LongCat 用量监控\n正在加载...",
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
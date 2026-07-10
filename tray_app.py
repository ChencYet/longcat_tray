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
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
logging.info("=== 程序启动 ===")

# ------------------------------------------------------------------
# 原生弹窗（不依赖 tkinter，避免 PyInstaller 打包坑，且天然线程安全）
# ------------------------------------------------------------------
def show_message(title, text, is_warning=False):
    MB_OK = 0x0
    MB_ICONINFORMATION = 0x40
    MB_ICONWARNING = 0x30
    MB_TOPMOST = 0x40000
    style = MB_OK | MB_TOPMOST | (MB_ICONWARNING if is_warning else MB_ICONINFORMATION)
    try:
        ctypes.windll.user32.MessageBoxW(0, text, title, style)
    except Exception as e:
        logging.error(f"弹窗显示失败: {e}")


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
# WebView2 内嵌登录获取 Cookie
# ------------------------------------------------------------------
def acquire_cookie_via_webview():
    try:
        import webview
    except ImportError:
        logging.error("pywebview not installed")
        return False

    LOGIN_URL = "https://longcat.chat/platform/usage"
    TARGET_COOKIE = "passport_token_key"
    result = {}
    event = threading.Thread(target=lambda: None)  # dummy

    def check_cookies(window):
        for _ in range(180):
            try:
                cookies = window.get_cookies()
                for c in cookies:
                    if c.get('name') == TARGET_COOKIE and c.get('value'):
                        cookie_dict = {}
                        for cc in cookies:
                            domain = cc.get('domain', '')
                            if 'longcat' in domain:
                                name = cc.get('name', '')
                                value = cc.get('value', '')
                                if name:
                                    cookie_dict[name] = value
                        if cookie_dict:
                            parts = [f"{k}={v}" for k, v in cookie_dict.items()]
                            result['cookie'] = "; ".join(parts)
                            logging.info(f"WebView2 got cookie from longcat.chat")
                            window.destroy()
                        return
            except Exception as e:
                logging.debug(f"Cookie check: {e}")
            time.sleep(2)

    def on_loaded(window):
        threading.Thread(target=check_cookies, args=(window,), daemon=True).start()

    window = webview.create_window(
        "LongCat 登录 - 登录完成后自动获取 Cookie",
        url=LOGIN_URL,
        width=1000,
        height=700,
        on_top=True,
    )

    try:
        webview.start(lambda: on_loaded(window), gui='edgechromium')
    except Exception as e:
        logging.error(f"webview.start failed: {e}")
        return False

    if result.get('cookie'):
        config['cookie'] = result['cookie']
        save_config(config)
        return True
    return False


# ------------------------------------------------------------------
# 打开配置文件供手动编辑
# ------------------------------------------------------------------
def open_config_in_notepad():
    try:
        os.startfile(CONFIG_PATH)
    except Exception as e:
        logging.error(f"打开配置文件失败: {e}")
        show_message("打开失败", f"无法打开配置文件：{e}\n\n路径：{CONFIG_PATH}", is_warning=True)


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


def action_edit_cookie(icon, item):
    open_config_in_notepad()


def action_reload_config(icon, item):
    global config
    try:
        config = load_config()
        logging.info("配置已手动重新加载")
        force_refresh_event.set()
    except Exception as e:
        logging.error(f"重新加载配置失败: {e}")
        show_message("重新加载失败", f"读取 config.json 失败：{e}", is_warning=True)


def action_relogin(icon, item):
    stop_event.set()
    icon.stop()
    threading.Thread(target=_relogin_and_restart, daemon=True).start()


def _relogin_and_restart():
    if acquire_cookie_via_webview():
        show_message("Cookie 已更新", "重新登录成功，请手动重启程序。")
    else:
        show_message("登录失败", "未能获取新 Cookie。", is_warning=True)


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
        pystray.MenuItem("编辑 Cookie（记事本）", action_edit_cookie),
        pystray.MenuItem("重新加载配置", action_reload_config),
        pystray.MenuItem("重新登录（WebView）", action_relogin),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("刷新间隔", interval_menu),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", action_exit),
    )


def main():
    global icon_ref

    if not config.get("cookie"):
        show_message(
            "需要登录 LongCat",
            "还没有配置 Cookie。\n\n"
            "即将打开登录窗口，请在窗口内完成登录。\n"
            "登录成功后程序会自动获取 Cookie。",
        )
        if not acquire_cookie_via_webview():
            show_message(
                "获取 Cookie 失败",
                "WebView2 登录未成功。\n\n"
                "可能原因：\n"
                "1. 未登录就关闭了窗口\n"
                "2. WebView2 Runtime 未安装\n\n"
                "即将用记事本打开 config.json，请手动填入 Cookie。",
                is_warning=True,
            )
            open_config_in_notepad()
            sys.exit(0)
        show_message("Cookie 获取成功", "登录成功，程序即将开始监控用量。")

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

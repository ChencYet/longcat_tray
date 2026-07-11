import ctypes
import json
import logging
import os
import sys
import winreg

APP_NAME = "LongCatUsage"


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


def set_autostart(enable):
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pythonw):
                pythonw = sys.executable
            main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            exe_path = f'"{pythonw}" "{main_py}"'

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        logging.error(f"设置开机自启失败: {e}")


def is_autostart_enabled():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def _find_system_chrome():
    import shutil
    system_chromes = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for path in system_chromes:
        if os.path.exists(path):
            return path
    return shutil.which("chrome") or shutil.which("msedge")


def _validate_cookie(cookie_str):
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://longcat.chat/api/pay/quota/metering/token-packs/summary",
            headers={
                "Cookie": cookie_str,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json",
            },
            method="POST",
            data=b"{}",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            return body.get("code") == 0 and body.get("data") is not None
    except Exception:
        pass
    return False


def fetch_cookie_in_browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        show_message(
            "缺少依赖",
            "未找到 playwright，请安装：\n  pip install playwright\n\n"
            "然后重启程序，或手动获取 Cookie。",
            is_warning=True,
        )
        return

    log_dir = os.path.join(os.path.expanduser("~"), ".longcat_tray")

    try:
        with sync_playwright() as p:
            browser_path = _find_system_chrome()
            kwargs = {"headless": False}
            if browser_path:
                kwargs["executable_path"] = browser_path
            browser = p.chromium.launch(**kwargs)
            context = browser.new_context()
            page = context.new_page()

            page.goto("https://longcat.chat/platform/usage", wait_until="domcontentloaded", timeout=30000)

            max_wait = 300
            elapsed = 0
            cookie_found = None

            while elapsed < max_wait:
                page.wait_for_timeout(5000)
                elapsed += 5

                all_cookies = context.cookies()
                domain_cookies = [c for c in all_cookies if "longcat.chat" in c.get("domain", "")]
                if domain_cookies:
                    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in domain_cookies)
                    if len(cookie_str) > 20 and _validate_cookie(cookie_str):
                        cookie_found = cookie_str
                        break

            browser.close()

        if cookie_found:
            config_path = os.path.join(
                os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
                else os.path.dirname(os.path.abspath(__file__)),
                "config.json"
            )
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    try:
                        cfg = json.load(f)
                    except (json.JSONDecodeError, ValueError):
                        cfg = {}
            else:
                cfg = {
                    "api_url": "https://longcat.chat/api/pay/quota/metering/token-packs/summary",
                    "refresh_interval_minutes": 5,
                    "low_quota_threshold_percent": 20,
                }
            cfg["cookie"] = cookie_found
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)

            show_message(
                "Cookie 获取成功",
                f"已保存到 config.json\n\n请重新启动程序或右键「立即刷新」。",
            )
        else:
            show_message(
                "获取失败",
                "未获取到有效 Cookie（超时）\n\n请确认已登录 longcat.chat 后重试。",
                is_warning=True,
            )
    except Exception as e:
        logging.error(f"获取 Cookie 失败: {e}")
        show_message("获取失败", f"发生错误：{e}", is_warning=True)

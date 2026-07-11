"""
自动获取 LongCat Cookie 的辅助脚本。

启动方式：
  - 独立运行: python get_cookie.py
  - 从托盘菜单: 点击「自动获取 Cookie」

原理：
  启动浏览器打开用量页面，直接在浏览器中读取登录态 Cookie 保存到 config.json。
  不依赖特定接口请求，只要登录了就能抓到。
"""

import json
import sys
import os
import urllib.request
import urllib.error

API_URL = "https://longcat.chat/api/pay/quota/metering/token-packs/summary"
CHECK_URL = "https://longcat.chat/api/pay/quota/metering/token-packs/summary"

TARGET_PAGE = "https://longcat.chat/platform/usage"
DOMAIN = "longcat.chat"

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║              LongCat Cookie 自动获取工具                     ║
╠══════════════════════════════════════════════════════════════╣
║  1. 浏览器窗口会自动打开                                     ║
║  2. 如果未登录请在浏览器中登录                               ║
║  3. 脚本会直接读取浏览器 Cookie                              ║
║  4. 获取成功后会自动保存并退出                               ║
║                                                              ║
║  按 Ctrl+C 可取消                                            ║
╚══════════════════════════════════════════════════════════════╝
"""


def get_config_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "config.json")


def save_cookie_to_config(cookie_value):
    config_path = get_config_path()
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
    cfg["cookie"] = cookie_value
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return config_path


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
    chrome_in_path = shutil.which("chrome") or shutil.which("msedge")
    if chrome_in_path:
        return chrome_in_path
    return None


def _get_domain_cookies(context, domain):
    all_cookies = context.cookies()
    domain_cookies = [c for c in all_cookies if domain in c.get("domain", "")]
    if not domain_cookies:
        return None
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in domain_cookies)
    return cookie_str


def _validate_cookie(cookie_str):
    try:
        req = urllib.request.Request(
            CHECK_URL,
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
            if body.get("code") == 0 and body.get("data"):
                return True
    except Exception:
        pass
    return False


def run():
    print(BANNER)
    log_file = os.path.join(os.path.expanduser("~"), ".longcat_tray", "get_cookie.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        msg = f"[错误] 未安装 playwright: {e}"
        print(msg)
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(f"\n{msg}\n")
        input("\n按回车退出...")
        return False

    print("[*] 正在启动浏览器...")

    try:
        with sync_playwright() as p:
            browser_path = _find_system_chrome()
            if browser_path:
                browser = p.chromium.launch(
                    headless=False,
                    executable_path=browser_path,
                )
            else:
                browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            page.goto(TARGET_PAGE, wait_until="domcontentloaded", timeout=30000)
            print(f"[*] 已打开: {TARGET_PAGE}")
            print("[*] 请在浏览器中登录（如未登录）...")
            print("[*] 登录后脚本会自动验证并保存，等待中...\n")

            max_wait = 300
            elapsed = 0
            cookie_found = None

            try:
                while elapsed < max_wait:
                    page.wait_for_timeout(5000)
                    elapsed += 5

                    cookie_str = _get_domain_cookies(context, DOMAIN)
                    if not cookie_str or len(cookie_str) < 20:
                        if elapsed % 20 == 0:
                            print(f"[*] 已等待 {elapsed} 秒...（未检测到 Cookie，请在浏览器登录）")
                        continue

                    print(f"[*] 检测到 Cookie（{len(cookie_str)} 字符），正在验证有效性...")
                    if _validate_cookie(cookie_str):
                        cookie_found = cookie_str
                        print(f"\n[✓] Cookie 验证通过！")
                        break
                    else:
                        print(f"[!] Cookie 无效（可能是旧凭证），继续等待...")
                        if elapsed % 30 == 0:
                            print(f"[!] 请在浏览器中重新登录 longcat.chat")

            except KeyboardInterrupt:
                print("\n[*] 用户取消")
                browser.close()
                return False

            browser.close()

    except Exception as e:
        error_msg = f"[错误] 浏览器启动失败: {e}\n请确认系统已安装 Chrome 或 Edge 浏览器"
        print(error_msg)
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(f"\n{error_msg}\n")
        input("\n按回车退出...")
        return False

    if cookie_found:
        config_path = save_cookie_to_config(cookie_found)
        print(f"\n[✓] Cookie 已保存到: {config_path}")
        print("[*] 请重新启动 LongCat 用量监控程序")
        return True
    else:
        print("\n[✗] 未获取到有效 Cookie（超时）")
        print("[*] 请确认已登录 longcat.chat 后重试")
        print("[*] 或手动获取：")
        print("  1. F12 → 网络 → Fetch/XHR")
        print("  2. 找到任意 longcat.chat 请求 → 复制 Cookie 请求头")
        print("  3. 粘贴到 config.json 的 cookie 字段")
        return False


if __name__ == "__main__":
    success = run()
    if not success:
        input("\n按回车退出...")
    sys.exit(0 if success else 1)

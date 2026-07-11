"""
自动获取 LongCat Cookie 的辅助脚本。

启动方式：
  - 独立运行: python get_cookie.py
  - 从托盘菜单: 点击「自动获取 Cookie」

原理：
  启动一个真实的浏览器窗口，让用户手动登录 longcat.chat，
  脚本会自动监听网络请求，当匹配到目标接口时抓取 Cookie 并写入 config.json。
"""

import json
import sys
import os

API_URL_PATH = "/api/pay/quota/metering/token-packs/summary"

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║              LongCat Cookie 自动获取工具                     ║
╠══════════════════════════════════════════════════════════════╣
║  1. 浏览器窗口会自动打开 longcat.chat                        ║
║  2. 请在浏览器中手动登录你的 LongCat 账号                    ║
║  3. 脚本会自动监听网络请求，匹配到目标接口后自动提取 Cookie   ║
║  4. 获取成功后会自动保存并退出                               ║
║                                                              ║
║  提示：登录后在页面随便点一下触发用量查询，能加快匹配速度     ║
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


def run():
    print(BANNER)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[错误] 未安装 playwright，请先运行：")
        print("  pip install playwright")
        print("  playwright install chromium")
        input("\n按回车退出...")
        return False

    try:
        from playwright.sync_api import TimeoutError as PWTimeout
    except ImportError:
        PWTimeout = Exception

    print("[*] 正在启动浏览器...")

    cookie_found = [None]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        def handle_request(request):
            if cookie_found[0]:
                return
            if API_URL_PATH in request.url and request.method == "POST":
                headers = request.headers
                cookie = headers.get("cookie", "")
                if cookie:
                    cookie_found[0] = cookie
                    print(f"\n[✓] 已捕获到 Cookie！")
                    print(f"    匹配接口: {request.url}")
                    print(f"    Cookie 长度: {len(cookie)} 字符")

        page.on("request", handle_request)

        page.goto("https://longcat.chat", wait_until="domcontentloaded", timeout=30000)
        print("[*] 浏览器已打开，请在页面中登录...")
        print("[*] 登录后系统会自动跳转，识别到 Cookie 后会自动退出\n")

        try:
            while not cookie_found[0]:
                page.wait_for_timeout(500)
        except KeyboardInterrupt:
            print("\n[*] 用户取消")
            browser.close()
            return False

        browser.close()

    if cookie_found[0]:
        config_path = save_cookie_to_config(cookie_found[0])
        print(f"[✓] Cookie 已保存到: {config_path}")
        print("[*] 请重新启动 LongCat 用量监控程序")
        return True
    else:
        print("[✗] 未获取到 Cookie")
        return False


if __name__ == "__main__":
    success = run()
    if not success:
        input("\n按回车退出...")
    sys.exit(0 if success else 1)

"""
自动获取 LongCat Cookie 的辅助脚本。

启动方式：
  - 独立运行: python get_cookie.py
  - 从托盘菜单: 点击「自动获取 Cookie」

原理：
  启动一个真实的浏览器窗口，让用户手动登录 longcat.chat，
  脚本会自动导航到用量页面触发目标接口请求，匹配后抓取 Cookie 写入 config.json。
"""

import json
import sys
import os

API_URL_PATH = "/api/pay/quota/metering/token-packs/summary"
TARGET_PAGE = "https://longcat.chat/platform/usage"

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║              LongCat Cookie 自动获取工具                     ║
╠══════════════════════════════════════════════════════════════╣
║  1. 浏览器窗口会自动打开                                     ║
║  2. 请在浏览器中手动登录（如未登录）                         ║
║  3. 导航到用量页面后自动抓取 Cookie                          ║
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


def run():
    print(BANNER)
    log_file = os.path.join(os.path.expanduser("~"), ".longcat_tray", "get_cookie.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        msg = f"[错误] 未安装 playwright: {e}\n请先运行：\n  pip install playwright\n  playwright install chromium"
        print(msg)
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(f"\n{msg}\n")
        input("\n按回车退出...")
        return False

    print("[*] 正在启动浏览器...")
    with open(log_file, "a", encoding="utf-8") as lf:
        lf.write("\n--- get_cookie 启动 ---\n")

    cookie_found = [None]

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

            page.goto(TARGET_PAGE, wait_until="domcontentloaded", timeout=30000)
            print(f"[*] 已打开用量页面: {TARGET_PAGE}")
            print("[*] 如未登录请先在浏览器中登录，登录后页面会自动刷新")
            print("[*] 脚本正在监听网络请求，获取到 Cookie 后会自动退出...\n")

            login_check_interval = 15
            elapsed = 0
            try:
                while not cookie_found[0]:
                    page.wait_for_timeout(1000)
                    elapsed += 1

                    if elapsed == login_check_interval:
                        print("[!] 未检测到目标请求，可能未登录或页面未触发用量查询")
                        print("[!] 正在重新导航到用量页面...")
                        page.goto(TARGET_PAGE, wait_until="domcontentloaded", timeout=30000)
                        print("[*] 已刷新页面，继续监听...\n")

                    if elapsed % 30 == 0 and elapsed > 0 and not cookie_found[0]:
                        current_url = page.url
                        print(f"[*] 已等待 {elapsed} 秒，当前页面: {current_url}")

            except KeyboardInterrupt:
                print("\n[*] 用户取消")
                browser.close()
                return False

            browser.close()
    except Exception as e:
        error_msg = f"[错误] 浏览器启动失败: {e}\n可能是 playwright 浏览器未安装，请运行：playwright install chromium"
        print(error_msg)
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(f"\n{error_msg}\n")
        input("\n按回车退出...")
        return False

    if cookie_found[0]:
        config_path = save_cookie_to_config(cookie_found[0])
        print(f"\n[✓] Cookie 已保存到: {config_path}")
        print("[✓] 请关闭浏览器窗口（如未自动关闭）")
        print("[*] 现在可以重新启动 LongCat 用量监控程序")
        return True
    else:
        print("[✗] 未获取到 Cookie")
        return False


if __name__ == "__main__":
    success = run()
    if not success:
        input("\n按回车退出...")
    sys.exit(0 if success else 1)

import logging
import time

import requests


def fetch_usage(cfg, max_retries=2):
    headers = {
        "Cookie": cfg["cookie"],
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://longcat.chat/platform/usage",
        "Origin": "https://longcat.chat",
        "Content-Type": "application/json",
    }

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(cfg["api_url"], headers=headers, json={}, timeout=10)
            resp.raise_for_status()
            payload = resp.json()
            break
        except requests.exceptions.ConnectionError as e:
            if attempt == max_retries:
                return False, f"网络连接失败：{e}"
            logging.warning(f"fetch_usage 第 {attempt + 1} 次尝试连接失败: {e}")
            time.sleep(1.5 * (attempt + 1))
        except requests.exceptions.Timeout as e:
            if attempt == max_retries:
                return False, f"请求超时：{e}"
            logging.warning(f"fetch_usage 第 {attempt + 1} 次尝试超时: {e}")
            time.sleep(1.5 * (attempt + 1))
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                return False, f"请求失败：{e}"
            logging.warning(f"fetch_usage 第 {attempt + 1} 次尝试失败: {e}")
            time.sleep(1.5 * (attempt + 1))
        except Exception as e:
            if attempt == max_retries:
                return False, f"请求失败：{e}"
            logging.warning(f"fetch_usage 第 {attempt + 1} 次尝试出错: {e}")
            time.sleep(1.5 * (attempt + 1))

    if payload.get("code") != 0:
        return False, f"接口返回异常（Cookie 可能已失效）：{payload.get('msg')}"

    return True, payload.get("data")

import json
import logging
import os
import sys
import time

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

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
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.error(f"config.json 损坏，已备份并重置: {e}")
        bad_path = CONFIG_PATH + f".bad-{int(time.time())}"
        try:
            os.replace(CONFIG_PATH, bad_path)
        except Exception:
            pass
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)

    if not isinstance(cfg.get("refresh_interval_minutes"), (int, float)) or cfg["refresh_interval_minutes"] < 0:
        cfg["refresh_interval_minutes"] = DEFAULT_CONFIG["refresh_interval_minutes"]

    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


config = load_config()

import threading

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
low_quota_notified = threading.Event()
icon_ref = None

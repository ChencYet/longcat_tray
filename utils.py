import ctypes
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

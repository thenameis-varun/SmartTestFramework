# src/utils.py
import os
import sys

def get_logs_dir():
    """
    Return the correct logs directory depending on whether we are running
    as a PyInstaller bundle or in dev mode.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in exe mode → logs live next to the launcher.exe
        logs_dir = os.path.join(os.getcwd(), "logs")
    else:
        # Running in dev mode → logs go to src/logs
        base_path = os.path.dirname(__file__)
        logs_dir = os.path.join(base_path, "logs")

    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

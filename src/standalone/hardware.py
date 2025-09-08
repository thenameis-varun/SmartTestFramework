# Copyright (c) 2025 Varun Kumar BS.
# This file contains proprietary code and/or utilities for development purposes.

import subprocess
import platform
import re

def mock_hardware_detection():
    """Static list of known DUTs (fallback)."""
    return [
        {"DUT": 1, "hardware_type": "Dgx", "serial": "123456", "com_port": "COM3", "mac_address": "00:1A:2B:3C:4D:5E"},
        {"DUT": 2, "hardware_type": "woa", "serial": "123457", "com_port": "COM4", "mac_address": "00:1A:2B:3C:4D:5F"},
        {"DUT": 3, "hardware_type": "Dgx", "serial": "123458", "com_port": "COM5", "mac_address": "00:1A:2B:3C:4D:60"},
    ]

def auto_detect_network_devices():
    """
    Use ARP table to list active devices quickly.
    Works on Windows and Linux/Mac.
    """
    devices = []
    try:
        output = subprocess.check_output("arp -a", shell=True).decode()

        if platform.system().lower() == "windows":
            for line in output.splitlines():
                match = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+([\da-f-]+)\s+\w+", line)
                if match:
                    ip, mac = match.groups()
                    devices.append(f"{ip} ({mac})")
        else:  # Linux/Mac
            for line in output.splitlines():
                match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\) at ([\da-f:]+)", line)
                if match:
                    ip, mac = match.groups()
                    devices.append(f"{ip} ({mac})")
    except Exception as e:
        devices.append(f"Error: {e}")

    return devices

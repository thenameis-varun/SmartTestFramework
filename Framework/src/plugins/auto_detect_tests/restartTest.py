# Copyright (c) 2025 Varun Kumar BS.
# This file contains proprietary code and/or utilities for development purposes.

import paramiko
import time
import os

def run_test(iterations=1, params=None):
    if params is None:
        params = {}

    ip = params.get("ip")
    username = params.get("username")
    password = params.get("password")
    key_file = params.get("key_file")  # support private key auth
    delay = params.get("delay", 0)     # extra wait time after reboot

    # ✅ Validate required parameters
    if not ip or not username:
        return {
            "outcome": "Fail",
            "metrics": {"error": f"Missing required SSH parameters (ip={ip}, username={username})"}
        }

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    outputs = []
    try:
        for i in range(iterations):
            # Retry connect for up to 30s
            start_time = time.time()
            connected = False
            while time.time() - start_time < 30:
                try:
                    print(f"[INFO] Attempting SSH to {ip} as {username} (iteration {i+1})...")
                    print(f"{ip},{username},{password},{delay}")
                    if key_file and os.path.exists(key_file):
                        pkey = paramiko.RSAKey.from_private_key_file(key_file)
                        client.connect(ip, username=username, pkey=pkey, timeout=5)
                    else:
                        client.connect(ip, username=username, password=password, timeout=5)
                    connected = True
                    break
                except Exception as e:
                    print(f"[WARN] SSH attempt failed: {e}")
                    time.sleep(2)

            if not connected:
                print(f"[ERROR] Connection failed after 30s to {ip}")
                return {"outcome": "Fail", "metrics": {"error": f"SSH connection failed on iteration {i+1}"}}

            print(f"[INFO] Connected to {ip} as {username}")

            # Run restart command
            stdin, stdout, stderr = client.exec_command("shutdown /r /t 0")
            error = stderr.read().decode(errors="ignore").strip()
            client.close()

            if error:
                print(f"[ERROR] Iteration {i+1} restart command error: {error}")
                return {"outcome": "Fail", "metrics": {"error": error}}

            print(f"[INFO] Restart command issued on iteration {i+1}.")
            wait_time = 60 + delay
            print(f"[INFO] Waiting {wait_time} seconds for reboot...")
            outputs.append(f"Restart {i+1} executed")

            # Always wait at least 60s + delay for reboot
            time.sleep(wait_time)

        return {"outcome": "Pass", "metrics": {"details": f"Completed {iterations} restarts"}}

    except Exception as e:
        print(f"[ERROR] Command execution failed: {e}")
        return {"outcome": "Fail", "metrics": {"error": str(e)}}

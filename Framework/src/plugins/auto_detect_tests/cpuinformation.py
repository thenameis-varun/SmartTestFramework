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
    delay = params.get("delay", 1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Retry connect for up to 20s
    start_time = time.time()
    connected = False
    while time.time() - start_time < 20:
        try:
            print(f"Attempting SSH to {ip} as {username}...")
            if key_file and os.path.exists(key_file):
                pkey = paramiko.RSAKey.from_private_key_file(key_file)
                client.connect(ip, username=username, pkey=pkey, timeout=5)
            else:
                client.connect(ip, username=username, password=password, timeout=5)
            connected = True
            break
        except Exception:
            time.sleep(2)

    if not connected:
        print(f"Connection failed after 20s to {ip}")
        return {"outcome": "Fail", "metrics": {"error": "SSH connection failed"}}

    print(f"Connected to {ip} as {username}")

    outputs = []
    try:
        for i in range(iterations):
            # CPU info command for Linux/Windows
            stdin, stdout, stderr = client.exec_command("cat /proc/cpuinfo || systeminfo | findstr /C:\"Processor\"")
            output = stdout.read().decode(errors="ignore").strip()
            error = stderr.read().decode(errors="ignore").strip()

            if error:
                print(f"Iteration {i+1} error: {error}")
                return {"outcome": "Fail", "metrics": {"error": error}}

            print("\n---------------------------------------------------------")
            print(f"CPU Information :: Iteration {i+1}:\n{output}\n")
            outputs.append(output)

            if i < iterations - 1:
                time.sleep(delay)

        client.close()

        if all(out == outputs[0] for out in outputs):
            return {"outcome": "Pass", "metrics": {"details": outputs[0]}}
        else:
            return {"outcome": "Fail", "metrics": {"error": "Inconsistent CPU outputs"}}

    except Exception as e:
        print(f"Command execution failed: {e}")
        return {"outcome": "Fail", "metrics": {"error": str(e)}}

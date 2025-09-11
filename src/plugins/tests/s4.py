# Copyright (c) 2025 Varun Kumar BS.
# This file contains proprietary code and/or utilities for development purposes.

import random
import time
import sys

# Ensure UTF-8 printing
sys.stdout.reconfigure(encoding='utf-8')

# Uncomment and run this below run_test method once there is serial communication established w/ actual hardware.

# def run_test(iterations, ports, baudrates, sleep_command="S4_SLEEP\n", wake_command="WAKE_UP\n", timeout=1):
#     """
#     Run S4 sleep/wake test on multiple devices via serial communication.

#     Parameters:
#         iterations (int): Number of sleep/wake cycles.
#         ports (list): List of serial ports for the devices.
#         baudrates (list): List of baud rates corresponding to the ports.
#         sleep_command (str): Command to put device into S4 sleep.
#         wake_command (str): Command to wake device from S4 sleep.
#         timeout (int/float): Serial timeout.

#     Returns:
#         str: "Pass" if all iterations succeed on all devices, else "Fail".
#     """
#     if len(ports) != len(baudrates):
#         print("Error: Number of ports and baudrates must match.")
#         return "Fail"

#     serial_devices = []
#     for i, port in enumerate(ports):
#         try:
#             ser = serial.Serial(port, baudrates[i], timeout=timeout)
#             serial_devices.append(ser)
#             print(f"Connected to device {i+1} on {port} at {baudrates[i]} baud.")
#         except serial.SerialException as e:
#             print(f"Failed to connect to device {i+1}: {e}")
#             return "Fail"

#     all_passed = True

#     for iteration in range(iterations):
#         print(f"\n=== S4 Iteration {iteration + 1} ===")
#         for i, ser in enumerate(serial_devices):
#             try:
#                 # Put device into S4 sleep
#                 print(f"Device {i+1}: Sending sleep command...")
#                 ser.write(sleep_command.encode())
#                 time.sleep(2)  # Adjust delay if needed

#                 # Wake device up
#                 print(f"Device {i+1}: Sending wake command...")
#                 ser.write(wake_command.encode())
#                 time.sleep(2)

#                 # Read response
#                 if ser.in_waiting:
#                     response = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
#                     print(f"Device {i+1} response:\n{response}")
#                 else:
#                     print(f"Device {i+1}: No response received.")

#             except Exception as e:
#                 print(f"Device {i+1}: Error during iteration {iteration + 1}: {e}")
#                 all_passed = False

#     for ser in serial_devices:
#         ser.close()

#     result = "Pass" if all_passed else "Fail"
#     print(f"\nOverall Result: {result}")
#     return result

# Below is the dummy run_test method

def run_test(iterations):
    for i in range(iterations):
        print(f"S4 Iteration {i+1}: Booting system... {random.randint(1000, 9999)}")
        gibberish_chars = []
        for _ in range(20):
            random_char_code = random.randint(32, 126)  # Printable ASCII
            gibberish_chars.append(chr(random_char_code))
        print("".join(gibberish_chars))
        time.sleep(0.5)
    result = random.choice(["Pass", "Fail"])
    print(f"Result: {result}")
    return result

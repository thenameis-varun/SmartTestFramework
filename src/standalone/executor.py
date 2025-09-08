# Copyright (c) 2025 Varun Kumar BS.
# This file contains proprietary code and/or utilities for development purposes.

import sqlite3
import json
from test_runner import run_test_in_cmd


def get_next_job_id(conn):
    cursor = conn.execute("SELECT next_job_id FROM JobIDCounter WHERE counter_id = 1")
    job_id = cursor.fetchone()[0]
    conn.execute(
        "UPDATE JobIDCounter SET next_job_id = ? WHERE counter_id = 1", (job_id + 1,)
    )
    return job_id


def process_jobs(conn, dut, hardware_type, serial, com_port, mac_address):
    """
    Process queued jobs for a given DUT. If DUT row is missing, simply return.
    """
    cursor = conn.execute("SELECT job_queue FROM DUTStatus WHERE dut = ?", (dut,))
    row = cursor.fetchone()
    if row is None:
        # No DUTStatus row — nothing to process here.
        return {
            "outcome": "No DUTStatus",
            "metrics": {},
            "job_id": None,
            "queued": False,
        }

    while True:
        cursor = conn.execute("SELECT job_queue FROM DUTStatus WHERE dut = ?", (dut,))
        row = cursor.fetchone()
        if row is None:
            # Row disappeared or was removed; stop processing
            break

        job_queue = json.loads(row[0])

        if not job_queue:
            conn.execute(
                "UPDATE DUTStatus SET status = ? WHERE dut = ?", ("Free", dut)
            )
            conn.commit()
            break

        job = job_queue.pop(0)
        conn.execute(
            "UPDATE DUTStatus SET job_queue = ? WHERE dut = ?",
            (json.dumps(job_queue), dut),
        )
        conn.commit()

        try:
            result = run_test_in_cmd(job)
        except Exception as e:
            # Ensure we always log something
            result = {"outcome": "Fail", "metrics": {"error": str(e)}}

        conn.execute(
            "INSERT INTO Logs (job_id, dut, hardware_type, serial, com_port, mac_address, test_name, parameters, outcome, metrics, ip, username, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                job_id,
                dut_db,
                hardware_type,
                serial,
                com_port,
                mac_address,
                test_name,
                json.dumps(parameters),
                result.get("outcome"),
                json.dumps(result.get("metrics", {})),
                parameters.get("ip"),
                parameters.get("username"),
            ),
        )

        conn.commit()

    return {"outcome": "ProcessedQueue", "metrics": {}, "queued": False}


def submit_job(
    conn, dut, hardware_type, serial, com_port, mac_address, test_name, iterations, parameters
):
    """
    Submit a job. If DUT exists in DUTStatus, respect queueing and Busy/Free.
    If DUT doesn't exist (e.g. an auto-detected network device), run immediately
    and log result without attempting to modify DUTStatus.
    Always return a dict describing the job result or queued state.
    """

    if parameters is None:
        parameters = {}

    import streamlit as st
    # Detect manual vs auto-detect
    cursor = conn.execute("SELECT 1 FROM DUTStatus WHERE dut = ?", (dut,))
    row = cursor.fetchone()
    manual_mode = row is not None

    if not manual_mode:
        # Auto-detect mode → enforce SSH details
        parameters["ip"] = parameters.get("ip") or st.session_state.get("auto_detected_device")
        parameters["username"] = parameters.get("username") or st.session_state.get("auto_detect_username")
        parameters["password"] = parameters.get("password") or st.session_state.get("auto_detect_password")

        if not parameters["ip"] or not parameters["username"]:
            return {
                "job_id": None,
                "outcome": "Fail",
                "metrics": {
                    "error": f"Missing required SSH parameters (ip={parameters.get('ip')}, username={parameters.get('username')})"
                },
                "queued": False,
            }
    else:
        # Manual mode → ignore SSH fields
        parameters["ip"] = None
        parameters["username"] = None
        parameters["password"] = None


    job_id = get_next_job_id(conn)
    job = {
        "job_id": job_id,
        "dut": dut,
        "hardware_type": hardware_type,
        "serial": serial,
        "com_port": com_port,
        "mac_address": mac_address,
        "test_name": test_name,
        "iterations": iterations,
        "parameters": parameters,
    }

    # Try to fetch DUTStatus row for this dut. If missing, treat as "non-managed" (e.g. auto device).
    try:
        cursor = conn.execute(
            "SELECT status, job_queue FROM DUTStatus WHERE dut = ?", (dut,)
        )
        row = cursor.fetchone()
    except Exception:
        row = None

    if row is None:
        # No DUTStatus row: run job immediately and log result. Use dut_db = -1 to indicate external device.
        dut_db = -1 if not isinstance(dut, int) else dut
        try:
            result = run_test_in_cmd(job)
        except Exception as e:
            result = {"outcome": "Fail", "metrics": {"error": str(e)}}

        try:
            conn.execute(
                """INSERT INTO Logs
                (job_id, dut, hardware_type, serial, com_port, mac_address,
                    test_name, parameters, outcome, metrics, ip, username, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    job_id,
                    dut_db,
                    hardware_type,
                    serial,
                    com_port,
                    mac_address,
                    test_name,
                    json.dumps(parameters),
                    result.get("outcome"),
                    json.dumps(result.get("metrics", {})),
                    parameters.get("ip"),
                    parameters.get("username"),
                ),
            )
            conn.commit()
        except Exception:
            return {
                "job_id": job_id,
                "outcome": "Fail",
                "metrics": {"error": "DB insert failed"},
                "queued": False,
            }

        return {
            "job_id": job_id,
            "outcome": result.get("outcome"),
            "metrics": result.get("metrics"),
            "queued": False,
        }
    else:
        # Existing DUT — preserve original queue logic
        status, job_queue_json = row
        job_queue = json.loads(job_queue_json or "[]")

        if status == "Free" and not job_queue:
            # Run immediately and mark Busy
            conn.execute("UPDATE DUTStatus SET status = ? WHERE dut = ?", ("Busy", dut))
            conn.commit()

            try:
                result = run_test_in_cmd(job)
            except Exception as e:
                result = {"outcome": "Fail", "metrics": {"error": str(e)}}

            conn.execute(
                """INSERT INTO Logs
                (job_id, dut, hardware_type, serial, com_port, mac_address,
                    test_name, parameters, outcome, metrics, ip, username, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    job_id,
                    dut,
                    hardware_type,
                    serial,
                    com_port,
                    mac_address,
                    test_name,
                    json.dumps(parameters),
                    result.get("outcome"),
                    json.dumps(result.get("metrics", {})),
                    parameters.get("ip"),
                    parameters.get("username"),
                ),
            )
            conn.commit()

            process_jobs(conn, dut, hardware_type, serial, com_port, mac_address)
            return {
                "job_id": job_id,
                "outcome": result.get("outcome"),
                "metrics": result.get("metrics"),
                "queued": False,
            }
        else:
            # Add to queue
            job_queue.append(job)
            conn.execute(
                "UPDATE DUTStatus SET job_queue = ? WHERE dut = ?",
                (json.dumps(job_queue), dut),
            )
            conn.commit()
            return {
                "job_id": job_id,
                "outcome": "queued",
                "metrics": {},
                "queued": True,
            }


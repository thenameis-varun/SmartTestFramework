# Copyright (c) 2025 Varun Kumar BS.
# This file contains proprietary code and/or utilities for development purposes.

# src/database.py
import sqlite3
import json
from hardware import mock_hardware_detection

def init_db(db_path="framework.db"):
    conn = sqlite3.connect(db_path, check_same_thread=False)

    # Create DUTStatus table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS DUTStatus (
            dut INTEGER PRIMARY KEY,
            status TEXT,
            job_queue TEXT
        )
    """)

    # Initialize DUTStatus for all DUTs (if missing)
    hardware = mock_hardware_detection()
    cursor = conn.execute("SELECT dut FROM DUTStatus")
    existing_duts = {row[0] for row in cursor}
    for h in hardware:
        if h["DUT"] not in existing_duts:
            conn.execute("INSERT INTO DUTStatus (dut, status, job_queue) VALUES (?, ?, ?)",
                        (h["DUT"], "Free", json.dumps([])))

    # Create Logs table (base schema)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Logs (
            log_id INTEGER PRIMARY KEY,
            job_id INTEGER,
            dut INTEGER,
            hardware_type TEXT,
            serial TEXT,
            com_port TEXT,
            mac_address TEXT,
            ip TEXT,
            username TEXT,
            test_name TEXT,
            parameters TEXT,
            outcome TEXT,
            metrics TEXT,
            timestamp DATETIME
        )
    """)

    # Check if logs table contains ip/username columns; migration not strictly necessary because
    # we created them above; but if older DB exists, ensure the columns exist:
    # Get current columns
    cur = conn.execute("PRAGMA table_info(Logs)")
    existing_cols = {row[1] for row in cur}
    # If ip or username missing, recreate table with new schema (safe copy)
    required_cols = {"log_id","job_id","dut","hardware_type","serial","com_port","mac_address","ip","username","test_name","parameters","outcome","metrics","timestamp"}
    if not required_cols.issubset(existing_cols):
        # perform safe migration: copy into new table
        conn.execute("ALTER TABLE Logs RENAME TO Logs_old_temp")
        # Create Logs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Logs (
                log_id INTEGER PRIMARY KEY,
                job_id INTEGER,
                dut INTEGER,
                hardware_type TEXT,
                serial TEXT,
                com_port TEXT,
                mac_address TEXT,
                test_name TEXT,
                parameters TEXT,
                outcome TEXT,
                metrics TEXT,
                ip TEXT,
                username TEXT,
                timestamp DATETIME
            )
        """)

        # Copy available columns from old table if exist
        old_cols = list(existing_cols)
        common = [c for c in ["log_id","job_id","dut","hardware_type","serial","com_port","mac_address","test_name","parameters","outcome","metrics","timestamp"] if c in old_cols]
        if common:
            placeholders = ", ".join(common)
            conn.execute(f"INSERT INTO Logs ({placeholders}) SELECT {placeholders} FROM Logs_old_temp")
        conn.execute("DROP TABLE Logs_old_temp")
        conn.commit()

    # Create JobIDCounter table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS JobIDCounter (
            counter_id INTEGER PRIMARY KEY,
            next_job_id INTEGER
        )
    """)
    # Initialize JobIDCounter if empty
    cursor = conn.execute("SELECT COUNT(*) FROM JobIDCounter")
    if cursor.fetchone()[0] == 0:
        conn.execute("INSERT INTO JobIDCounter (counter_id, next_job_id) VALUES (1, 1)")

    conn.commit()
    return conn

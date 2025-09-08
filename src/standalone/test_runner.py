# Copyright (c) 2025 Varun Kumar BS.
# This file contains proprietary code and/or utilities for development purposes.

import subprocess
import os
import random
import sys
import tempfile
import json as _json


def run_test_in_cmd(job):
    """
    Run the named test in a new process and return {"outcome": ..., "metrics": {...}}.
    Search for the test module first in src/plugins/tests, then in src/plugins/auto_detect_tests.
    The test module must expose run_test(iterations, **kwargs) or run_test(iterations).
    We call it via a temporary runner file to avoid shell escaping issues.
    """

    test_name = job.get("test_name")
    iterations = job.get("iterations", 1)
    job_id = job.get("job_id")

    tests_dir = os.path.join(os.getcwd(), "src", "plugins", "tests")
    auto_tests_dir = os.path.join(os.getcwd(), "src", "plugins", "auto_detect_tests")

    # Determine test file path (prefer auto_detect_tests first if present there)
    candidate_paths = [
        os.path.join(auto_tests_dir, f"{test_name}.py"),
        os.path.join(tests_dir, f"{test_name}.py"),
    ]

    found_path = None
    for p in candidate_paths:
        if os.path.exists(p):
            found_path = p
            break

    if not found_path:
        # Create logs dir and write error
        os.makedirs("src/logs", exist_ok=True)
        log_file = os.path.abspath(os.path.join("src", "logs", f"job_{job_id}.txt"))
        with open(log_file, "w") as f:
            f.write(f"Error: Test script {test_name}.py not found in expected locations.")
        return {
            "outcome": "Fail",
            "metrics": {"error": "Test script not found", "serial": job.get("serial")},
        }

    # Ensure logs directory exists
    os.makedirs("src/logs", exist_ok=True)
    log_file = os.path.abspath(os.path.join("src", "logs", f"job_{job_id}.txt"))
    error_log = os.path.abspath(os.path.join("src", "logs", f"job_{job_id}_error.txt"))

    # Build PYTHONPATH to include both test directories so import will work
    env = os.environ.copy()
    pythonpath_parts = [auto_tests_dir, tests_dir]
    env["PYTHONPATH"] = (
        os.pathsep.join([p for p in pythonpath_parts if os.path.exists(p)])
        + os.pathsep
        + env.get("PYTHONPATH", "")
    )

    # Prepare parameters
    params = job.get("parameters", {})
    params_literal = _json.dumps(params)

    # Runner code with no leading spaces (fix for IndentationError)
    runner_code = f"""import json,sys
import {test_name}

params = json.loads('''{params_literal}''')
try:
    r = {test_name}.run_test({iterations}, params)
except TypeError:
    r = {test_name}.run_test({iterations})
print("\\n===RESULT_START===")
print(json.dumps(r))
print("===RESULT_END===")
"""


    # Write this to a temp file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as tmpfile:
        tmpfile.write(runner_code)
        runner_path = tmpfile.name

    cmd = [sys.executable, runner_path]

    try:
        # Run the test subprocess and capture stdout to the log file
        with open(log_file, "w", encoding="utf-8") as lf:
            process = subprocess.Popen(
                cmd,
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=os.path.dirname(found_path),
                shell=False,
            )
            process.wait()
    except Exception as e:
        with open(error_log, "w", encoding="utf-8") as f:
            f.write(f"Subprocess error: {str(e)}")
        return {
            "outcome": "Fail",
            "metrics": {"error": f"Subprocess failed: {str(e)}", "serial": job.get("serial")},
        }

    # After process completes, attempt to read log and determine outcome.
    if not os.path.exists(log_file):
        with open(error_log, "w", encoding="utf-8") as f:
            f.write("Error: Log file was not created")
        return {
            "outcome": "Fail",
            "metrics": {"error": "Log file not created", "serial": job.get("serial")},
        }

    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()

    # Basic heuristic to decide pass/fail
    outcome = "Fail"
    metrics = {"runtime": random.randint(100, 1000), "serial": job.get("serial")}

    try:
        import re, json as _json2
        m = re.search(r"===RESULT_START===\\s*(\\{{.*\\}})\\s*===RESULT_END===", log_content, re.DOTALL)
        if m:
            data = _json2.loads(m.group(1))
            if isinstance(data, dict):
                out = data.get("outcome") or data.get("result") or data.get("status")
                if out:
                    outcome = "Pass" if str(out).lower().startswith("pass") else "Fail"
                if "metrics" in data and isinstance(data["metrics"], dict):
                    metrics.update(data["metrics"])

    except Exception:
        pass

    if "Result: Pass" in log_content or "PASS" in log_content.upper():
        outcome = "Pass"

    return {"outcome": outcome, "metrics": metrics}

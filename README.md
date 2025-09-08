# Table of Contents    

| Line -> Section            
|------|--------------------
| 12   -> Introduction
| 28   -> Technical Highlights
| 53   -> Project Structure
| 90   -> Project Workflow
| 282  -> User Manual

_________________________________________________________________________________________________________

**INTRODUCTION**

*TestFrameworkApplication* - it is a next-generation hardware & remote device testing framework application, blending automation, AI-driven parameter tuning, and interactive dashboards into one powerful package.

It provides:

Serial Connection Mode → For direct DUT (Device Under Test) validation over local COM/USB ports.

Remote Connection Mode → For network-based auto-detected devices, with secure SSH execution and multi-user dashboards.

The framework empowers hardware engineers, QA testers, and DevOps teams to validate devices locally or across distributed systems.

More than a framework — it’s a portable, plug-and-play foundation that makes test automation flexible and reusable

_________________________________________________________________________________________________________

**TECHNICAL HIGHLIGHTS**

* AI Integration: Reinforcement Learning optimizes test parameters (iterations, delays) dynamically based on DUT/test history.

* Data Persistence: SQLite3 with transaction-safe job logs, DUT states, and queue tracking ensures consistency and recoverability.

* Scalable Architecture: Modular plugin-based system supporting both *local DUT tests* and *remote auto-detected devices* via SSH.

* Visualization Engine: Plotly-powered charts with Streamlit frontend deliver real-time interactive dashboards (pie, bar, scatter, trend).

* Standalone Builds: PyInstaller support for portable distribution across Windows/Linux with embedded DB and plugins.

* Queue Orchestration: Intelligent job scheduling with per-DUT queue management and automatic transition from queued → running → completed.

* Remote Execution Layer: SSH-based command dispatch for remote auto-detect devices, with username/password authentication.

* Extensible Test Plugins: Dynamic discovery of test scripts (local/remote) with hot-plug capability via the `plugins/` directory.

* Session-State Aware UI: Streamlit session state maintains DUT/job context across tabs for seamless user interaction.

* Logging & Traceability: Structured log capture per job in `src/logs/` and detailed test history in DB for auditing.

* Trend Analytics: Historical data aggregation enables iteration-vs-delay correlation plots and long-term pass/fail trend analysis.
_________________________________________________________________________________________________________

**PROJECT STRUCTURE**

Framework/
│
├── src/
│   ├── standalone/
│   │   ├── app.py                # Streamlit UI entry point
│   │   ├── hardware.py           # Local DUT manager (Serial)
│   │   ├── executor.py           # orchestrates the job execution process
│   │   ├── ai_model.py           # RL model for AI parameter suggestions
│   │   ├── database.py           # SQLite DB schema & operations
│   │   └── test_runner.py        # executing individual test scripts
│   │
│   ├── plugins/
│   │   ├── tests/                # Local DUT test plugins (Serial)
│   │   │   ├── cold_boot.py
│   │   │   ├── power_cycle.py
│   │   │   └── ...
│   │   │
│   │   └── auto_detect_tests/    # Remote system test plugins (SSH)
│   │       ├── cpuinformation.py
│   │       ├── memoryinformation.py
│   │       ├── diskinformation.py
│   │       ├── systeminformation.py
│   │       ├── activeprocessinformation.py
│   │       ├── restartTest.py
│   │       └── ...
│   │
│   └── logs/                     # Execution logs
│       └── Job_*.log        
│
├── requirements.txt              # Dependencies
├── framework.db                  # SQLite databas
└── README.md                     # Documentation

_________________________________________________________________________________________________________

**PROJECT WORKFLOW**

The framework orchestrates the entire lifecycle of *test definition → execution → logging → analytics visualization* in four well-defined phases:

1. Initialization Phase
2. Main Tab – Job Lifecycle
   * Serial Connection (Local DUTs)
   * Remote Connection (SSH-based Auto-Detected Devices)
3. Job Queue & Status Management
4. Dashboard Analytics

---

# 1: Initialization Phase

    File: `src/standalone/app.py` (Streamlit entrypoint)

1. App Launch
   
   Navigate to root - Framework

   ```bash
   streamlit run src/standalone/app.py
   ```

2. Core Modules Loaded:

   * `hardware.py` → Detects DUTs (Serial & Remote).
   * `executor.py` → Manages job submission & orchestration.
   * `ai_model.py` → Suggests RL-based parameters.
   * `database.py` → Initializes SQLite schema & tables.
   * `test_runner.py` → Executes tests in isolated subprocess.

3. Database Setup (`framework.db`):

   * `Logs` → Test outcomes & metrics.
   * `DUTStatus` → Tracks device status (`Free`, `Busy`, `Queued`).
   * `JobIDCounter` → Auto-incrementing unique job IDs.

4. Session State Setup:

   * DUT inventory, job status map, queue state all tracked in `st.session_state`.

At this stage, the system is ready with DB + DUT metadata + session state.

---

# 2: Main Tab – Job Lifecycle

The Main Tab provides two operational modes:

---

*Serial Connection (Local DUTs)*

1. User Input via UI:

   * Select DUT (from `hardware.py` discovery).
   * Select test from `plugins/tests/`.
   * Provide iterations + delay (or auto-fill via AI Suggestion).

2. AI Parameter Suggestion (Optional):

   * `app.py` → `ai_model.py.suggest_parameters(dut, test)`
   * Reinforcement Learning returns optimized parameters.

3. Job Submission:

   * `app.py` generates unique `job_id` (via `JobIDCounter`).
   * Checks DUT availability (`DUTStatus`):

     * If Free → Job set to `running`.
     * If Busy → Job enqueued into `job_queue`.

4. Job Execution:

   * `app.py` → `executor.submit_job()`
   * `executor.py`:

     * Packages job metadata (DUT, test, params).
     * Delegates execution → `test_runner.run_test_in_cmd(job)`.
   * `test_runner.py`:

     * Locates plugin in `plugins/tests/`.
     * Builds a temporary runner script.
     * Launches subprocess (`subprocess.Popen`).
     * Captures logs → `src/logs/Job_*.log`.

5. Result Capture & Logging:

   * JSON/heuristic parsing of test result.
   * Logs inserted into `Logs` table.
   * DUT status updated in `DUTStatus`.

---

*Remote Connection (SSH Auto-Detected Devices)*

1. Mode Switch:

   * User select - auto detect device.
   * UI updates → username/password fields shown.
   * Test list switches to `plugins/auto_detect_tests/`.

2. Remote Device Discovery:

   * `hardware.py` enumerates reachable devices.
   * User selects target device.

3. AI Parameter Suggestion:

   * `ai_model.py` considers remote DUT profile + test type.
   * Suggests optimal `{iterations, delay}`.

4. Job Submission:

   * Same lifecycle as Serial (Free → run / Busy → enqueue).

5. Remote Execution Flow:

   * `executor.py`: Establishes SSH session.
   * Transfers/executes plugin from `plugins/auto_detect_tests/`.
   * Examples:

     * `cpuinformation.py` → CPU % usage.
     * `memoryinformation.py` → RAM metrics.
     * `restartTest.py` → remote reboot validation.

6. Result Capture & Logging:

   * Collected results pushed to SQLite `Logs`.
   * Includes remote-specific metadata (hostname, username).

👉 Difference vs Serial: Uses *SSH layer + auto\_detect\_tests plugins* instead of direct Serial plugins.

---

# 3: Job Queue & Status Management

File: `executor.py` + `database.py`

* Queue Handling:

  * If DUT busy → job queued in `DUTStatus.job_queue`.
  * Upon completion → first queued job dequeued & executed.

* Status Lifecycle:

  * `Free → Busy → Completed`
  * Queue transitions handled automatically.

* Session State Sync:

  * `app.py` continuously polls DB + updates `st.session_state.job_status`.

-> Supports *parallel execution across multiple DUTs*, while ensuring *sequential execution per DUT*.

---

# 4: Dashboard Analytics

Files:
`src/standalone/app.py` → Visualization logic + UI
`src/standalone/database.py` → Query helpers & persistence

1. Toggle** → Serial ↔ Remote (top-right)

2. User selects filters & mode in Streamlit UI

3. `app.py` calls **`database.py` query helpers with filter constraints.

4. Data returned → pandas DataFrame → Plotly figures (`px.pie`, `px.bar`, `px.scatter`, `px.line`).

    * Pass / Fail Pie Chart
        * Source: Aggregate outcomes from `Logs` (optionally split by `test_name` or `hardware_type`).

    * Bar Chart (Entities Distribution)
        * Serial Mode**: DUT-wise pass/fail counts (stacked bars per DUT).
        * Remote Mode**: User-wise / Host-wise pass/fail counts (or grouped by username).
        * Source: Grouped counts from `Logs` (`dut`, `username`, or `device`).

    * Iteration vs Delay Scatter Plot
        * Purpose: Visualize clusters that indicate stable vs unstable parameter ranges.
        * Axes: X → iterations, Y → delay.
        * Source: Parsed `Logs.metrics` column (JSON) for `iterations` and `delay`.

    * Trend Graph (Time Series)
        * Features: Time-range control, zoom, rolling averages, event markers.
        * Source: `Logs.timestamp` + outcome, aggregated into time buckets (hour/day/week/month).
        
_________________________________________________________________________________________________________

**USER MANUAL**

Welcome to *TestFrameworkApp*
This guide will walk you through *how to use the framework* in both *Serial Connection (local DUT)* and *Remote Connection (network device)* modes.

---

# Starting the Application

1. Navigate to root - Framework
   
   ```bash
   streamlit run src/standalone/app.py
   ```

2. The app opens in your browser: [http://localhost:8502](http://localhost:8502)

* You will see two tabs:
* *Main Tab* → where you run tests.
* *Dashboard Tab* → where you review and analyze Job results.

---

# A: Serial Connection Mode (Local DUTs)

* Step 1: Select DUT

    * On the *Main Tab*, you will see a list of connected DUTs (Device Under Test).
    * Choose the one you want to test (e.g., DUT1, DUT2).

* Step 2: Understanding DUT Status

    * Free → Ready to accept new jobs.
    * Busy → Currently running or has queued jobs.
    * Jobs auto-queue if DUT is busy.

* Step 3: Choose Test

    * Pick a test script (e.g., `cold_boot`, `power_cycle`).

* Step 4: Configure Parameters

    * Enter values for iterations and delay.
    * OR click AI Suggestion to auto-fill optimal values, courtesy reinforcement learning.

* Step 5: Run Test

    * Press *Run Test*.
    * The DUT will execute the test.
    * If DUT is busy, your job is placed in a queue and runs automatically later.

* Step 6: View Results

    * Switch to *Dashboard Tab*.
    * See:
        * Pass/Fail Pie Charts
        * Bar Charts by Test/User
        * Iteration vs Delay Scatter Plots
        * Trend Graphs (last hours → months)

---

# B: Using Remote Connection Mode (Network Devices)

* Step 1: Enable Remote Mode

    * On the *Main Tab*, select the *Auto detect device* as your DUT.

* Step 2: Select Device

    * Pick any device from listed auto-detected devices.

* Step 3: Login

    * Enter *username* and *password* for the remote system.

* Step 4: Choose Test

    * Select from available remote tests:
        * CPU Information
        * Memory Information
        * Disk Information
        * System Info
        * Active Processes
        * Restart Test

* Step 5: Configure Parameters

    * Enter iterations and delay.
    * OR click AI Suggestion to auto-fill optimal values tailored to provided remote device, courtesy reinforcement learning.

* Step 6: Run Test

    * Click *Run Test*.
    * Test executes on the remote system via SSH.
    * Results are saved in the database.

* Step 7: View Results

    * Go to *Dashboard Tab*.
    * Filter by any combinations of *username* + *test*
    * See:
        * Pass/Fail Pie Charts
        * Bar Charts by Test/User
        * Iteration vs Delay Scatter Plots
        * Trend Graphs (last hours → months)

---

# Tips for Best Use

* Always consider *DUT status* before running a test.
* Use *AI Suggestion* to save time on parameter tuning.
* Regularly explore the *Dashboard Tab* - Trend Graphs for better analysis.
* For remote devices → ensure *network connectivity + SSH access*.

---

# 📌 Quick Reference

* *Main Tab* = Where you run tests.
* *Dashboard Tab* = Where you see results.
* *Serial Mode* = Local DUTs via COM ports.
* *Remote Mode* = Network devices via SSH.
* *AI Suggestion* = Auto-recommended parameters.
______________________________________________________________________________________________________ :)

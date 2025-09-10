# Copyright (c) 2025 Varun Kumar BS.
# This file contains proprietary code and/or utilities for development purposes.

# src/standalone/app.py
import streamlit as st
import json
import os
import time
import sqlite3
import plotly.express as px
import pandas as pd
from hardware import mock_hardware_detection
from ai_model import suggest_parameters
from executor import submit_job
from database import init_db
import plotly.graph_objects as go
from hardware import mock_hardware_detection, auto_detect_network_devices
import sys

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller bundle."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ---------------------- GLOBAL STYLES ----------------------
st.markdown(
    """
    <style>
    body {
        font-family: 'Segoe UI', sans-serif;
        background-color: #0f1116;  /* Dark background */
        color: #f9fafb;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1 {
        font-weight: 700;
        color: #f9fafb;
        text-align: center; /* Centered title */
        text-shadow: 2px 2px 4px rgba(0,0,0,0.6); /* Shadow effect */
        margin-bottom: 1.5rem;
    }
    h2, h3 {
        font-weight: 600;
        color: #f9fafb;
    }
    .stButton > button {
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(255,255,255,0.2);
    }
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
        color: white;
    }
    .status-queued { background-color: #f59e0b; }
    .status-running { background-color: #3b82f6; }
    .status-completed { background-color: #10b981; }
    .info-card, .job-card {
        padding: 1rem;
        border-radius: 12px;
        background-color: #1f2937 !important;
        border: 1px solid #ffffff;
        box-shadow: 0 2px 6px rgba(0,0,0,0.5);
        margin-bottom: 1rem;
        color: #f9fafb;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ---------------------- SESSION STATE ----------------------
if "job_status" not in st.session_state:
    st.session_state.job_status = {}
if "ai_suggestion" not in st.session_state:
    st.session_state.ai_suggestion = None
if "iterations" not in st.session_state:
    st.session_state.iterations = 10
if "delay" not in st.session_state:
    st.session_state.delay = 5
if "dashboard_selection" not in st.session_state:
    st.session_state.dashboard_selection = None
if "selected_hardware_type" not in st.session_state:
    st.session_state.selected_hardware_type = None
if "selected_test_name" not in st.session_state:
    st.session_state.selected_test_name = None
# new session states for auto detect
if "auto_detected_device" not in st.session_state:
    st.session_state.auto_detected_device = None
if "auto_detect_username" not in st.session_state:
    st.session_state.auto_detect_username = None
if "auto_detect_password" not in st.session_state:
    st.session_state.auto_detect_password = None

# Initialize DB
conn = init_db()

# ---------------------- PAGE TITLE ----------------------
st.title("SmartTestFramework")

# ---------------------- TABS ----------------------
main_tab, dashboard_tab = st.tabs(["🖥️ Main", "📊 Dashboard"])

# ---------------------- MAIN TAB ----------------------
with main_tab:
    def update_job_status():
        cursor = conn.execute("SELECT job_id, dut, outcome, metrics FROM Logs")
        completed_jobs = {row[0]: {"dut": row[1], "outcome": row[2], "metrics": json.loads(row[3])} for row in cursor}
        cursor = conn.execute("SELECT dut, status, job_queue FROM DUTStatus")
        for dut, status, job_queue in cursor:
            job_queue = json.loads(job_queue)
            for job_id, info in st.session_state.job_status.items():
                if job_id in completed_jobs and info["dut"] == dut:
                    st.session_state.job_status[job_id]["status"] = "completed"
                    st.session_state.job_status[job_id]["outcome"] = completed_jobs[job_id]["outcome"]
                    st.session_state.job_status[job_id]["metrics"] = completed_jobs[job_id]["metrics"]
            if status == "Busy" and not job_queue:
                for job_id, info in st.session_state.job_status.items():
                    if info["dut"] == dut and info["status"] == "queued":
                        st.session_state.job_status[job_id]["status"] = "running"
                        break
            elif status == "Busy" and job_queue:
                for job_id, info in st.session_state.job_status.items():
                    if info["dut"] == dut and info["status"] == "queued":
                        st.session_state.job_status[job_id]["status"] = "queued"

    # Hardware + DUT selection
    hardware = mock_hardware_detection()
    cursor = conn.execute("SELECT dut, status FROM DUTStatus")
    dut_status = {row[0]: row[1] for row in cursor}
    hardware_options = [f"DUT{h['DUT']} ({dut_status.get(h['DUT'], 'Unknown')})" for h in hardware]
    dut_ids = [h['DUT'] for h in hardware]

    # Append "Auto detect" option
    hardware_options.append("🔍 Auto detect device")

    st.subheader("🔧 DUT & Test Selection")

    selected_hardware_option = st.selectbox("Select DUT", hardware_options)

    # Handle Auto detect flow
    if selected_hardware_option == "🔍 Auto detect device":
        with st.spinner("🔍 Searching for devices in the network..."):
            devices_in_network = auto_detect_network_devices()  # returns list of IPs/hostnames

        if not devices_in_network:
            st.warning("⚠️ No active devices found on the network.")
            selected_dut = None
            selected_hardware_data = None
        else:
            auto_device = st.selectbox(
                "Select Detected Device",
                devices_in_network,
                key="auto_detect_device_select"
            )
            auto_username = st.text_input("Username", key="auto_detect_username")
            auto_password = st.text_input("Password", type="password", key="auto_detect_password")

            if auto_device and auto_username:
                st.markdown(
                    f"""
                    <div class="info-card">
                        <b>Auto-detected DUT</b><br>
                        <small>Device:</small> {auto_device}<br>
                        <small>User:</small> {auto_username}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            selected_dut = "auto"
            # ip: take first token (like "192.168.0.5 (mac)") -> split by space and pick first
            selected_hardware_data = {
                "hardware_type": "auto-detected",
                "serial": "-",
                "com_port": "-",
                "mac_address": "-",
                "ip": (auto_device.split()[0] if auto_device else None),
                "username": auto_username,
                "password": auto_password
            }

            # ✅ Only push IP into session_state (since widgets already manage username/password)
            st.session_state.auto_detected_device = selected_hardware_data["ip"]
            # Note: username/password kept by their widgets' keys

    else:
        # Normal DUT flow
        selected_dut = dut_ids[hardware_options.index(selected_hardware_option)]
        selected_hardware_data = next(h for h in hardware if h["DUT"] == selected_dut)
        st.markdown(
            f"""
            <div class="info-card">
                <b>DUT {selected_dut}</b><br>
                <small>Type:</small> {selected_hardware_data['hardware_type']}<br>
                <small>Serial:</small> {selected_hardware_data['serial']}<br>
                <small>COM Port:</small> {selected_hardware_data['com_port']}<br>
                <small>MAC:</small> {selected_hardware_data['mac_address']}
            </div>
            """,
            unsafe_allow_html=True
        )

    # Select test directory based on DUT type
    if selected_dut == "auto":
        tests_dir = resource_path(os.path.join("src", "plugins", "auto_detect_tests"))
    else:
        tests_dir = resource_path(os.path.join("src", "plugins", "tests"))

    tests = [f[:-3] for f in os.listdir(tests_dir) if f.endswith(".py")]

    if not tests:
        st.error(f"🚫 No test scripts found in {tests_dir}/")
    else:
        selected_test = st.selectbox("Select Test", tests)

    # AI Suggestion + Parameters
    if selected_dut and tests and selected_test:
        st.markdown("### ⚙️ Test Parameters")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✨ AI Suggestion"):
                suggested = suggest_parameters(selected_hardware_data["hardware_type"], selected_test)
                st.session_state.ai_suggestion = suggested
                st.session_state.iterations = suggested["parameters"]["iterations"]
                st.session_state.delay = suggested["parameters"]["delay"]

        if st.session_state.ai_suggestion:
            st.info(
                f"**AI Suggested Parameters:** Iterations={st.session_state.ai_suggestion['parameters']['iterations']}, "
                f"Delay={st.session_state.ai_suggestion['parameters']['delay']} "
                f"(Confidence: {st.session_state.ai_suggestion['confidence']*100:.1f}%)"
            )

        st.number_input("Iterations", min_value=1, key="iterations")
        st.number_input("Delay (seconds)", min_value=1, key="delay")
    else:
        st.number_input("Iterations", min_value=1, value=10, disabled=True, key="iterations")
        st.number_input("Delay (seconds)", min_value=1, value=5, disabled=True, key="delay")

    # Run Test Button
    if st.button("🚀 Run Test", use_container_width=True):
        try:
            # Reserve a job id & show immediate submit notice
            conn.execute("BEGIN TRANSACTION")
            cursor = conn.execute("SELECT next_job_id FROM JobIDCounter WHERE counter_id = 1")
            job_id = cursor.fetchone()[0]
            conn.commit()

            st.session_state.job_status[job_id] = {
                "dut": selected_dut,
                "status": "queued" if dut_status.get(selected_dut) == "Busy" else "running",
                "result": None
            }

            # Show job submission immediately
            st.success(f"✅ Job {job_id} submitted successfully")

            # Build parameters dict, include network creds for auto flow
            params_dict = {
                "iterations": st.session_state.iterations,
                "delay": st.session_state.delay,
            }
            if selected_dut == "auto":
                # prefer values from widgets / session_state
                params_dict["ip"] = st.session_state.get("auto_detected_device") or selected_hardware_data.get("ip")
                params_dict["username"] = st.session_state.get("auto_detect_username") or selected_hardware_data.get("username")
                params_dict["password"] = st.session_state.get("auto_detect_password") or selected_hardware_data.get("password")

            conn.execute("BEGIN TRANSACTION")
            job_result = submit_job(
                conn, selected_dut, selected_hardware_data["hardware_type"], selected_hardware_data["serial"],
                selected_hardware_data["com_port"], selected_hardware_data["mac_address"],
                selected_test, st.session_state.iterations, params_dict
            )
            conn.commit()

            # Save the result (returned by submit_job)
            st.session_state.job_status[job_id]["result"] = job_result

            # If submit_job returned immediate outcome, mark completed; otherwise queue logic will update later
            if job_result and job_result.get("queued") is False:
                st.session_state.job_status[job_id]["status"] = "completed"
            else:
                # queued -> keep it queued/running depending on DB status; update_job_status will sync later
                st.session_state.job_status[job_id]["status"] = "queued"

        except Exception as e:
            conn.rollback()
            st.error(f"Error submitting job: {str(e)}")

    # Job Status
    st.subheader("📋 Job Status")
    update_job_status()
    for job_id, info in st.session_state.job_status.items():
        if info["dut"] == selected_dut:
            badge_class = (
                "status-queued" if info["status"] == "queued"
                else "status-running" if info["status"] == "running"
                else "status-completed"
            )

            status_text = (
                "Queued" if info["status"] == "queued"
                else "Running" if info["status"] == "running"
                else "Completed"
            )

            # Handle result display
            result_text = ""
            if info["status"] == "completed" and info.get("result"):
                if isinstance(info["result"], dict):
                    outcome = info["result"].get("outcome", "")
                    metrics = info["result"].get("metrics", {})
                    result_text = f"<b>Result:</b> {outcome}<br><b>Metrics:</b> {metrics}"
                else:
                    result_text = f"<b>Result:</b> {str(info['result'])}"

            st.markdown(
                f"""
                <div class="job-card">
                    <b>Job {job_id}</b> → DUT {selected_dut}<br>
                    <span class="status-badge {badge_class}">{status_text}</span><br>
                    {result_text}
                </div>
                """,
                unsafe_allow_html=True
            )


# ---------------------- DASHBOARD TAB ----------------------
with dashboard_tab:
    # Create a header row with two columns
    colL, colR = st.columns([2, 1])

    with colL:
        st.subheader("Job History Dashboard")

    with colR:
        remote_mode = st.checkbox("🌐 Remote Device Mode", key="remote_mode")

    # --- rest of your dashboard logic ---
    hardware = mock_hardware_detection()
    hardware_types = sorted(list(set(h["hardware_type"] for h in hardware)))

    tests_dir_local = resource_path(os.path.join("src", "plugins", "tests"))
    test_names_local = sorted([f[:-3] for f in os.listdir(tests_dir_local) if f.endswith(".py")])

    # --- State Management ---
    if "dashboard_selection" not in st.session_state:
        st.session_state.dashboard_selection = None
    if "selected_hardware_type" not in st.session_state:
        st.session_state.selected_hardware_type = None
    if "selected_test_name" not in st.session_state:
        st.session_state.selected_test_name = None

    if remote_mode:
        # Remote Device dashboard -> multi-select username + tests from auto_detect_tests
        st.markdown("### Remote Device Job History")

        # get unique usernames from Logs
        cursor = conn.execute("SELECT DISTINCT username FROM Logs WHERE username IS NOT NULL")
        usernames = [str(row[0]).strip() for row in cursor if row[0]]

        auto_tests_dir = resource_path(os.path.join("src", "plugins", "auto_detect_tests"))
        auto_test_names = sorted([f[:-3] for f in os.listdir(auto_tests_dir) if f.endswith(".py")])

        # Provide "Select All" first option
        user_choice = st.multiselect("Select Usernames", ["Select All"] + usernames, default=["Select All"])
        test_choice = st.multiselect("Select Tests (auto_detect_tests)", ["Select All"] + auto_test_names, default=["Select All"])

        if st.button("Submit Filters", key="remote_submit"):
            # Interpret select-all
            if "Select All" in user_choice or not user_choice:
                sel_users = usernames
            else:
                sel_users = user_choice

            if "Select All" in test_choice or not test_choice:
                sel_tests = auto_test_names
            else:
                sel_tests = test_choice

            if not sel_users:
                st.warning("No usernames available in logs to query.")
                st.stop()

            # Build placeholders for parameterized query (usernames first, then tests)
            placeholders_u = ",".join(["?"] * len(sel_users))
            placeholders_t = ",".join(["?"] * len(sel_tests))

            query = f"""
                SELECT username, test_name, outcome, parameters, timestamp
                FROM Logs
                WHERE username IN ({placeholders_u}) AND test_name IN ({placeholders_t})
            """

            # Correct ordering of params: usernames first, then tests
            params = sel_users + sel_tests
            rows = conn.execute(query, params).fetchall()

            if not rows:
                st.warning("No data found for selected filters.")
                st.stop()

            df = pd.DataFrame(rows, columns=["username", "test_name", "outcome", "parameters", "timestamp"])

            # Normalize usernames -> ensure everything is string (this is critical)
            df["username"] = df["username"].astype(str).str.strip()
            df["username"] = df["username"].replace(["None", "nan", "NaN", ""], "Unknown")

            # === Debug / quick sanity info (helps verify multiple usernames are present) ===
            unique_users = df["username"].unique().tolist()

            # ======================= PIE =======================
            agg_outcome = df.groupby("outcome").size().reset_index(name="count")
            agg_outcome["label"] = agg_outcome.apply(lambda r: f"{r['outcome']} ({r['count']})", axis=1)

            fig_pie = px.pie(
                agg_outcome,
                names="label",
                values="count",
                color="outcome",
                color_discrete_map={
                    "Pass": "#2563eb",  # Blue
                    "Fail": "#eab308"   # Yellow
                },
                title="Pass/Fail Ratio (Remote)"
            )
            fig_pie.update_traces(
                textinfo="percent+value",
                textfont_size=14,
                pull=[0.05 if r["outcome"] == "Fail" else 0 for _, r in agg_outcome.iterrows()]
            )
            fig_pie.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#333"),
                title_font_size=16
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            # ======================= BAR =======================
            # Aggregate by username + outcome
            bar_df = df.groupby(["username", "outcome"]).size().reset_index(name="count")

            # Force username to be a string categorical so Plotly does not treat numeric-like values as numeric axis
            bar_df["username"] = bar_df["username"].astype(str)

            # Use sorted unique usernames for consistent x-axis ordering
            username_order = sorted(bar_df["username"].unique().tolist(), key=lambda x: (str(x)))

            fig_bar = px.bar(
                bar_df.astype({"username": "string"}),   # force username as string
                x="username",
                y="count",
                color="outcome",
                barmode="stack",   # or "group" if you want side-by-side bars
                text="count",
                category_orders={"username": username_order},
                color_discrete_map={"Pass": "#2563eb", "Fail": "#eab308"},
                title="Pass/Fail Count by Username"
            )

            # Force x-axis to categorical (no auto-formatting like k/M suffixes)
            fig_bar.update_xaxes(type="category")


            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(
                xaxis_title="Usernames",
                yaxis_title="Count",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#333"),
                title_font_size=16
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            # ======================= SCATTER (Remote) =======================
            scatter_rows = []
            for _, row in df.iterrows():
                try:
                    p = json.loads(row["parameters"] or "{}")
                    it = p.get("iterations")
                    dl = p.get("delay")
                    if it is not None and dl is not None:
                        scatter_rows.append({"Iterations": it, "Delay": dl, "Outcome": row["outcome"]})
                except Exception:
                    continue

            if scatter_rows:
                scatter_df = pd.DataFrame(scatter_rows)

                # Aggregate counts
                grouped = scatter_df.groupby(["Iterations", "Delay", "Outcome"]).size().reset_index(name="Count")
                totals = grouped.groupby(["Iterations", "Delay"])["Count"].sum().reset_index(name="Total")
                grouped = grouped.merge(totals, on=["Iterations", "Delay"])

                grouped["hover"] = grouped.apply(
                    lambda r: f"Iterations={r['Iterations']}<br>Delay={r['Delay']}<br>{r['Outcome']}: {r['Count']}<br>Total={r['Total']}", axis=1
                )

                # Build figure
                fig_scatter = go.Figure()
                for outcome, color in [("Pass", "#2563eb"), ("Fail", "#eab308")]:
                    sub = grouped[grouped["Outcome"] == outcome]
                    fig_scatter.add_trace(go.Scatter(
                        x=sub["Delay"],
                        y=sub["Iterations"],
                        mode="markers+text",
                        marker=dict(size=12, color=color, opacity=0.7, line=dict(width=1, color="DarkSlateGrey")),
                        text=sub.apply(lambda r: f"x{r['Total']}" if r["Total"] > 1 else "", axis=1),
                        textposition="top center",
                        name=outcome,
                        hovertext=sub["hover"],
                        hoverinfo="text"
                    ))

                fig_scatter.update_layout(
                    title="Iterations-Delay Correlation w/ Result (Remote)",
                    xaxis_title="Delay (seconds)",
                    yaxis_title="Iterations",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#333"),
                    title_font_size=16
                )

                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("No iterations/delay parameters available for selected filters.")

            # ======================= LINE TREND =======================
            trend_rows = []
            for _, row in df.iterrows():
                ts = row["timestamp"]
                if ts:
                    try:
                        trend_rows.append({"Timestamp": pd.to_datetime(ts), "Outcome": row["outcome"]})
                    except Exception:
                        continue
            if trend_rows:
                trend_df = pd.DataFrame(trend_rows)
                trend_counts = trend_df.groupby([pd.Grouper(key="Timestamp", freq="h"), "Outcome"]).size().reset_index(name="Count")
                fig_trend = px.line(
                    trend_counts,
                    x="Timestamp",
                    y="Count",
                    color="Outcome",
                    color_discrete_map={"Pass": "#2563eb", "Fail": "#eab308"},
                    title="Pass/Fail Trend (Remote)"
                )
                fig_trend.update_layout(
                    xaxis=dict(
                        title="Timeline",
                        rangeselector=dict(
                            buttons=list([
                                dict(count=24, label="24h", step="hour", stepmode="backward"),
                                dict(count=7, label="1w", step="day", stepmode="backward"),
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(step="all")
                            ])
                        ),
                        rangeslider=dict(visible=True),
                        type="date"
                    ),
                    yaxis_title="Number of Tests",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#333"),
                    title_font_size=16
                )
                fig_trend.update_traces(mode="lines+markers")
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("No timeline data available for selected filters.")


    else:
        # Existing (local) dashboard behavior (your existing UI)
        # --- Button Row (unique keys to separate from other buttons) ---
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Hardware Type", key="dashboard_hardware_btn"):
                st.session_state.dashboard_selection = "hardware"
                st.session_state.selected_test_name = None
        with col2:
            if st.button("Test Name", key="dashboard_test_btn"):
                st.session_state.dashboard_selection = "test"
                st.session_state.selected_hardware_type = None

        # --- Dropdown + Button Highlight after Selection ---
        hardware_selected, test_selected = None, None
        if st.session_state.dashboard_selection == "hardware":
            hardware_selected = st.selectbox(
                "Select Hardware Type",
                ["Select Hardware", "All"] + hardware_types,
                key="hardware_dropdown"
            )
            if hardware_selected != "Select Hardware":
                st.session_state.selected_hardware_type = hardware_selected
                st.session_state.selected_test_name = None

        elif st.session_state.dashboard_selection == "test":
            test_selected = st.selectbox(
                "Select Test Name",
                ["Select Test", "All"] + test_names_local,
                key="test_dropdown"
            )
            if test_selected != "Select Test":
                st.session_state.selected_test_name = test_selected
                st.session_state.selected_hardware_type = None

        # --- Scoped CSS for Dashboard Buttons Only ---
        st.markdown(
            f"""
            <style>
            /* Default button look (only dashboard buttons) */
            div[data-testid="stHorizontalBlock"] div[data-testid="column"]:first-child button {{
                background-color: #262730; /* dark neutral */
                color: white;
            }}
            div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(2) button {{
                background-color: #262730;
                color: white;
            }}
            /* Highlight Hardware button if dropdown has valid selection */
            div[data-testid="stHorizontalBlock"] div[data-testid="column"]:first-child button {{
                background-color: {"#f43f5e" if st.session_state.selected_hardware_type else "#262730"};
                color: {"white" if st.session_state.selected_hardware_type else "white"};
            }}
            /* Highlight Test button if dropdown has valid selection */
            div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(2) button {{
                background-color: {"#f43f5e" if st.session_state.selected_test_name else "#262730"};
                color: {"white" if st.session_state.selected_test_name else "white"};
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        modern_colors = {
            "Pass": "#10b981",  # Emerald
            "Fail": "#f43f5e"   # Rose
        }

        # --- Graph Rendering After Selection ---
        if st.session_state.selected_hardware_type or st.session_state.selected_test_name:
            if st.session_state.selected_hardware_type:
                if st.session_state.selected_hardware_type == "All":
                    cursor = conn.execute(
                        "SELECT dut, outcome, COUNT(*) FROM Logs WHERE hardware_type != 'auto-detected' GROUP BY dut, outcome"
                    )
                    title_suffix = "All Hardware Types"
                    duts = [h["DUT"] for h in hardware if h["hardware_type"] != "auto-detected"]
                else:
                    cursor = conn.execute(
                        "SELECT dut, outcome, COUNT(*) FROM Logs WHERE hardware_type = ? GROUP BY dut, outcome",
                        (st.session_state.selected_hardware_type,)
                    )
                    title_suffix = st.session_state.selected_hardware_type
                    duts = [h["DUT"] for h in hardware if h["hardware_type"] == st.session_state.selected_hardware_type]
                data = cursor.fetchall()

            else:  # test selected
                if st.session_state.selected_test_name == "All":
                    cursor = conn.execute(
                        "SELECT dut, outcome, COUNT(*) FROM Logs WHERE hardware_type != 'auto-detected' GROUP BY dut, outcome"
                    )
                    title_suffix = "All Tests"
                    duts = [h["DUT"] for h in hardware if h["hardware_type"] != "auto-detected"]
                else:
                    cursor = conn.execute(
                        "SELECT dut, outcome, COUNT(*) FROM Logs WHERE test_name = ? GROUP BY dut, outcome",
                        (st.session_state.selected_test_name,)
                    )
                    title_suffix = st.session_state.selected_test_name
                    duts = [h["DUT"] for h in hardware]
                data = cursor.fetchall()


            # ---- If No Data: Show Card, Stop Rendering ----
            if not data:
                st.error(f"No jobs available for {title_suffix}")
                st.stop()

            # ======================= PIE + BAR =======================
            df = pd.DataFrame(data, columns=["dut", "outcome", "count"])
            df["DUT"] = df["dut"].apply(lambda x: f"DUT {x}")

            outcome_counts = df.groupby("outcome")["count"].sum().to_dict()
            outcome_labels = {o: f"{o} ({outcome_counts.get(o, 0)})" for o in outcome_counts.keys()}

            # ---- PIE CHART ----
            with st.spinner("Rendering Pass/Fail Ratio..."):
                time.sleep(0.3)
                fig_pie = px.pie(
                    df,
                    names=df["outcome"].map(outcome_labels),
                    values="count",
                    color=df["outcome"].map(outcome_labels),
                    color_discrete_map={
                        outcome_labels.get("Pass", "Pass"): "#10B981",
                        outcome_labels.get("Fail", "Fail"): "#EF4444"
                    },
                    title=f"Pass/Fail Ratio for {title_suffix}"
                )
                fig_pie.update_traces(
                    textinfo="percent+value",
                    textfont_size=14,
                    pull=[0.05 if "Fail" in lbl else 0 for lbl in df["outcome"].map(outcome_labels)]
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            # ---- BAR CHART ----
            with st.spinner("Rendering Pass/Fail Count by DUT..."):
                time.sleep(0.3)
                fig_bar = px.bar(
                    df,
                    x="DUT",
                    y="count",
                    color=df["outcome"].map(outcome_labels),
                    color_discrete_map={
                        outcome_labels.get("Pass", "Pass"): "#10B981",
                        outcome_labels.get("Fail", "Fail"): "#EF4444"
                    },
                    barmode="stack",
                    text="count",
                    title=f"Pass/Fail Count by DUT for {title_suffix}"
                )
                fig_bar.update_traces(textposition="outside")
                fig_bar.update_layout(
                    xaxis_title="DUT",
                    yaxis_title="Count",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#333"),
                    title_font_size=16
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            # ======================= SCATTER + TREND =======================
            if st.session_state.selected_hardware_type:
                if st.session_state.selected_hardware_type == "All":
                    cursor = conn.execute(
                        "SELECT job_id, dut, parameters, outcome, timestamp "
                        "FROM Logs WHERE hardware_type != 'auto-detected'"
                    )
                else:
                    cursor = conn.execute(
                        "SELECT job_id, dut, parameters, outcome, timestamp "
                        "FROM Logs WHERE hardware_type = ?",
                        (st.session_state.selected_hardware_type,)
                    )
            else:
                if st.session_state.selected_test_name == "All":
                    cursor = conn.execute(
                        "SELECT job_id, dut, parameters, outcome, timestamp "
                        "FROM Logs WHERE hardware_type != 'auto-detected'"
                    )
                else:
                    cursor = conn.execute(
                        "SELECT job_id, dut, parameters, outcome, timestamp "
                        "FROM Logs WHERE test_name = ?",
                        (st.session_state.selected_test_name,)
                    )


            scatter_rows = cursor.fetchall()
            if not scatter_rows:
                st.error(f"No jobs available for {title_suffix}")
                st.stop()

            scatter_data, trend_data = [], []
            for job_id, dut, params, outcome, ts in scatter_rows:
                try:
                    params_dict = json.loads(params)
                    iterations = params_dict.get("iterations")
                    delay = params_dict.get("delay")
                    if iterations is not None and delay is not None:
                        scatter_data.append({
                            "Job ID": job_id,
                            "DUT": f"DUT {dut}",
                            "Iterations": iterations,
                            "Delay": delay,
                            "Outcome": outcome
                        })
                    if ts:
                        trend_data.append({"Timestamp": pd.to_datetime(ts), "Outcome": outcome})
                except Exception:
                    continue

            # ---- SCATTER PLOT ----
            if scatter_data:
                with st.spinner("Rendering Iterations vs Delay..."):
                    time.sleep(0.3)
                    scatter_df = pd.DataFrame(scatter_data)

                    # Aggregate counts by (Iterations, Delay, Outcome)
                    grouped = scatter_df.groupby(["Iterations", "Delay", "Outcome"]).size().reset_index(name="Count")

                    # Also get total counts per point (Iterations, Delay)
                    totals = grouped.groupby(["Iterations", "Delay"])["Count"].sum().reset_index(name="Total")

                    # Merge totals to grouped
                    grouped = grouped.merge(totals, on=["Iterations", "Delay"])

                    # Add hover text
                    grouped["hover"] = grouped.apply(
                        lambda r: f"Iterations={r['Iterations']}<br>Delay={r['Delay']}<br>{r['Outcome']}: {r['Count']}<br>Total={r['Total']}", axis=1
                    )

                    # Base scatter
                    fig_scatter = go.Figure()

                    for outcome, color in [("Pass", "#10B981"), ("Fail", "#EF4444")]:
                        sub = grouped[grouped["Outcome"] == outcome]
                        fig_scatter.add_trace(go.Scatter(
                            x=sub["Delay"],
                            y=sub["Iterations"],
                            mode="markers+text",
                            marker=dict(size=12, color=color, opacity=0.7, line=dict(width=1, color="DarkSlateGrey")),
                            text=sub.apply(lambda r: f"x{r['Total']}" if r["Total"] > 1 else "", axis=1),
                            textposition="top center",
                            name=outcome,
                            hovertext=sub["hover"],
                            hoverinfo="text"
                        ))

                    fig_scatter.update_layout(
                        title=f"Iterations-Delay Correlation w/ Result for {title_suffix}",
                        xaxis_title="Delay (seconds)",
                        yaxis_title="Iterations",
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#333"),
                        title_font_size=16
                    )

                    st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info(f"No iteration/delay data available for {title_suffix}")

            # ---- TREND GRAPH ----
            if trend_data:
                with st.spinner("Rendering Pass/Fail Trend..."):
                    time.sleep(0.3)
                    trend_df = pd.DataFrame(trend_data)
                    trend_counts = trend_df.groupby([pd.Grouper(key="Timestamp", freq="h"), "Outcome"]).size().reset_index(name="Count")

                    fig_trend = px.line(
                        trend_counts,
                        x="Timestamp",
                        y="Count",
                        color="Outcome",
                        color_discrete_map={
                            "Pass": "#10B981",
                            "Fail": "#EF4444"
                        },
                        title=f"Pass/Fail Trend over Time for {title_suffix}"
                    )
                    fig_trend.update_traces(mode="lines+markers")
                    fig_trend.update_layout(
                        xaxis=dict(
                            title="Timeline",
                            rangeselector=dict(
                                buttons=list([
                                    dict(count=24, label="24h", step="hour", stepmode="backward"),
                                    dict(count=7, label="1w", step="day", stepmode="backward"),
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(step="all")
                                ])
                            ),
                            rangeslider=dict(visible=True),
                            type="date"
                        ),
                        yaxis_title="Number of Tests",
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#333"),
                        title_font_size=16
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)

            else:
                st.error(f"No timeline data available for {title_suffix}")



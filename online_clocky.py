"""Streamlit-based Time Tracker (online version) - Independent app

Upper section: editable table of recorded tasks.
Lower section: dashboard summary and controls (Start/Stop timer, Set hourly rate, Export CSV).

This is a separate app with independent data storage from the Tkinter desktop version.

Usage: run `streamlit run online_clocky.py` in the `KoalaLiteLaundry` folder.
"""

import os
import json
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

TIME_RECORDS_FILE = "online_time_records.csv"
CONFIG_FILE = "online_config.json"

DEFAULT_CONFIG = {"hourly_rate": 300.0}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)


def load_records():
    if not os.path.exists(TIME_RECORDS_FILE):
        return pd.DataFrame(columns=["project", "task", "start", "end", "duration", "billable", "hours", "amount"])
    df = pd.read_csv(TIME_RECORDS_FILE)
    return df


def save_records(df: pd.DataFrame):
    df.to_csv(TIME_RECORDS_FILE, index=False)


def format_hms(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"


st.set_page_config(page_title="Online Time Tracker", layout="wide")

cfg = load_config()

if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "project" not in st.session_state:
    st.session_state.project = ""
if "task" not in st.session_state:
    st.session_state.task = ""
if "billable" not in st.session_state:
    st.session_state.billable = True


def start_timer():
    if not st.session_state.project.strip() or not st.session_state.task.strip():
        st.warning("Enter project and task before starting the timer.")
        return
    st.session_state.timer_running = True
    st.session_state.start_time = datetime.now().isoformat(sep=" ")


def stop_timer():
    if not st.session_state.timer_running or not st.session_state.start_time:
        return
    st.session_state.timer_running = False
    start = datetime.fromisoformat(st.session_state.start_time)
    end = datetime.now()
    duration = end - start
    hours = duration.total_seconds() / 3600.0
    amount = hours * cfg.get("hourly_rate", DEFAULT_CONFIG["hourly_rate"]) if st.session_state.billable else 0.0

    rec = {
        "project": st.session_state.project.strip(),
        "task": st.session_state.task.strip(),
        "start": start.isoformat(sep=" "),
        "end": end.isoformat(sep=" "),
        "duration": str(duration).split(".")[0],
        "billable": st.session_state.billable,
        "hours": round(hours, 3),
        "amount": round(amount, 2),
    }

    df = load_records()
    df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True, sort=False)
    save_records(df)
    st.success("Recorded time entry.")
    # Reset input fields
    st.session_state.project = ""
    st.session_state.task = ""
    st.session_state.start_time = None


def main():
    st.title("🕒 Online Time Tracker")

    # Upper section: Records table
    st.header("Recorded Tasks")
    df = load_records()
    # show editable table
    edited = st.data_editor(df, num_rows="dynamic", use_container_width='stretch')
    if st.button("Save Table Edits"):
        # ensure typed columns are correct
        try:
            edited["hours"] = pd.to_numeric(edited["hours"], errors="coerce").fillna(0.0)
            edited["amount"] = pd.to_numeric(edited["amount"], errors="coerce").fillna(0.0)
            save_records(edited)
            st.success("Table saved to CSV.")
        except Exception as e:
            st.error(f"Failed to save table: {e}")

    st.markdown("---")

    # Lower section: Dashboard and controls
    col1, col2 = st.columns([3, 1])

    with col1:
        st.header("Dashboard")
        df = load_records()
        if df.empty:
            st.info("No records yet.")
        else:
            df["start"] = pd.to_datetime(df["start"])
            df["hours"] = pd.to_numeric(df["hours"], errors="coerce").fillna(0.0)
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

            now = datetime.now()
            seven_days_ago = now - timedelta(days=6)
            last_7 = df[df["start"] >= pd.Timestamp(seven_days_ago)]
            total_hours = last_7["hours"].sum()
            total_amount = last_7["amount"].sum()

            week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            this_week = df[df["start"] >= pd.Timestamp(week_start)]
            per_project = this_week.groupby("project")[["hours", "amount"]].sum() if not this_week.empty else pd.DataFrame()

            st.markdown(f"**Last 7 days** — Hours: {total_hours:.3f}, Amount: ${total_amount:.2f}")
            st.markdown("**This week's totals by project:**")
            if not per_project.empty:
                st.table(per_project)
            else:
                st.write("No records this week.")

            st.markdown("**Most recent records**")
            recent = df.sort_values("start", ascending=False).head(10)
            st.dataframe(recent)

    with col2:
        st.header("Controls")
        
        # Get previous project and task names
        df_hist = load_records()
        prev_projects = [""] + sorted(df_hist["project"].unique().tolist()) if not df_hist.empty else [""]
        prev_tasks = [""] + sorted(df_hist["task"].unique().tolist()) if not df_hist.empty else [""]
        
        # Project selector
        selected_project = st.selectbox("Select or type Project", prev_projects, key="project_select")
        if selected_project:
            st.session_state.project = selected_project
        else:
            st.session_state.project = st.text_input("Or enter new Project", key="project_input", value=st.session_state.project)
        
        # Task selector
        selected_task = st.selectbox("Select or type Task", prev_tasks, key="task_select")
        if selected_task:
            st.session_state.task = selected_task
        else:
            st.session_state.task = st.text_input("Or enter new Task", key="task_input", value=st.session_state.task)
        
        st.checkbox("Billable", key="billable")

        # Timer display
        if st.session_state.timer_running and st.session_state.start_time:
            start = datetime.fromisoformat(st.session_state.start_time)
            elapsed = datetime.now() - start
            secs = int(elapsed.total_seconds())
            st.markdown(f"**Timer:** {format_hms(secs)}")
            if st.button("Stop Timer"):
                stop_timer()
                st.rerun()
        else:
            st.markdown("**Timer:** 00:00:00")
            if st.button("Start Timer"):
                if st.session_state.project and st.session_state.task:
                    st.session_state.timer_running = True
                    st.session_state.start_time = datetime.now().isoformat(sep=" ")
                    st.rerun()
                else:
                    st.warning("Enter project and task first.")

        st.markdown("---")
        st.write(f"Hourly rate: ${cfg.get('hourly_rate', DEFAULT_CONFIG['hourly_rate']):.2f}/hr")
        new_rate = st.number_input("Set hourly rate ($)", value=cfg.get("hourly_rate", DEFAULT_CONFIG["hourly_rate"]), min_value=0.0, step=10.0)
        if new_rate != cfg.get("hourly_rate", DEFAULT_CONFIG["hourly_rate"]):
            cfg["hourly_rate"] = float(new_rate)
            save_config(cfg)

        st.markdown("---")
        # Export
        csv_bytes = load_records().to_csv(index=False).encode("utf-8")
        st.download_button("Export CSV", data=csv_bytes, file_name="online_time_records.csv", mime="text/csv")


if __name__ == "__main__":
    main()

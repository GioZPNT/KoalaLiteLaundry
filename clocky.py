"""Simple Tkinter Time Tracker

- Tracks start/stop time per project/task
- Saves records to CSV
- Shows an editable table of records
- Shows weekly summary and totals in the dashboard
- Lets user set a global hourly rate (stored in config.json)
"""

import json
import os
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import pandas as pd

TIME_RECORDS_FILE = "time_records.csv"
CONFIG_FILE = "config.json"

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


class TimeTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Time Tracker")
        self.root.geometry("900x600")

        self.config = load_config()

        # State
        self.project_var = tk.StringVar()
        self.task_var = tk.StringVar()
        self.billable_var = tk.BooleanVar(value=True)
        self.timer_running = False
        self.start_time = None
        self.current_item_id = None

        # Build UI
        self.create_widgets()
        self.load_records()
        self.update_dashboard()

    def create_widgets(self):
        # Top controls
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=8)

        ttk.Label(top_frame, text="Project:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top_frame, textvariable=self.project_var, width=30).grid(row=0, column=1, padx=6)

        ttk.Label(top_frame, text="Task:").grid(row=0, column=2, sticky="w")
        ttk.Entry(top_frame, textvariable=self.task_var, width=30).grid(row=0, column=3, padx=6)

        ttk.Checkbutton(top_frame, text="Billable", variable=self.billable_var).grid(row=0, column=4, padx=6)

        self.timer_label = ttk.Label(top_frame, text="00:00:00", font=("Helvetica", 18))
        self.timer_label.grid(row=0, column=5, padx=10)

        self.start_stop_button = ttk.Button(top_frame, text="Start", command=self.toggle_timer)
        self.start_stop_button.grid(row=0, column=6, padx=6)

        ttk.Button(top_frame, text="Set Hourly Rate", command=self.set_hourly_rate).grid(row=0, column=7, padx=6)
        self.rate_label = ttk.Label(top_frame, text=f"Rate: ${self.config['hourly_rate']:.2f}/hr")
        self.rate_label.grid(row=0, column=8, padx=6)

        # Main Panes (vertical split: upper = table, lower = dashboard + actions)
        main_pane = ttk.Panedwindow(self.root, orient=tk.VERTICAL)
        main_pane.pack(fill="both", expand=True, padx=10, pady=8)

        # Upper: Records table
        table_frame = ttk.Frame(main_pane)
        main_pane.add(table_frame, weight=3)

        self.tree = ttk.Treeview(table_frame, columns=("project", "task", "start", "end", "duration", "billable", "hours", "amount"), show="headings", selectmode="browse")
        for col, text in [("project", "Project"), ("task", "Task"), ("start", "Start"), ("end", "End"), ("duration", "Duration"), ("billable", "Billable"), ("hours", "Hours"), ("amount", "Amount")]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=110, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        # Vertical scrollbar
        vscrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vscrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vscrollbar.set)

        # Horizontal scrollbar
        hscrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        hscrollbar.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=hscrollbar.set)

        # Configure grid weights
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Lower: Dashboard and action buttons
        lower_frame = ttk.Frame(main_pane)
        main_pane.add(lower_frame, weight=1)

        # Dashboard (left side of lower frame)
        dashboard_frame = ttk.Frame(lower_frame)
        dashboard_frame.pack(side="left", fill="both", expand=True)

        ttk.Label(dashboard_frame, text="Dashboard", font=("Helvetica", 14, "bold")).pack(anchor="w")
        self.dashboard_text = tk.Text(dashboard_frame, height=8, width=40)
        self.dashboard_text.pack(fill="both", expand=True)
        ttk.Button(dashboard_frame, text="Refresh Dashboard", command=self.update_dashboard).pack(pady=6)

        # Actions (right side of lower frame)
        action_frame = ttk.Frame(lower_frame)
        action_frame.pack(side="right", fill="y", padx=10, pady=6)

        ttk.Button(action_frame, text="Edit Selected", command=self.edit_selected, width=18).pack(pady=4)
        ttk.Button(action_frame, text="Delete Selected", command=self.delete_selected, width=18).pack(pady=4)
        ttk.Button(action_frame, text="Export CSV", command=self.export_csv, width=18).pack(pady=4)
        ttk.Separator(action_frame, orient="horizontal").pack(fill="x", pady=6)
        ttk.Label(action_frame, text=f"Rate: ${self.config['hourly_rate']:.2f}/hr").pack(pady=2)
        ttk.Button(action_frame, text="Set Hourly Rate", command=self.set_hourly_rate, width=18).pack(pady=2)

    # Timer control
    def toggle_timer(self):
        if self.timer_running:
            self.stop_timer()
        else:
            self.start_timer()

    def start_timer(self):
        if not self.project_var.get().strip() or not self.task_var.get().strip():
            messagebox.showwarning("Missing Information", "Please enter a project and task before starting the timer.")
            return
        self.timer_running = True
        self.start_time = datetime.now()
        self.start_stop_button.config(text="Stop")
        self.update_timer()

    def stop_timer(self):
        if not self.timer_running:
            return
        self.timer_running = False
        end_time = datetime.now()
        duration = end_time - self.start_time
        hours = duration.total_seconds() / 3600.0
        amount = hours * self.config.get("hourly_rate", DEFAULT_CONFIG["hourly_rate"]) if self.billable_var.get() else 0.0

        start_str = self.start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        record = {
            "project": self.project_var.get().strip(),
            "task": self.task_var.get().strip(),
            "start": start_str,
            "end": end_str,
            "duration": str(duration).split(".")[0],
            "billable": str(self.billable_var.get()),
            "hours": f"{hours:.3f}",
            "amount": f"{amount:.2f}"
        }
        self.add_record(record)
        self.save_records()
        self.start_stop_button.config(text="Start")
        self.timer_label.config(text="00:00:00")

    def update_timer(self):
        if not self.timer_running:
            return
        elapsed = datetime.now() - self.start_time
        # Format as HH:MM:SS
        total_seconds = int(elapsed.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        self.timer_label.config(text=f"{hours:02}:{minutes:02}:{seconds:02}")
        self.root.after(1000, self.update_timer)

    # Records management
    def add_record(self, record):
        # Format times to show HH:MM:SS only in display
        start_parts = record["start"].split(" ") if record["start"] else ["", "00:00:00"]
        end_parts = record["end"].split(" ") if record["end"] else ["", "00:00:00"]
        start_display = start_parts[1] if len(start_parts) > 1 else "00:00:00"
        end_display = end_parts[1] if len(end_parts) > 1 else "00:00:00"
        
        values = (record["project"], record["task"], start_display, end_display, record["duration"], record["billable"], record["hours"], record["amount"])
        # Use index from dataframe as row ID
        idx = len(self.tree.get_children())
        self.tree.insert("", "end", iid=f"row{idx}", values=values)

    def load_records(self):
        if not os.path.exists(TIME_RECORDS_FILE):
            return
        try:
            # Check if file is empty or contains only whitespace
            with open(TIME_RECORDS_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return  # File is empty, nothing to load
            df = pd.read_csv(TIME_RECORDS_FILE)
            for idx, row in df.iterrows():
                rec = {
                    "project": row.get("project", ""),
                    "task": row.get("task", ""),
                    "start": row.get("start", ""),
                    "end": row.get("end", ""),
                    "duration": row.get("duration", ""),
                    "billable": str(row.get("billable", "False")),
                    "hours": f"{row.get('hours', 0):.3f}",
                    "amount": f"{row.get('amount', 0):.2f}"
                }
                self.add_record(rec)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load records: {e}")

    def save_records(self):
        # write all records from tree to CSV
        rows = []
        df_orig = pd.DataFrame()  # Default to empty dataframe
        
        if os.path.exists(TIME_RECORDS_FILE):
            try:
                # Check if file is empty or contains only whitespace
                with open(TIME_RECORDS_FILE, 'r') as f:
                    content = f.read().strip()
                    if content:
                        df_orig = pd.read_csv(TIME_RECORDS_FILE)
            except Exception:
                pass  # If reading fails, use empty dataframe
        
        for idx, iid in enumerate(self.tree.get_children()):
            vals = self.tree.item(iid, "values")
            # Get original full datetime from CSV
            orig_start, orig_end = vals[2], vals[3]
            if not df_orig.empty and idx < len(df_orig):
                orig_start = df_orig.iloc[idx]["start"]
                orig_end = df_orig.iloc[idx]["end"]
            
            row = {
                "project": vals[0],
                "task": vals[1],
                "start": orig_start,
                "end": orig_end,
                "duration": vals[4],
                "billable": vals[5],
                "hours": float(vals[6]),
                "amount": float(vals[7])
            }
            rows.append(row)
        
        try:
            df = pd.DataFrame(rows)
            df.to_csv(TIME_RECORDS_FILE, index=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save records: {e}")

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Edit", "Please select a record to edit.")
            return
        self.edit_record(sel[0])

    def edit_record(self, item_id):
        item = self.tree.item(item_id)
        vals = item["values"]
        
        # Get row index and original datetime from CSV
        row_idx = int(item_id.replace("row", ""))
        df_orig = pd.read_csv(TIME_RECORDS_FILE) if os.path.exists(TIME_RECORDS_FILE) else pd.DataFrame()
        full_start = vals[2]
        full_end = vals[3]
        if not df_orig.empty and row_idx < len(df_orig):
            full_start = df_orig.iloc[row_idx]["start"]
            full_end = df_orig.iloc[row_idx]["end"]
        
        # Ensure full_start and full_end have date+time format
        # If only time is available, prepend today's date
        today = datetime.now().strftime("%Y-%m-%d")
        if len(full_start) <= 8:  # Only time portion (HH:MM:SS)
            full_start = f"{today} {full_start}"
        if len(full_end) <= 8:  # Only time portion (HH:MM:SS)
            full_end = f"{today} {full_end}"
        
        edit_win = tk.Toplevel(self.root)
        edit_win.title("Edit Record")

        tk.Label(edit_win, text="Project:").grid(row=0, column=0, sticky="w")
        proj = tk.Entry(edit_win)
        proj.insert(0, vals[0])
        proj.grid(row=0, column=1, padx=6, pady=4)

        tk.Label(edit_win, text="Task:").grid(row=1, column=0, sticky="w")
        task = tk.Entry(edit_win)
        task.insert(0, vals[1])
        task.grid(row=1, column=1, padx=6, pady=4)

        tk.Label(edit_win, text="Start (YYYY-MM-DD HH:MM:SS):").grid(row=2, column=0, sticky="w")
        start_e = tk.Entry(edit_win, width=30)
        start_e.insert(0, full_start)
        start_e.grid(row=2, column=1, padx=6, pady=4)

        tk.Label(edit_win, text="End (YYYY-MM-DD HH:MM:SS):").grid(row=3, column=0, sticky="w")
        end_e = tk.Entry(edit_win, width=30)
        end_e.insert(0, full_end)
        end_e.grid(row=3, column=1, padx=6, pady=4)

        bill = tk.BooleanVar(value=(vals[5] == 'True'))
        tk.Checkbutton(edit_win, text="Billable", variable=bill).grid(row=4, columnspan=2, pady=4)

        def save():
            try:
                s = datetime.strptime(start_e.get(), "%Y-%m-%d %H:%M:%S")
                e = datetime.strptime(end_e.get(), "%Y-%m-%d %H:%M:%S")
                dur = e - s
                hours = dur.total_seconds() / 3600.0
                amount = hours * self.config.get("hourly_rate", DEFAULT_CONFIG["hourly_rate"]) if bill.get() else 0.0
                start_display = start_e.get().split(" ")[1]
                end_display = end_e.get().split(" ")[1]
                self.tree.item(item_id, values=(proj.get().strip(), task.get().strip(), start_display, end_display, str(dur).split('.')[0], str(bill.get()), f"{hours:.3f}", f"{amount:.2f}"))
                self.save_records()
                edit_win.destroy()
                self.update_dashboard()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save changes: {e}")

        ttk.Button(edit_win, text="Save", command=save).grid(row=5, column=0, columnspan=2, pady=8)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "Please select a record to delete.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected record(s)?"):
            return
        for iid in sel:
            self.tree.delete(iid)
        self.save_records()
        self.update_dashboard()

    def export_csv(self):
        # just re-save to file and notify where
        self.save_records()
        messagebox.showinfo("Export", f"Saved to {os.path.abspath(TIME_RECORDS_FILE)}")

    def set_hourly_rate(self):
        val = simpledialog.askfloat("Hourly Rate", "Set hourly rate ($):", initialvalue=self.config.get("hourly_rate", DEFAULT_CONFIG["hourly_rate"]))
        if val is None:
            return
        self.config["hourly_rate"] = float(val)
        save_config(self.config)
        self.rate_label.config(text=f"Rate: ${self.config['hourly_rate']:.2f}/hr")
        self.update_dashboard()

    def update_dashboard(self):
        # Read CSV and summarize last 7 days and current week
        if not os.path.exists(TIME_RECORDS_FILE):
            self.dashboard_text.delete("1.0", tk.END)
            self.dashboard_text.insert(tk.END, "No records yet.")
            return
        try:
            # Check if file is empty or contains only whitespace
            with open(TIME_RECORDS_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    self.dashboard_text.delete("1.0", tk.END)
                    self.dashboard_text.insert(tk.END, "No records yet.")
                    return
            
            df = pd.read_csv(TIME_RECORDS_FILE, parse_dates=["start", "end"])
            # Ensure proper typing
            df["hours"] = pd.to_numeric(df["hours"], errors="coerce").fillna(0.0)
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

            now = datetime.now()
            seven_days_ago = now - timedelta(days=6)
            last_7 = df[df["start"] >= pd.Timestamp(seven_days_ago)]
            total_hours = last_7["hours"].sum()
            total_amount = last_7["amount"].sum()

            # Weekly per project
            week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            this_week = df[df["start"] >= pd.Timestamp(week_start)]
            per_project = this_week.groupby("project")[["hours", "amount"]].sum() if not this_week.empty else pd.DataFrame()

            text = []
            text.append(f"Last 7 days — Hours: {total_hours:.3f}, Amount: ${total_amount:.2f}\n")
            text.append("This week's totals by project:\n")
            if not per_project.empty:
                for proj, row in per_project.iterrows():
                    text.append(f" - {proj}: {row['hours']:.3f} hrs, ${row['amount']:.2f}\n")
            else:
                text.append(" No records this week.\n")

            # Show most recent records
            text.append('\nMost recent records:\n')
            recent = df.sort_values("start", ascending=False).head(10)
            for _, r in recent.iterrows():
                s = pd.to_datetime(r["start"]).strftime("%Y-%m-%d %H:%M") if not pd.isnull(r["start"]) else r["start"]
                text.append(f"{s} — {r['project']} / {r['task']} — {r['hours']:.3f} hrs — ${r['amount']:.2f}\n")

            self.dashboard_text.delete("1.0", tk.END)
            self.dashboard_text.insert(tk.END, "".join(text))
        except Exception as e:
            self.dashboard_text.delete("1.0", tk.END)
            self.dashboard_text.insert(tk.END, f"Failed to compute dashboard: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = TimeTrackerApp(root)
    root.mainloop()
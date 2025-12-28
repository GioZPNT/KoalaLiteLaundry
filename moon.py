import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Koala Management System", layout="wide")

# --- GLOBAL CONSTANTS & CONFIG ---
ADMIN_PASSWORD = "Moonshine88"  # Password for the Admin Section
TIERS = {"Tier 1 (₱125)": 125, "Tier 2 (₱150)": 150}

# Define all file paths
FILES = {
    "sales": "sales.csv",
    "employees": "payroll_employees.csv",
    "dtr": "payroll_dtr.csv",
    "leaves": "payroll_leaves.csv"
}

# --- DATABASE INITIALIZATION ---
def init_all_dbs():
    # 1. Sales DB
    if not os.path.exists(FILES["sales"]):
        df = pd.DataFrame(columns=[
            "Order_ID", "Date", "Customer", "Contact", "Tier", "Garment_Type", 
            "Loads", "Additionals", "Misc_Amount", "Amount", "Payment_Type", 
            "Payment_Status", "Work_Status", "Notes"
        ])
        df.to_csv(FILES["sales"], index=False)
    
    # 2. Employee DB
    if not os.path.exists(FILES["employees"]):
        df = pd.DataFrame(columns=[
            "Employee_ID", "Name", "Position", "Start_Date", "Status",
            "Daily_Rate", "Hourly_Rate", "OT_Rate", "Holiday_Rate"
        ])
        df.to_csv(FILES["employees"], index=False)
    
    # 3. DTR DB
    if not os.path.exists(FILES["dtr"]):
        df = pd.DataFrame(columns=[
            "Date", "Employee_ID", "Name", "Time_In", "Time_Out", 
            "Reg_Hours", "OT_Hours", "Is_Holiday", "Notes"
        ])
        df.to_csv(FILES["dtr"], index=False)

    # 4. Leaves DB
    if not os.path.exists(FILES["leaves"]):
        df = pd.DataFrame(columns=["Employee_ID", "Name", "Leave_Date", "Type", "Status"])
        df.to_csv(FILES["leaves"], index=False)

init_all_dbs()

# --- HELPER FUNCTIONS ---
def load_csv(key):
    # General loader
    return pd.read_csv(FILES[key], dtype=str).fillna("")

def load_sales_data():
    # Specific loader for sales
    df = pd.read_csv(FILES["sales"], dtype={"Notes": str, "Contact": str, "Order_ID": str, "Work_Status": str, "Payment_Status": str})
    df["Notes"] = df["Notes"].fillna("")
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    return df

def save_csv(key, df):
    df.to_csv(FILES[key], index=False)

def calculate_tenure(start_date_str):
    try:
        start = pd.to_datetime(start_date_str).date()
        today = date.today()
        delta = today - start
        years = delta.days // 365
        months = (delta.days % 365) // 30
        return f"{years} yrs, {months} mos"
    except:
        return "N/A"

# --- MAIN NAVIGATION ---
st.sidebar.title("🐨 Koala System")
app_mode = st.sidebar.radio("Select Department:", ["🛒 Sales Monitoring", "🔐 Admin & Payroll"])

# Embedded dashboard mode: render the Koala operations dashboard inside the Sales Monitoring page
if app_mode == "🛒 Sales Monitoring":
    st.title("📊 Sales Monitoring")
    st.info("Embedded Sales Dashboard")
    try:
        import koala_dashboard
        koala_dashboard.render_dashboard()
    except Exception as e:
        st.error(f"Failed to load embedded dashboard: {e}")
        st.write("You can also run the standalone dashboard: `streamlit run koala_dashboard.py`")
    # Prevent further page logic from executing for this mode
    st.stop()

# Sales & Orders section removed in favor of Sales Monitoring dashboard

# =========================================================
# SECTION 2: ADMIN & PAYROLL (Password Protected)
# =========================================================
elif app_mode == "🔐 Admin & Payroll":
    # --- ADMIN LOGIN LOGIC ---
    if "admin_unlocked" not in st.session_state:
        st.session_state.admin_unlocked = False

    if not st.session_state.admin_unlocked:
        st.title("🔐 Admin Access Required")
        pwd = st.text_input("Enter Admin Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_unlocked = True
                st.rerun()
            else:
                st.error("Incorrect Password")
    else:
        # --- ADMIN INTERFACE (Unlocked) ---
        if st.sidebar.button("🔒 Lock Admin"):
            st.session_state.admin_unlocked = False
            st.rerun()

        st.title("🐨 Koala Payroll Manager")

        tab_emp, tab_dtr, tab_pay, tab_leave = st.tabs([
            "👥 Employee List", "⏱️ Daily Time Record", "💰 Pay Summary", "📅 Leaves"
        ])

        # --- ADMIN: EMPLOYEES ---
        with tab_emp:
            st.subheader("Employee Registry")

            # Add Employee Form (separate block)
            with st.expander("➕ Add New Employee"):
                with st.form("add_emp"):
                    c1, c2 = st.columns(2)
                    name = c1.text_input("Full Name")
                    pos = c2.text_input("Position")
                    start_date = c1.date_input("Start Date")
                    status = c2.selectbox("Status", ["Probationary", "Regular", "Contractual"])

                    st.divider()
                    st.caption("Rates")
                    r1, r2, r3, r4 = st.columns(4)
                    daily = r1.number_input("Daily Rate (₱)", min_value=0.0)
                    hourly = r2.number_input("Hourly (Auto)", value=(daily/8) if daily > 0 else 0.0)
                    ot_rate = r3.number_input("OT Rate", value=1.25)
                    hol_rate = r4.number_input("Hol Rate", value=2.0)

                    if st.form_submit_button("Save Employee"):
                        if not name:
                            st.error("⚠️ Name is required.")
                        else:
                            emp_df = load_csv("employees")
                            new_id = f"EMP-{len(emp_df) + 1:03d}"
                            new_data = pd.DataFrame([{
                                "Employee_ID": new_id, "Name": name, "Position": pos,
                                "Start_Date": start_date, "Status": status,
                                "Daily_Rate": daily, "Hourly_Rate": hourly,
                                "OT_Rate": ot_rate, "Holiday_Rate": hol_rate
                            }])
                            save_csv("employees", pd.concat([emp_df, new_data], ignore_index=True))
                            st.success(f"✅ Added {name}")
                            st.rerun()

            st.divider()
            st.subheader("📝 Employee Registry (Editable)")
            emp_df = load_csv("employees")
            if not emp_df.empty:
                emp_df["Tenure"] = emp_df["Start_Date"].apply(calculate_tenure)
                num_cols = ["Daily_Rate", "Hourly_Rate", "OT_Rate", "Holiday_Rate"]
                for c in num_cols:
                    emp_df[c] = pd.to_numeric(emp_df[c], errors='coerce')

                edited_emp_df = st.data_editor(
                    emp_df,
                    width='stretch',
                    hide_index=True,
                    num_rows="dynamic",
                    disabled=["Employee_ID", "Tenure"],
                    key="emp_editor"
                )

                if st.button("💾 Save Registry Changes"):
                    to_save = edited_emp_df.copy()
                    if "Tenure" in to_save.columns:
                        to_save = to_save.drop(columns=["Tenure"])
                    # Ensure dates are saved as ISO strings to preserve format
                    if "Start_Date" in to_save.columns:
                        to_save["Start_Date"] = pd.to_datetime(to_save["Start_Date"]).dt.date
                    save_csv("employees", to_save)
                    st.success("✅ Employee Registry updated!")
                    st.rerun()

        # --- ADMIN: DTR ---
        with tab_dtr:
            st.subheader("Log Work Hours")
            
            emp_df = load_csv("employees")
            if emp_df.empty:
                st.warning("Add employees first.")
            else:
                c1, c2 = st.columns([1, 2])
                with c1:
                    with st.form("admin_dtr_form"):
                        dtr_date = st.date_input("Date", date.today())
                        emp_list = [f"{r['Name']} ({r['Employee_ID']})" for _, r in emp_df.iterrows()]
                        sel_emp = st.selectbox("Employee", emp_list)
                        sel_name = sel_emp.split(" (")[0]
                        sel_id = sel_emp.split(" (")[1].replace(")", "")
                        
                        t_in = st.time_input("In", value=datetime.strptime("08:00", "%H:%M").time())
                        t_out = st.time_input("Out", value=datetime.strptime("17:00", "%H:%M").time())
                        is_hol = st.checkbox("Holiday?")
                        notes = st.text_input("Notes")
                        
                        if st.form_submit_button("Log Time"):
                            # Check Dupes
                            dtr_check = load_csv("dtr")
                            dtr_check["Date"] = dtr_check["Date"].astype(str)
                            if not dtr_check[(dtr_check["Employee_ID"] == sel_id) & (dtr_check["Date"] == str(dtr_date))].empty:
                                st.error("Log already exists.")
                            else:
                                dt_in = datetime.combine(date(2000,1,1), t_in)
                                dt_out = datetime.combine(date(2000,1,1), t_out)
                                hrs = (dt_out - dt_in).total_seconds() / 3600
                                if hrs > 5: hrs -= 1
                                reg = min(hrs, 8.0)
                                ot = max(hrs - 8.0, 0.0)
                                
                                new_log = pd.DataFrame([{
                                    "Date": dtr_date, "Employee_ID": sel_id, "Name": sel_name,
                                    "Time_In": t_in, "Time_Out": t_out, "Reg_Hours": reg,
                                    "OT_Hours": ot, "Is_Holiday": is_hol, "Notes": notes
                                }])
                                # Let user edit the new entry before saving
                                edited_log = st.data_editor(new_log, width='stretch', hide_index=True)
                                # Use the edited result as the new_log to be saved
                                new_log = edited_log
                                save_csv("dtr", pd.concat([load_csv("dtr"), new_log], ignore_index=True))
                                st.success("Logged!")
                                st.rerun()

                with c2:
                    dtr_df = load_csv("dtr")
                    if not dtr_df.empty:
                        dtr_df["Date"] = pd.to_datetime(dtr_df["Date"]).dt.date
                        edited_dtr = st.data_editor(dtr_df.sort_values("Date", ascending=False), num_rows="dynamic", width='stretch', hide_index=True)
                        if st.button("💾 Save Logs"):
                            save_csv("dtr", edited_dtr)
                            st.success("Saved!")
import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- CONFIGURATION ---
st.set_page_config(page_title="Koala Ledger Payroll", layout="wide")

FILES = {
    "employees": "payroll_employees.csv",
    "dtr": "payroll_dtr.csv",
    "leaves": "payroll_leaves.csv"
}

# --- DATABASE INITIALIZATION ---
def init_db():
    # 1. Employee File
    if not os.path.exists(FILES["employees"]):
        df = pd.DataFrame(columns=[
            "Employee_ID", "Name", "Position", "Start_Date", "Status",
            "Daily_Rate", "Hourly_Rate", "OT_Rate", "Holiday_Rate"
        ])
        df.to_csv(FILES["employees"], index=False)
    
    # 2. Daily Time Record (DTR) File
    if not os.path.exists(FILES["dtr"]):
        df = pd.DataFrame(columns=[
            "Date", "Employee_ID", "Name", "Time_In", "Time_Out", 
            "Reg_Hours", "OT_Hours", "Is_Holiday", "Notes"
        ])
        df.to_csv(FILES["dtr"], index=False)

    # 3. Leaves File
    if not os.path.exists(FILES["leaves"]):
        df = pd.DataFrame(columns=["Employee_ID", "Name", "Leave_Date", "Type", "Status"])
        df.to_csv(FILES["leaves"], index=False)

init_db()

# --- HELPER FUNCTIONS ---
def load_csv(key):
    return pd.read_csv(FILES[key])

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

# --- MAIN APP ---
st.title("🐨 Koala Ledger: Payroll Manager")

# Tabs for the 4 main features
tab_emp, tab_dtr, tab_pay, tab_leave = st.tabs([
    "👥 Employee List", "⏱️ Daily Time Record", "💰 Pay Summary", "📅 Leaves & Schedule"
])

# ==========================================
# 1. EMPLOYEE LIST
# ==========================================
with tab_emp:
    st.subheader("Employee Registry")
    
    with st.expander("➕ Add New Employee"):
        with st.form("add_emp"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Full Name")
            pos = c2.text_input("Position")
            start_date = c1.date_input("Start Date")
            status = c2.selectbox("Status", ["Probationary", "Regular", "Contractual"])
            
            st.divider()
            st.caption("Compensation Rates")
            r1, r2, r3, r4 = st.columns(4)
            daily = r1.number_input("Daily Rate (₱)", min_value=0.0)
            # Auto-calculate hourly (Standard: Daily / 8)
            hourly = r2.number_input("Hourly Rate (₱)", min_value=0.0, value=daily/8 if daily > 0 else 0.0)
            ot_rate = r3.number_input("OT Rate (Multiplier)", value=1.25, help="Usually 1.25 for Regular Days")
            hol_rate = r4.number_input("Holiday Rate (Multiplier)", value=2.0, help="2.0 for Regular Holiday, 1.3 for Special")

            if st.form_submit_button("Save Employee"):
                emp_df = load_csv("employees")
                new_id = f"EMP-{len(emp_df) + 1:03d}"
                new_data = pd.DataFrame([{
                    "Employee_ID": new_id, "Name": name, "Position": pos,
                    "Start_Date": start_date, "Status": status,
                    "Daily_Rate": daily, "Hourly_Rate": hourly,
                    "OT_Rate": ot_rate, "Holiday_Rate": hol_rate
                }])
                save_csv("employees", pd.concat([emp_df, new_data], ignore_index=True))
                st.success(f"Added {name}!")
                st.rerun()

    # Display Table with Tenure
    emp_df = load_csv("employees")
    if not emp_df.empty:
        # Calculate tenure for display only
        display_df = emp_df.copy()
        display_df["Tenure"] = display_df["Start_Date"].apply(calculate_tenure)
        st.dataframe(
            display_df, 
            column_order=["Employee_ID", "Name", "Position", "Status", "Tenure", "Daily_Rate", "Hourly_Rate"],
            width='stretch', hide_index=True
        )
    else:
        st.info("No employees found.")

# ==========================================
# 2. DAILY TIME RECORD (DTR)
# ==========================================
with tab_dtr:
    st.subheader("Log Work Hours")
    emp_df = load_csv("employees")
    
    if emp_df.empty:
        st.warning("Please add employees first.")
    else:
        c1, c2 = st.columns([1, 2])
        
        # --- LEFT COLUMN: NEW ENTRY FORM ---
        with c1:
            with st.form("dtr_form"):
                dtr_date = st.date_input("Date", date.today())
                
                # Map Name to ID
                emp_display = [f"{row['Name']} ({row['Employee_ID']})" for i, row in emp_df.iterrows()]
                selected_emp_str = st.selectbox("Select Employee", emp_display)
                
                # Extract ID and Name
                sel_name = selected_emp_str.split(" (")[0]
                sel_id = selected_emp_str.split(" (")[1].replace(")", "")

                t_in = st.time_input("Time In", value=datetime.strptime("08:00", "%H:%M").time())
                t_out = st.time_input("Time Out", value=datetime.strptime("17:00", "%H:%M").time())
                
                is_hol = st.checkbox("Is this a Holiday?")
                notes = st.text_input("Notes")
                
                if st.form_submit_button("Log Time"):
                    # Calculate Hours
                    dummy_date = date(2000, 1, 1)
                    dt_in = datetime.combine(dummy_date, t_in)
                    dt_out = datetime.combine(dummy_date, t_out)
                    
                    total_hours = (dt_out - dt_in).total_seconds() / 3600
                    
                    # Auto-deduct 1 hour break if worked more than 5 hours
                    if total_hours > 5:
                        total_hours -= 1
                    
                    # OT Calculation (After 8 hours)
                    reg_hours = min(total_hours, 8.0)
                    ot_hours = max(total_hours - 8.0, 0.0)
                    
                    dtr_entry = pd.DataFrame([{
                        "Date": dtr_date, "Employee_ID": sel_id, "Name": sel_name,
                        "Time_In": t_in, "Time_Out": t_out,
                        "Reg_Hours": reg_hours, "OT_Hours": ot_hours,
                        "Is_Holiday": is_hol, "Notes": notes
                    }])
                    save_csv("dtr", pd.concat([load_csv("dtr"), dtr_entry], ignore_index=True))
                    st.success(f"Logged {total_hours} hrs for {sel_name}")
                    st.rerun()

        # --- RIGHT COLUMN: EDITABLE LOGS ---
        with c2:
            st.caption("Recent Logs (Editable - Double click to change)")
            dtr_df = load_csv("dtr")
            if not dtr_df.empty:
                # Ensure Date is datetime for sorting, but keep as string/date for editing if preferred
                dtr_df["Date"] = pd.to_datetime(dtr_df["Date"]).dt.date
                dtr_sorted = dtr_df.sort_values("Date", ascending=False)
                
                # Make the dataframe editable
                edited_dtr = st.data_editor(
                    dtr_sorted,
                    width='stretch',
                    hide_index=True,
                    num_rows="dynamic", # Allows adding/deleting rows directly in table
                    key="dtr_editor"
                )

                # Save changes if the edited dataframe is different from the original
                # Note: st.data_editor automatically updates session state, but we need to save to CSV
                # We add a save button to confirm changes to disk to avoid constant re-writing on every keystroke
                if st.button("💾 Save Changes to Logs"):
                    # Convert dates back to string format for consistent CSV storage if needed
                    save_csv("dtr", edited_dtr)
                    st.success("DTR Logs updated successfully!")

# ==========================================
# 3. PAY SUMMARY (Payslip)
# ==========================================
with tab_pay:
    st.subheader("Payroll Generation")
    
    # Filter by Date Range
    c1, c2 = st.columns(2)
    start_pay = c1.date_input("Start Period")
    end_pay = c2.date_input("End Period")
    
    if st.button("Generate Payroll Summary"):
        dtr_df = load_csv("dtr")
        emp_df = load_csv("employees")
        
        # Filter DTR
        dtr_df["Date"] = pd.to_datetime(dtr_df["Date"]).dt.date
        mask = (dtr_df["Date"] >= start_pay) & (dtr_df["Date"] <= end_pay)
        period_dtr = dtr_df.loc[mask]
        
        if period_dtr.empty:
            st.warning("No logs found for this period.")
        else:
            # Merge with Rate info
            merged = pd.merge(period_dtr, emp_df, on="Employee_ID", how="left", suffixes=("", "_ref"))
            
            # CALCULATIONS
            # 1. Base Pay = Reg Hours * Hourly Rate
            # 2. OT Pay = OT Hours * Hourly Rate * OT_Rate
            # 3. Holiday Premium logic (Simplified: If Holiday, Reg Hours * (HolRate - 1) is added bonus)
            
            merged["Base_Pay"] = merged["Reg_Hours"] * merged["Hourly_Rate"]
            merged["OT_Pay"] = merged["OT_Hours"] * merged["Hourly_Rate"] * merged["OT_Rate"]
            
            # If Is_Holiday is True, apply multiplier to Base Pay
            # Logic: If holiday, rate is usually double (2.0). 
            # We already paid 1.0 in Base Pay, so we add the extra (Rate - 1.0)
            merged["Holiday_Premium"] = merged.apply(
                lambda x: (x["Reg_Hours"] * x["Hourly_Rate"] * (x["Holiday_Rate"] - 1.0)) if x["Is_Holiday"] else 0, axis=1
            )
            
            merged["Total_Daily_Pay"] = merged["Base_Pay"] + merged["OT_Pay"] + merged["Holiday_Premium"]
            
            # Group by Employee
            payroll_summary = merged.groupby(["Employee_ID", "Name"]).agg(
                Total_Reg_Hours=('Reg_Hours', 'sum'),
                Total_OT_Hours=('OT_Hours', 'sum'),
                Total_Base_Pay=('Base_Pay', 'sum'),
                Total_OT_Pay=('OT_Pay', 'sum'),
                Total_Hol_Pay=('Holiday_Premium', 'sum'),
                Grand_Total=('Total_Daily_Pay', 'sum')
            ).reset_index()
            
            st.success("Calculation Complete!")
            st.dataframe(payroll_summary, width='stretch')
            
            # --- GOOGLE SHEETS EXPORT OPTION ---
            st.divider()
            st.markdown("### 📄 Export for Google Sheets")
            st.caption("Download this CSV and import it into your Google Sheets Payslip Template.")
            
            csv = payroll_summary.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Payslip Data (CSV)",
                data=csv,
                file_name=f"Payroll_{start_pay}_{end_pay}.csv",
                mime="text/csv"
            )

# ==========================================
# 4. LEAVE MANAGEMENT
# ==========================================
with tab_leave:
    st.subheader("Leave & Schedule")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("leave_form"):
            emp_df = load_csv("employees")
            if not emp_df.empty:
                leave_emp = st.selectbox("Employee", emp_df["Name"].unique())
                leave_date = st.date_input("Leave Date")
                l_type = st.selectbox("Type", ["Sick Leave", "Vacation Leave", "Emergency"])
                
                if st.form_submit_button("File Leave"):
                    # Get ID
                    e_id = emp_df[emp_df["Name"] == leave_emp].iloc[0]["Employee_ID"]
                    
                    new_leave = pd.DataFrame([{
                        "Employee_ID": e_id, "Name": leave_emp, 
                        "Leave_Date": leave_date, "Type": l_type, "Status": "Approved"
                    }])
                    save_csv("leaves", pd.concat([load_csv("leaves"), new_leave], ignore_index=True))
                    st.success("Leave Filed!")
    
    with c2:
        st.caption("Scheduled Leaves")
        leaves_df = load_csv("leaves")
        if not leaves_df.empty:
            leaves_df["Leave_Date"] = pd.to_datetime(leaves_df["Leave_Date"])
            st.dataframe(leaves_df.sort_values("Leave_Date"), width='stretch', hide_index=True)

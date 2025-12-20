import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- SECURITY CONFIG ---
ACCESS_PASSWORD = "Koala2025"

# --- CONFIGURATION ---
st.set_page_config(page_title="Koala Insite", layout="wide")

# 1. UPDATE: Add new files to the configuration
FILES = {
    "sales": "sales.csv",
    "employees": "payroll_employees.csv", # New
    "dtr": "payroll_dtr.csv"             # New
}

TIERS = {"Tier 1 (₱125)": 125, "Tier 2 (₱150)": 150}

# --- LOGIN LOGIC ---
def check_password():
    def password_entered():
        if st.session_state["password"] == ACCESS_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🧺 Koala Management System")
        st.text_input("Enter Shop Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🧺 Koala Management System")
        st.text_input("Enter Shop Password", type="password", on_change=password_entered, key="password")
        st.error("❌ Access Denied")
        return False
    return True

if check_password():
    if st.sidebar.button("Log Out"):
        st.session_state["password_correct"] = False
        st.rerun()

    # 2. UPDATE: Update database initialization to create new files
    def init_db():
        # Sales DB
        if not os.path.exists(FILES["sales"]):
            df = pd.DataFrame(columns=[
                "Order_ID", "Date", "Customer", "Contact", "Tier", "Garment_Type", 
                "Loads", "Additionals", "Misc_Amount", "Amount", "Payment_Type", 
                "Payment_Status", "Work_Status", "Notes"
            ])
            df.to_csv(FILES["sales"], index=False)
        
        # Employee DB (Required for DTR)
        if not os.path.exists(FILES["employees"]):
            # Minimal columns needed for DTR to work
            df = pd.DataFrame(columns=["Employee_ID", "Name", "Position", "Status"])
            df.to_csv(FILES["employees"], index=False)

        # DTR DB
        if not os.path.exists(FILES["dtr"]):
            df = pd.DataFrame(columns=[
                "Date", "Employee_ID", "Name", "Time_In", "Time_Out", 
                "Reg_Hours", "OT_Hours", "Is_Holiday", "Notes"
            ])
            df.to_csv(FILES["dtr"], index=False)

    init_db()

    # --- HELPER FUNCTIONS ---
    def load_data(): # Keeps existing logic for Sales
        df = pd.read_csv(FILES["sales"], dtype={"Notes": str, "Contact": str, "Order_ID": str, "Work_Status": str, "Payment_Status": str})
        df["Notes"] = df["Notes"].fillna("")
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        return df

    def save_data(df): # Keeps existing logic for Sales
        df.to_csv(FILES["sales"], index=False)

    # 3. UPDATE: Add generic CSV helpers for the new module
    def load_csv(key):
        return pd.read_csv(FILES[key])

    def save_csv(key, df):
        df.to_csv(FILES[key], index=False)

    # --- NAVIGATION ---
    st.sidebar.title("🧺 Koala Insite")
    # 4. UPDATE: Add "Staff Timekeeping" to the menu
    menu = st.sidebar.selectbox("Go to Page:", ["Dashboard", "New Sale", "Manage Orders", "Staff Timekeeping"])

    # --- MODULES ---

    # 1. DASHBOARD (Existing)
    if menu == "Dashboard":
        # ... (Keep your existing Dashboard code here) ...
        # (For brevity, I'm assuming the existing dashboard code remains unchanged)
        st.title("📊 Business Performance")
        sales_df = load_data()
        if not sales_df.empty:
            today_val = date.today()
            today_sales = sales_df[sales_df["Date"] == today_val]["Amount"].sum()
            unpaid_total = sales_df[sales_df["Payment_Status"] == "Unpaid"]["Amount"].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Sales Today", f"₱{today_sales:,.2f}")
            c2.metric("Unpaid Receivables", f"₱{unpaid_total:,.2f}")
            c3.metric("WIP Jobs", len(sales_df[sales_df["Work_Status"] == "WIP"]))
        else:
            st.info("No records found yet.")

    # 2. NEW SALE (Existing)
    elif menu == "New Sale":
        # ... (Keep your existing New Sale code here) ...
        st.title("💰 Create New Job Order")
        # (Paste your existing New Sale logic here)

    # 3. MANAGE ORDERS (Existing)
    elif menu == "Manage Orders":
        # ... (Keep your existing Manage Orders code here) ...
        st.title("📋 Job Order Management")
        # (Paste your existing Manage Orders logic here)

    # 4. NEW FEATURE: STAFF TIMEKEEPING (DTR)
    elif menu == "Staff Timekeeping":
        st.title("⏱️ Staff Timekeeping (DTR)")
        
        # Note: We removed 'with tab_dtr:' because this is now a main page, not a tab.
        st.subheader("Log Work Hours")
        emp_df = load_csv("employees")
        
        if emp_df.empty:
            st.warning("⚠️ No employees found. Please add employees to 'payroll_employees.csv' manually or via the Admin module.")
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
                    # Ensure Date is datetime for sorting
                    dtr_df["Date"] = pd.to_datetime(dtr_df["Date"]).dt.date
                    dtr_sorted = dtr_df.sort_values("Date", ascending=False)
                    
                    # Make the dataframe editable
                    edited_dtr = st.data_editor(
                        dtr_sorted,
                        use_container_width=True,
                        hide_index=True,
                        num_rows="dynamic", # Allows adding/deleting rows directly in table
                        key="dtr_editor"
                    )

                    # Save changes logic
                    if st.button("💾 Save Changes to Logs"):
                        save_csv("dtr", edited_dtr)
                        st.success("DTR Logs updated successfully!")

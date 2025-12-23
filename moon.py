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
app_mode = st.sidebar.radio("Select Department:", ["🛒 Sales & Orders", "🔐 Admin & Payroll"])

# =========================================================
# SECTION 1: SALES & ORDERS (Public/Staff Access)
# =========================================================
if app_mode == "🛒 Sales & Orders":
    # 1. UPDATE: Added "Staff Timekeeping" to the dropdown
    menu = st.sidebar.selectbox("Sales Menu:", ["Dashboard", "New Sale", "Manage Orders", "Staff Timekeeping"])
    
    # --- SALES: DASHBOARD ---
    if menu == "Dashboard":
        st.title("📊 Sales Dashboard")
        sales_df = load_sales_data()
        
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

    # --- SALES: NEW SALE ---
    elif menu == "New Sale":
        st.title("💰 Create New Job Order")

        # Success Message
        if "last_success_msg" in st.session_state and st.session_state.last_success_msg:
            st.success(st.session_state.last_success_msg)
            del st.session_state.last_success_msg

        # Reset Logic
        if "form_key" not in st.session_state:
            st.session_state.form_key = 0
        
        if st.button("🔄 Reset Form"):
            st.session_state.form_key += 1
            st.rerun()

        # The Form
        with st.form("order_form", clear_on_submit=False):
            st.subheader("👤 Customer & Service")
            k = st.session_state.form_key
            
            col1, col2 = st.columns(2)
            with col1:
                cust_name = st.text_input("Customer Name", key=f"cust_name_{k}")
                contact = st.text_input("Contact Number", key=f"contact_{k}")
                selected_tier = st.selectbox("Pricing Tier", list(TIERS.keys()), key=f"tier_{k}")
                garment = st.selectbox("Garment Type", ["Regular", "Semi-Heavy", "Heavy"], key=f"garment_{k}")
            with col2:
                loads = st.number_input("Loads", min_value=1, step=1, key=f"loads_{k}")
                open_amt = st.number_input("Misc / Open Amount (₱)", min_value=0.0, key=f"open_{k}")
                pay_type = st.radio("Payment", ["Cash", "GCash"], horizontal=True, key=f"ptype_{k}")
                pay_status = st.radio("Status", ["Unpaid", "Paid"], horizontal=True, key=f"pstat_{k}")

            st.divider()
            st.subheader("🧴 Add-ons (Supplies)")
            c1, c2 = st.columns(2)
            with c1:
                det_brand = st.text_input("Brand", placeholder="Detergent (e.g. Ariel)", key=f"d_brand_{k}")
                det_price = st.number_input("Amount (₱)", min_value=0.0, step=5.0, key=f"d_price_{k}")
            with c2:
                fab_brand = st.text_input("Brand", placeholder="FabCon (e.g. Downy)", key=f"f_brand_{k}")
                fab_price = st.number_input("Amount (₱)", min_value=0.0, step=5.0, key=f"f_price_{k}")

            st.divider()
            notes = st.text_area("Notes / Remarks", key=f"notes_{k}")
            work_status = st.select_slider("Work Status", options=["WIP", "Ready", "Claimed"], key=f"ws_{k}")

            # Calculations
            base_price = float(TIERS[selected_tier] * loads)
            supplies_total = float(det_price) + float(fab_price)
            grand_total = base_price + supplies_total + float(open_amt)

            st.markdown(f"### Total Amount: ₱{grand_total:,.2f}")
            
            c_act1, c_act2 = st.columns(2)
            update_click = c_act1.form_submit_button("🔄 Update Total", type="secondary", use_container_width=True)
            confirm_click = c_act2.form_submit_button("✅ Confirm Order", type="primary", use_container_width=True)

            if confirm_click:
                if not cust_name:
                    st.error("⚠️ Customer Name is required.")
                else:
                    supplies_str = []
                    if det_price > 0 or det_brand: supplies_str.append(f"Det: {det_brand} (₱{det_price})")
                    if fab_price > 0 or fab_brand: supplies_str.append(f"Fab: {fab_brand} (₱{fab_price})")
                    supplies_final = ", ".join(supplies_str) if supplies_str else "None"

                    new_entry = pd.DataFrame([{
                        "Order_ID": datetime.now().strftime("%y%m%d-%H%M%S"),
                        "Date": date.today(), "Customer": cust_name, "Contact": str(contact),
                        "Tier": selected_tier, "Garment_Type": garment, "Loads": loads,
                        "Additionals": supplies_total, "Misc_Amount": open_amt, "Amount": grand_total,
                        "Payment_Type": pay_type, "Payment_Status": pay_status, "Work_Status": work_status,
                        "Notes": f"{supplies_final} | {notes}"
                    }])
                    
                    save_csv("sales", pd.concat([load_sales_data(), new_entry], ignore_index=True))
                    st.session_state.last_success_msg = f"✅ Saved! {cust_name} (Total: ₱{grand_total:,.2f})"
                    st.session_state.form_key += 1
                    st.rerun()

    # --- SALES: MANAGE ORDERS ---
    elif menu == "Manage Orders":
        st.title("📋 Manage Orders")
        sales_df = load_sales_data()
        
        if not sales_df.empty:
            st.subheader("🔍 Fetch & Actions")
            order_to_fetch = st.text_input("Enter Order ID (e.g., 231219-1200)")
            
            if order_to_fetch:
                fetched_job = sales_df[sales_df["Order_ID"] == order_to_fetch]
                if not fetched_job.empty:
                    st.info(f"Order: **{fetched_job.iloc[0]['Customer']}**")
                    tab_up, tab_del = st.tabs(["Update", "Delete"])
                    
                    with tab_up:
                        with st.form("up_form"):
                            c1, c2, c3 = st.columns(3)
                            curr_work = fetched_job.iloc[0]["Work_Status"]
                            curr_pay = fetched_job.iloc[0]["Payment_Status"]
                            curr_type = fetched_job.iloc[0]["Payment_Type"]
                            
                            nw = c1.selectbox("Work", ["WIP", "Ready", "Claimed"], index=["WIP", "Ready", "Claimed"].index(curr_work) if curr_work in ["WIP", "Ready", "Claimed"] else 0)
                            np = c2.selectbox("Payment", ["Paid", "Unpaid"], index=["Paid", "Unpaid"].index(curr_pay) if curr_pay in ["Paid", "Unpaid"] else 0)
                            nt = c3.selectbox("Type", ["Cash", "GCash"], index=["Cash", "GCash"].index(curr_type) if curr_type in ["Cash", "GCash"] else 0)
                            nn = st.text_area("Notes", value=fetched_job.iloc[0]["Notes"])
                            
                            if st.form_submit_button("Save"):
                                sales_df.loc[sales_df["Order_ID"] == order_to_fetch, ["Work_Status", "Payment_Status", "Payment_Type", "Notes"]] = [nw, np, nt, str(nn)]
                                save_csv("sales", sales_df)
                                st.success("Updated!")
                                st.rerun()
                    
                    with tab_del:
                        if st.checkbox("Confirm Delete"):
                            if st.button("Delete Permanently"):
                                save_csv("sales", sales_df[sales_df["Order_ID"] != order_to_fetch])
                                st.error("Deleted.")
                                st.rerun()

            st.divider()
            st.subheader("📝 Bulk Editor")
            edited_df = st.data_editor(sales_df, use_container_width=True, hide_index=True, disabled=["Order_ID", "Date", "Customer", "Amount"])
            if st.button("Save Bulk Changes"):
                save_csv("sales", edited_df)
                st.success("Saved!")
                st.rerun()

    # --- 2. UPDATE: ADDED STAFF TIMEKEEPING BLOCK HERE ---
    elif menu == "Staff Timekeeping":
        st.title("⏱️ Staff Timekeeping (DTR)")
        
        st.subheader("Log Work Hours")
        emp_df = load_csv("employees")
        
        if emp_df.empty:
            st.warning("Please add employees first.")
        else:
            c1, c2 = st.columns([1, 2])
            
            with c1:
                with st.form("dtr_form"):
                    dtr_date = st.date_input("Date", date.today())
                    # specific_emp = st.selectbox("Employee", emp_df["Name"].tolist())
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

            with c2:
                st.caption("Recent Logs")
                dtr_df = load_csv("dtr")
                if not dtr_df.empty:
                    # Sort by date desc
                    dtr_df["Date"] = pd.to_datetime(dtr_df["Date"])
                    st.dataframe(dtr_df.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)

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
            
            # --- SUCCESS MESSAGE LOGIC ---
            # Check if a success message exists from the previous run
            if "emp_success" in st.session_state and st.session_state.emp_success:
                st.success(st.session_state.emp_success)
                del st.session_state.emp_success  # Clear message so it doesn't stay forever

            with st.expander("➕ Add New Employee"):
                # Added clear_on_submit=True so fields reset after adding
                with st.form("add_emp", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    name = c1.text_input("Full Name")
                    pos = c2.text_input("Position")
                    start_date = c1.date_input("Start Date")
                    status = c2.selectbox("Status", ["Probationary", "Regular", "Contractual"])
                    
                    st.divider()
                    st.caption("Rates")
                    r1, r2, r3, r4 = st.columns(4)
                    daily = r1.number_input("Daily Rate (₱)", min_value=0.0)
                    hourly = r2.number_input("Hourly (Auto)", value=daily/8 if daily > 0 else 0.0)
                    ot_rate = r3.number_input("OT Rate", value=1.25)
                    hol_rate = r4.number_input("Hol Rate", value=2.0)

                    

            emp_df = load_csv("employees")
            if not emp_df.empty:
                emp_df["Tenure"] = emp_df["Start_Date"].apply(calculate_tenure)
                st.dataframe(emp_df, use_container_width=True, hide_index=True)

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
                                if hrs > 5: hrs -= 0.5
                                reg = min(hrs, 8.0)
                                ot = max(hrs - 8.0, 0.0)
                                
                                new_log = pd.data_editor([{
                                    "Date": dtr_date, "Employee_ID": sel_id, "Name": sel_name,
                                    "Time_In": t_in, "Time_Out": t_out, "Reg_Hours": reg,
                                    "OT_Hours": ot, "Is_Holiday": is_hol, "Notes": notes
                                }])
                                save_csv("dtr", pd.concat([load_csv("dtr"), new_log], ignore_index=True))
                                st.success("Logged!")
                                st.rerun()
                
                with c2:
                    dtr_df = load_csv("dtr")
                    if not dtr_df.empty:
                        dtr_df["Date"] = pd.to_datetime(dtr_df["Date"]).dt.date
                        edited_dtr = st.data_editor(dtr_df.sort_values("Date", ascending=False), num_rows="dynamic", use_container_width=True, hide_index=True)
                        if st.button("💾 Save Logs"):
                            save_csv("dtr", edited_dtr)
                            st.success("Saved!")

        # --- ADMIN: PAY SUMMARY ---
        with tab_pay:
            st.subheader("Payroll Generation")
            c1, c2 = st.columns(2)
            start_pay = c1.date_input("Start")
            end_pay = c2.date_input("End")
            
            if st.button("Generate"):
                dtr_df = load_csv("dtr")
                emp_df = load_csv("employees")
                # Convert numeric columns safely
                cols = ["Daily_Rate", "Hourly_Rate", "OT_Rate", "Holiday_Rate"]
                for c in cols: emp_df[c] = pd.to_numeric(emp_df[c], errors='coerce').fillna(0)
                
                dtr_df["Date"] = pd.to_datetime(dtr_df["Date"]).dt.date
                dtr_df["Reg_Hours"] = pd.to_numeric(dtr_df["Reg_Hours"], errors='coerce').fillna(0)
                dtr_df["OT_Hours"] = pd.to_numeric(dtr_df["OT_Hours"], errors='coerce').fillna(0)
                
                mask = (dtr_df["Date"] >= start_pay) & (dtr_df["Date"] <= end_pay)
                period = dtr_df.loc[mask]
                
                if period.empty:
                    st.warning("No logs.")
                else:
                    merged = pd.merge(period, emp_df, on="Employee_ID", how="left", suffixes=("", "_ref"))
                    merged["Base_Pay"] = merged["Reg_Hours"] * merged["Hourly_Rate"]
                    merged["OT_Pay"] = merged["OT_Hours"] * merged["Hourly_Rate"] * merged["OT_Rate"]
                    merged["Hol_Prem"] = merged.apply(lambda x: (x["Reg_Hours"]*x["Hourly_Rate"]*(x["Holiday_Rate"]-1)) if x["Is_Holiday"] else 0, axis=1)
                    merged["Total"] = merged["Base_Pay"] + merged["OT_Pay"] + merged["Hol_Prem"]
                    
                    summary = merged.groupby(["Employee_ID", "Name"]).agg(
                        Reg_Hrs=('Reg_Hours', 'sum'), OT_Hrs=('OT_Hours', 'sum'),
                        Net_Pay=('Total', 'sum')
                    ).reset_index()
                    st.dataframe(summary, use_container_width=True)

        # --- ADMIN: LEAVES ---
        with tab_leave:
            st.subheader("Leave Management")
            emp_df = load_csv("employees")
            if not emp_df.empty:
                with st.form("leave"):
                    l_emp = st.selectbox("Employee", emp_df["Name"].unique())
                    l_date = st.date_input("Date")
                    l_type = st.selectbox("Type", ["Sick", "Vacation", "Emergency"])
                    if st.form_submit_button("File"):
                        eid = emp_df[emp_df["Name"] == l_emp].iloc[0]["Employee_ID"]
                        new_l = pd.DataFrame([{"Employee_ID": eid, "Name": l_emp, "Leave_Date": l_date, "Type": l_type, "Status": "Approved"}])
                        save_csv("leaves", pd.concat([load_csv("leaves"), new_l], ignore_index=True))
                        st.success("Filed!")
                        st.rerun()
            
            leaves = load_csv("leaves")
            if not leaves.empty:
                st.dataframe(leaves, use_container_width=True)

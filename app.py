import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- CONFIGURATION ---
st.set_page_config(page_title="LabadaBoss Pro", layout="wide")

FILES = {"sales": "sales.csv"}
TIERS = {"Tier 1 (₱125)": 125, "Tier 2 (₱150)": 150}
ADDON_OPTIONS = [0, 10, 20, 30, 40]

# --- DATABASE INIT ---
def init_db():
    if not os.path.exists(FILES["sales"]):
        df = pd.DataFrame(columns=[
            "Order_ID", "Date", "Customer", "Contact", "Tier", "Garment_Type", 
            "Loads", "Add_on_Fixed", "Open_Amount", "Amount", "Payment_Type", 
            "Payment_Status", "Work_Status", "Notes"
        ])
        df.to_csv(FILES["sales"], index=False)

init_db()

def load_data():
    # Force string types to prevent leading zero errors and "Notes" column crashes
    df = pd.read_csv(FILES["sales"], dtype={
        "Notes": str, 
        "Contact": str, 
        "Order_ID": str,
        "Work_Status": str,
        "Payment_Status": str
    })
    df["Notes"] = df["Notes"].fillna("")
    # Convert 'Date' column to actual datetime objects for filtering
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    return df

def save_data(df):
    df.to_csv(FILES["sales"], index=False)

# --- NAVIGATION (UPDATED TO DROPDOWN) ---
st.sidebar.title("🧺 LabadaBoss")
menu = st.sidebar.selectbox("Go to Page:", ["Dashboard", "New Sale", "Manage Orders"])

# --- MODULES ---

# 1. DASHBOARD
if menu == "Dashboard":
    st.title("📊 Business Performance")
    sales_df = load_data()
    
    if not sales_df.empty:
        # --- Top Metrics (Today Only) ---
        today_val = date.today()
        today_sales = sales_df[sales_df["Date"] == today_val]["Amount"].sum()
        unpaid_total = sales_df[sales_df["Payment_Status"] == "Unpaid"]["Amount"].sum()
        wip_count = len(sales_df[sales_df["Work_Status"] == "WIP"])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Sales Today", f"₱{today_sales:,.2f}")
        col2.metric("Total Unpaid Receivables", f"₱{unpaid_total:,.2f}")
        col3.metric("WIP Jobs", wip_count)
        
        # --- Date Range Breakdown ---
        st.divider()
        st.subheader("📅 Sales Period Breakdown")
        
        # Default to this week
        start_default = today_val - pd.Timedelta(days=7)
        date_range = st.date_input(
            "Select Sales Period",
            value=(start_default, today_val),
            help="Select a start and end date to see total collections."
        )

        # Logic for range calculation
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            period_df = sales_df[(sales_df["Date"] >= start_date) & (sales_df["Date"] <= end_date)]
            
            cash_total = period_df[period_df["Payment_Type"] == "Cash"]["Amount"].sum()
            gcash_total = period_df[period_df["Payment_Type"] == "GCash"]["Amount"].sum()
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.info(f"**Cash Total**\n\n₱{cash_total:,.2f}")
            with c2:
                st.info(f"**GCash Total**\n\n₱{gcash_total:,.2f}")
            with c3:
                st.success(f"**Grand Total**\n\n₱{cash_total + gcash_total:,.2f}")
            
            st.caption(f"Showing results from {start_date} to {end_date}")
        else:
            st.warning("Please select both a start and end date on the calendar.")
    else:
        st.info("No records found in the system.")

# 2. NEW SALE
elif menu == "New Sale":
    st.title("💰 Create New Job Order")
    with st.form("order_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            cust_name = st.text_input("Customer Name")
            contact = st.text_input("Contact Number (Start with 09)")
            selected_tier = st.selectbox("Select Pricing Tier", list(TIERS.keys()))
            garment = st.selectbox("Type of Garment", ["Regular Items", "Semi-Heavy Items", "Heavy Items"])
        with col2:
            loads = st.number_input("Number of Loads", min_value=1, step=1)
            selected_addon = st.selectbox("Select Add-on Rate (₱)", ADDON_OPTIONS)
            open_amt = st.number_input("Open Amount (₱)", min_value=0.0, step=1.0)
            pay_type = st.radio("Payment Method", ["Cash", "GCash"], horizontal=True)
            pay_status = st.radio("Payment Status", ["Unpaid", "Paid"], horizontal=True)
            
        notes = st.text_area("Notes / Remarks")
        work_status = st.select_slider("Initial Work Status", options=["WIP", "Ready", "Claimed"])

        total_amt = (TIERS[selected_tier] * loads) + selected_addon + open_amt
        st.markdown(f"### **Total Amount: ₱{total_amt:,.2f}**")

        if st.form_submit_button("Confirm Order"):
            new_entry = pd.DataFrame([{
                "Order_ID": datetime.now().strftime("%y%m%d-%H%M%S"),
                "Date": date.today(),
                "Customer": cust_name, "Contact": str(contact),
                "Tier": selected_tier, "Garment_Type": garment,
                "Loads": loads, "Add_on_Fixed": selected_addon,
                "Open_Amount": open_amt, "Amount": total_amt,
                "Payment_Type": pay_type, "Payment_Status": pay_status,
                "Work_Status": work_status, "Notes": str(notes)
            }])
            sales_df = pd.read_csv(FILES["sales"]) # Fresh read to append
            save_data(pd.concat([sales_df, new_entry], ignore_index=True))
            st.success("Order recorded!")

# 3. MANAGE ORDERS
elif menu == "Manage Orders":
    st.title("📋 Job Order Management")
    sales_df = load_data()
    
    if not sales_df.empty:
        # --- FETCH SECTION ---
        st.subheader("🔍 Fetch & Actions")
        order_to_fetch = st.text_input("Enter Order ID (e.g., 231219-1200)")
        
        if order_to_fetch:
            fetched_job = sales_df[sales_df["Order_ID"] == order_to_fetch]
            if not fetched_job.empty:
                st.info(f"Managing Order for: **{fetched_job.iloc[0]['Customer']}**")
                
                # Update & Delete Layout
                tab_update, tab_delete = st.tabs(["Update Status", "⚠️ Delete Order"])
                
                with tab_update:
                    with st.form("update_form"):
                        c1, c2, c3 = st.columns(3)
                        u_work = c1.selectbox("Work Status", ["WIP", "Ready", "Claimed"], index=["WIP", "Ready", "Claimed"].index(fetched_job.iloc[0]["Work_Status"]))
                        u_pay = c2.selectbox("Payment Status", ["Paid", "Unpaid"], index=["Paid", "Unpaid"].index(fetched_job.iloc[0]["Payment_Status"]))
                        u_type = c3.selectbox("Payment Type", ["Cash", "GCash"], index=["Cash", "GCash"].index(fetched_job.iloc[0]["Payment_Type"]))
                        u_notes = st.text_area("Update Notes", value=fetched_job.iloc[0]["Notes"])
                        if st.form_submit_button("Save Changes"):
                            sales_df.loc[sales_df["Order_ID"] == order_to_fetch, ["Work_Status", "Payment_Status", "Payment_Type", "Notes"]] = [u_work, u_pay, u_type, str(u_notes)]
                            save_data(sales_df)
                            st.success("Updated!")
                            st.rerun()

                with tab_delete:
                    st.warning("Deletions cannot be undone. This will remove the record from your sales history.")
                    confirm_check = st.checkbox("I confirm that I want to delete this order.")
                    if st.button("Delete Permanently", disabled=not confirm_check):
                        updated_df = sales_df[sales_df["Order_ID"] != order_to_fetch]
                        save_data(updated_df)
                        st.error(f"Order {order_to_fetch} deleted.")
                        st.rerun()
            else:
                st.error("Order ID not found.")

        st.divider()
        st.subheader("📝 Bulk Status Editor")
        edited_df = st.data_editor(
            sales_df,
            column_config={
                "Work_Status": st.column_config.SelectboxColumn("Work Status", options=["WIP", "Ready", "Claimed"]),
                "Payment_Status": st.column_config.SelectboxColumn("Payment Status", options=["Paid", "Unpaid"]),
                "Payment_Type": st.column_config.SelectboxColumn("Payment Type", options=["Cash", "GCash"]),
                "Notes": st.column_config.TextColumn("Notes", width="large")
            },
            disabled=["Order_ID", "Date", "Customer", "Amount", "Tier", "Loads", "Add_on_Fixed", "Open_Amount", "Garment_Type", "Contact"],
            use_container_width=True, hide_index=True
        )
        if st.button("Save All Bulk Changes"):
            save_data(edited_df)
            st.success("Bulk updates saved!")
            st.rerun()

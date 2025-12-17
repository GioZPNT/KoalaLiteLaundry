import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="LabadaBoss Lite", layout="wide")

FILES = {
    "sales": "sales.csv"
}

PRICES = {
    "Wash-Dry-Fold": 200,
    "Wash Only": 70,
    "Dry Only": 80
}

# --- DATABASE INIT ---
def init_db():
    if not os.path.exists(FILES["sales"]):
        pd.DataFrame(columns=[
            "Order_ID", "Date", "Customer", "Contact", "Service", "Garment_Type", 
            "Loads", "Amount", "Payment_Type", "Payment_Status", "Work_Status"
        ]).to_csv(FILES["sales"], index=False)

init_db()

def load_data():
    return pd.read_csv(FILES["sales"])

def save_data(df):
    df.to_csv(FILES["sales"], index=False)

# --- NAVIGATION ---
st.sidebar.title("🧺 LabadaBoss")
menu = st.sidebar.radio("Navigation", ["Dashboard", "New Sale", "Manage Orders"])

# --- MODULES ---

# 1. DASHBOARD
if menu == "Dashboard":
    st.title("📊 Shop Overview")
    sales_df = load_data()
    
    if not sales_df.empty:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Calculations
        daily_sales = sales_df[sales_df["Date"] == today]["Amount"].sum()
        unpaid_total = sales_df[sales_df["Payment_Status"] == "Unpaid"]["Amount"].sum()
        wip_count = len(sales_df[sales_df["Work_Status"] == "WIP"])
        ready_count = len(sales_df[sales_df["Work_Status"] == "Ready"])
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Sales Today", f"₱{daily_sales:,.2f}")
        col2.metric("Total Unpaid", f"₱{unpaid_total:,.2f}")
        col3.metric("WIP Jobs", wip_count)
        col4.metric("Ready for Pickup", ready_count)
        
        st.divider()
        st.subheader("Daily Payment Breakdown")
        cash_total = sales_df[(sales_df["Date"] == today) & (sales_df["Payment_Type"] == "Cash")]["Amount"].sum()
        gcash_total = sales_df[(sales_df["Date"] == today) & (sales_df["Payment_Type"] == "GCash")]["Amount"].sum()
        
        c1, c2 = st.columns(2)
        c1.info(f"**Cash:** ₱{cash_total:,.2f}")
        c2.info(f"**GCash:** ₱{gcash_total:,.2f}")
    else:
        st.info("No data available yet. Start by creating a New Sale.")

# 2. NEW SALE
elif menu == "New Sale":
    st.title("💰 Create New Job Order")
    
    with st.form("order_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            cust_name = st.text_input("Customer Name")
            contact = st.text_input("Contact Number")
            service = st.selectbox("Service", list(PRICES.keys()))
            garment = st.selectbox("Type of Garment", ["Regular Items", "Semi-Heavy Items", "Heavy Items"])
        
        with col2:
            loads = st.number_input("Number of Loads (9kg/load)", min_value=1, step=1)
            pay_type = st.radio("Payment Method", ["Cash", "GCash"], horizontal=True)
            pay_status = st.radio("Payment Status", ["Unpaid", "Paid"], horizontal=True)
            work_status = st.select_slider("Initial Work Status", options=["WIP", "Ready", "Claimed"])

        total_amt = PRICES[service] * loads
        st.write(f"### Total Amount: ₱{total_amt:,.2f}")

        if st.form_submit_button("Confirm Order"):
            new_entry = pd.DataFrame([{
                "Order_ID": datetime.now().strftime("%y%m%d-%H%M%S"),
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Customer": cust_name,
                "Contact": contact,
                "Service": service,
                "Garment_Type": garment,
                "Loads": loads,
                "Amount": total_amt,
                "Payment_Type": pay_type,
                "Payment_Status": pay_status,
                "Work_Status": work_status
            }])
            sales_df = load_data()
            save_data(pd.concat([sales_df, new_entry], ignore_index=True))
            st.success(f"Order for {cust_name} recorded!")

# 3. MANAGE ORDERS
elif menu == "Manage Orders":
    st.title("📋 Job Order Management")
    sales_df = load_data()
    
    if not sales_df.empty:
        # Quick Filters
        f1, f2 = st.columns(2)
        with f1:
            search = st.text_input("🔍 Search by Customer or Order ID")
        with f2:
            status_filter = st.multiselect("Filter by Status", ["WIP", "Ready", "Claimed"], default=["WIP", "Ready"])

        # Filter Logic
        display_df = sales_df.copy()
        if search:
            display_df = display_df[display_df["Customer"].str.contains(search, case=False) | 
                                    display_df["Order_ID"].str.contains(search, case=False)]
        if status_filter:
            display_df = display_df[display_df["Work_Status"].isin(status_filter)]

        st.write("### Active Job List")
        edited_df = st.data_editor(
            display_df,
            column_config={
                "Work_Status": st.column_config.SelectboxColumn("Work Status", options=["WIP", "Ready", "Claimed"]),
                "Payment_Status": st.column_config.SelectboxColumn("Payment Status", options=["Paid", "Unpaid"]),
                "Payment_Type": st.column_config.SelectboxColumn("Payment Type", options=["Cash", "GCash"]),
            },
            disabled=["Order_ID", "Date", "Customer", "Amount", "Service", "Loads", "Garment_Type", "Contact"],
            use_container_width=True,
            hide_index=True
        )
        
        if st.button("Save All Updates"):
            # Sync changes back to the main CSV
            for _, row in edited_df.iterrows():
                sales_df.loc[sales_df["Order_ID"] == row["Order_ID"], ["Work_Status", "Payment_Status", "Payment_Type"]] = \
                    [row["Work_Status"], row["Payment_Status"], row["Payment_Type"]]
            save_data(sales_df)
            st.success("Database updated!")
            st.rerun()
    else:
        st.warning("No orders found.")

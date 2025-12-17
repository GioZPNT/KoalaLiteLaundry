import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- SECURITY CONFIG ---
# Change this to your desired password
LOGIN_PASSWORD = "KoalaLaundry2025" 

# --- CONFIGURATION ---
st.set_page_config(page_title="Koala Lite", layout="wide")

FILES = {"sales": "sales.csv"}
TIERS = {"Tier 1 (₱125)": 125, "Tier 2 (₱150)": 150}
ADDON_OPTIONS = [0, 10, 20, 30, 40]

# --- LOGIN LOGIC ---
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == LOGIN_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.title("🧺 Koala Management System")
        st.text_input("Enter Password to Access Operations", type="password", on_change=password_entered, key="password")
        st.info("Authorized Personnel Only")
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.title("🧺 Koala Management System")
        st.text_input("Enter Password to Access Operations", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

# --- ONLY RUN APP IF LOGGED IN ---
if check_password():
    
    # --- LOGOUT BUTTON IN SIDEBAR ---
    if st.sidebar.button("Log Out"):
        st.session_state["password_correct"] = False
        st.rerun()

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
        df = pd.read_csv(FILES["sales"], dtype={"Notes": str, "Contact": str, "Order_ID": str})
        df["Notes"] = df["Notes"].fillna("")
        return df

    def save_data(df):
        df.to_csv(FILES["sales"], index=False)

    # --- NAVIGATION ---
    st.sidebar.title("🧺 Koala Laundry")
    menu = st.sidebar.radio("Navigation", ["Dashboard", "New Sale", "Manage Orders"])

    # 1. DASHBOARD
    if menu == "Dashboard":
        st.title("📊 Shop Overview")
        sales_df = load_data()
        if not sales_df.empty:
            today = datetime.now().strftime("%Y-%m-%d")
            daily_sales = sales_df[sales_df["Date"] == today]["Amount"].sum()
            unpaid_total = sales_df[sales_df["Payment_Status"] == "Unpaid"]["Amount"].sum()
            wip_count = len(sales_df[sales_df["Work_Status"] == "WIP"])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Sales Today", f"₱{daily_sales:,.2f}")
            col2.metric("Total Unpaid", f"₱{unpaid_total:,.2f}")
            col3.metric("WIP Jobs", wip_count)
            
            st.divider()
            cash = sales_df[(sales_df["Date"] == today) & (sales_df["Payment_Type"] == "Cash")]["Amount"].sum()
            gcash = sales_df[(sales_df["Date"] == today) & (sales_df["Payment_Type"] == "GCash")]["Amount"].sum()
            st.info(f"💵 Cash Today: ₱{cash:,.2f} | 📱 GCash Today: ₱{gcash:,.2f}")
        else:
            st.info("No data yet.")

    # 2. NEW SALE
    elif menu == "New Sale":
        st.title("💰 Create New Job Order")
        with st.form("order_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cust_name = st.text_input("Customer Name")
                contact = st.text_input("Contact Number")
                selected_tier = st.selectbox("Select Pricing Tier", list(TIERS.keys()))
                garment = st.selectbox("Type of Garment", ["Regular Items", "Semi-Heavy Items", "Heavy Items"])
            with col2:
                loads = st.number_input("Number of Loads", min_value=1, step=1)
                selected_addon = st.selectbox("Select Add-on Rate (₱)", ADDON_OPTIONS)
                open_amt = st.number_input("Other Amount (₱)", min_value=0.0, step=1.0)
                pay_type = st.radio("Payment Method", ["Cash", "GCash"], horizontal=True)
                pay_status = st.radio("Payment Status", ["Unpaid", "Paid"], horizontal=True)
                
            notes = st.text_area("Notes / Remarks")
            work_status = st.select_slider("Initial Work Status", options=["WIP", "Ready", "Claimed"])

            total_amt = (TIERS[selected_tier] * loads) + selected_addon + open_amt
            st.markdown(f"### **Total Amount: ₱{total_amt:,.2f}**")

            if st.form_submit_button("Confirm Order"):
                new_entry = pd.DataFrame([{
                    "Order_ID": datetime.now().strftime("%y%m%d-%H%M%S"),
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Customer": cust_name, "Contact": str(contact),
                    "Tier": selected_tier, "Garment_Type": garment,
                    "Loads": loads, "Add_on_Fixed": selected_addon,
                    "Open_Amount": open_amt, "Amount": total_amt,
                    "Payment_Type": pay_type, "Payment_Status": pay_status,
                    "Work_Status": work_status, "Notes": str(notes)
                }])
                sales_df = load_data()
                save_data(pd.concat([sales_df, new_entry], ignore_index=True))
                st.success("Order recorded!")

    # 3. MANAGE ORDERS
    elif menu == "Manage Orders":
        st.title("📋 Job Order Management")
        sales_df = load_data()
        
        if not sales_df.empty:
            search = st.text_input("🔍 Search Customer or Order ID")
            if search:
                display_df = sales_df[sales_df["Customer"].str.contains(search, case=False) | 
                                      sales_df["Order_ID"].astype(str).str.contains(search, case=False)]
            else:
                display_df = sales_df

            edited_df = st.data_editor(
                display_df,
                column_config={
                    "Work_Status": st.column_config.SelectboxColumn("Work Status", options=["WIP", "Ready", "Claimed"]),
                    "Payment_Status": st.column_config.SelectboxColumn("Payment Status", options=["Paid", "Unpaid"]),
                    "Payment_Type": st.column_config.SelectboxColumn("Payment Type", options=["Cash", "GCash"]),
                    "Notes": st.column_config.TextColumn("Notes", width="large")
                },
                disabled=["Order_ID", "Date", "Customer", "Amount", "Tier", "Loads", "Add_on_Fixed", "Open_Amount", "Garment_Type", "Contact"],
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("Save All Updates"):
                for _, row in edited_df.iterrows():
                    sales_df.loc[sales_df["Order_ID"] == row["Order_ID"], ["Work_Status", "Payment_Status", "Payment_Type", "Notes"]] = \
                        [row["Work_Status"], row["Payment_Status"], row["Payment_Type"], row["Notes"]]
                save_data(sales_df)
                st.success("Updated!")
                st.rerun()

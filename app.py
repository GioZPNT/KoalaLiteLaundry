import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- SECURITY CONFIG ---
ACCESS_PASSWORD = "Koala2025"

# --- CONFIGURATION ---
st.set_page_config(page_title="Koala Insite", layout="wide")

FILES = {"sales": "sales.csv"}
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
    # --- LOGOUT & DB INIT ---
    if st.sidebar.button("Log Out"):
        st.session_state["password_correct"] = False
        st.rerun()

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
        df = pd.read_csv(FILES["sales"], dtype={"Notes": str, "Contact": str, "Order_ID": str, "Work_Status": str, "Payment_Status": str})
        df["Notes"] = df["Notes"].fillna("")
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        return df

    def save_data(df):
        df.to_csv(FILES["sales"], index=False)

    # --- NAVIGATION ---
    st.sidebar.title("🧺 Koala Insite")
    menu = st.sidebar.selectbox("Go to Page:", ["Dashboard", "New Sale", "Manage Orders"])

    # 1. DASHBOARD
    if menu == "Dashboard":
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

    # 2. NEW SALE (FIXED)
    elif menu == "New Sale":
        st.title("💰 Create New Job Order")
        
        # Reset Logic
        if "extra_items_list" not in st.session_state:
            st.session_state.extra_items_list = pd.DataFrame(columns=["Item Description", "Price (₱)"])

        if st.button("🔄 Clear/Reset Form"):
            st.session_state.extra_items_list = pd.DataFrame(columns=["Item Description", "Price (₱)"])
            st.rerun()

        with st.form("order_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cust_name = st.text_input("Customer Name")
                contact = st.text_input("Contact Number")
                selected_tier = st.selectbox("Pricing Tier", list(TIERS.keys()))
                garment = st.selectbox("Garment Type", ["Regular", "Semi-Heavy", "Heavy"])
            with col2:
                loads = st.number_input("Loads", min_value=1, step=1)
                open_amt = st.number_input("Misc Amount (₱)", min_value=0.0)
                pay_type = st.radio("Payment", ["Cash", "GCash"], horizontal=True)
                pay_status = st.radio("Status", ["Unpaid", "Paid"], horizontal=True)

            st.subheader("🧺 Extra Items")
            edited_items = st.data_editor(st.session_state.extra_items_list, num_rows="dynamic", use_container_width=True, key="items_ed")

            notes = st.text_area("Notes")
            work_status = st.select_slider("Work Status", options=["WIP", "Ready", "Claimed"])

            # --- THE FIX: Safe Numeric Summing ---
            base_price = float(TIERS[selected_tier] * loads)
            if not edited_items.empty:
                extras_sum = pd.to_numeric(edited_items["Price (₱)"], errors='coerce').fillna(0).sum()
            else:
                extras_sum = 0.0
            
            total_amt = base_price + float(extras_sum) + float(open_amt)
            st.markdown(f"### **Total: ₱{total_amt:,.2f}**")

            if st.form_submit_button("Confirm Order"):
                items_str = ", ".join([f"{r['Item Description']}(₱{r['Price (₱)']})" for _, r in edited_items.iterrows() if r['Item Description']])
                new_entry = pd.DataFrame([{
                    "Order_ID": datetime.now().strftime("%y%m%d-%H%M%S"),
                    "Date": date.today(), "Customer": cust_name, "Contact": str(contact),
                    "Tier": selected_tier, "Garment_Type": garment, "Loads": loads,
                    "Add_on_Fixed": extras_sum, "Open_Amount": open_amt, "Amount": total_amt,
                    "Payment_Type": pay_type, "Payment_Status": pay_status,
                    "Work_Status": work_status, "Notes": f"Items: {items_str} | {notes}"
                }])
                save_data(pd.concat([pd.read_csv(FILES["sales"]), new_entry], ignore_index=True))
                st.success("Order Saved!")

    # 3. MANAGE ORDERS
    elif menu == "Manage Orders":
        st.title("📋 Job Management")
        sales_df = load_data()
        if not sales_df.empty:
            order_id = st.text_input("Enter Order ID to Fetch")
            if order_id:
                job = sales_df[sales_df["Order_ID"] == order_id]
                if not job.empty:
                    tab1, tab2 = st.tabs(["Update", "Delete"])
                    with tab1:
                        with st.form("u_form"):
                            # Logic for selectbox defaults
                            w_opts = ["WIP", "Ready", "Claimed"]
                            p_opts = ["Paid", "Unpaid"]
                            t_opts = ["Cash", "GCash"]
                            
                            nw = st.selectbox("Work", w_opts, index=w_opts.index(job.iloc[0]["Work_Status"]) if job.iloc[0]["Work_Status"] in w_opts else 0)
                            np = st.selectbox("Payment", p_opts, index=p_opts.index(job.iloc[0]["Payment_Status"]) if job.iloc[0]["Payment_Status"] in p_opts else 0)
                            nt = st.selectbox("Type", t_opts, index=t_opts.index(job.iloc[0]["Payment_Type"]) if job.iloc[0]["Payment_Type"] in t_opts else 0)
                            nn = st.text_area("Notes", value=job.iloc[0]["Notes"])
                            if st.form_submit_button("Update"):
                                sales_df.loc[sales_df["Order_ID"] == order_id, ["Work_Status", "Payment_Status", "Payment_Type", "Notes"]] = [nw, np, nt, nn]
                                save_data(sales_df)
                                st.rerun()
                    with tab2:
                        if st.checkbox("Confirm Delete"):
                            if st.button("Delete Permanently"):
                                save_data(sales_df[sales_df["Order_ID"] != order_id])
                                st.rerun()

            st.divider()
            edited_bulk = st.data_editor(sales_df, use_container_width=True, hide_index=True, disabled=["Order_ID", "Date", "Customer", "Amount"])
            if st.button("Save Bulk Changes"):
                save_data(edited_bulk)
                st.success("Saved!")

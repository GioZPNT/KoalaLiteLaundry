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
                "Loads", "Additionals", "Misc_Amount", "Amount", "Payment_Type", 
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
        # --- ADMIN SECURITY CHECK ---
        DASHBOARD_PASSWORD = "Bebot88"  # <--- Change this to your preferred admin password

        # Initialize the specific state for dashboard access
        if "dashboard_unlocked" not in st.session_state:
            st.session_state.dashboard_unlocked = False

        # If locked, show the password input
        if not st.session_state.dashboard_unlocked:
            st.title("🔒 Admin Access Required")
            st.info("This section contains sensitive financial data.")
            
            admin_input = st.text_input("Enter Owner Password", type="password", key="dash_pass_input")
            
            if st.button("Unlock Dashboard"):
                if admin_input == DASHBOARD_PASSWORD:
                    st.session_state.dashboard_unlocked = True
                    st.rerun()
                else:
                    st.error("❌ Incorrect Password")
        
        # If unlocked, show the actual dashboard
        else:
            # Optional: Button to re-lock the screen
            if st.button("🔒 Lock Dashboard"):
                st.session_state.dashboard_unlocked = False
                st.rerun()

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
                
                # (You can add your Date Range breakdown code here if needed)
            else:
                st.info("No records found yet.")

    # 2. NEW SALE (FIXED)
    elif menu == "New Sale":
        st.title("💰 Create New Job Order")

        # --- 0. PERSISTENT SUCCESS MESSAGE LOGIC ---
        # Check if a message exists from the previous run (before the reset)
        if "last_success_msg" in st.session_state and st.session_state.last_success_msg:
            st.success(st.session_state.last_success_msg)
            # Clear it immediately so it doesn't stay on screen forever
            del st.session_state.last_success_msg

        # --- 1. SESSION STATE FOR RESETTING ---
        if "form_key" not in st.session_state:
            st.session_state.form_key = 0

        # Reset Button (Manual Clear)
        if st.button("🔄 Reset Form"):
            st.session_state.form_key += 1
            st.rerun()

        # --- 2. THE FORM ---
        with st.form("order_form", clear_on_submit=False):
            st.subheader("👤 Customer & Service")
            
            # Helper for the current key
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
                st.markdown("##### Detergent")
                det_brand = st.text_input("Brand", placeholder="e.g. Ariel", key=f"d_brand_{k}")
                det_price = st.number_input("Amount (₱)", min_value=0.0, step=5.0, key=f"d_price_{k}")
            
            with c2:
                st.markdown("##### Fabric Conditioner")
                fab_brand = st.text_input("Brand", placeholder="e.g. Downy", key=f"f_brand_{k}")
                fab_price = st.number_input("Amount (₱)", min_value=0.0, step=5.0, key=f"f_price_{k}")

            st.divider()
            notes = st.text_area("Notes / Remarks", key=f"notes_{k}")
            work_status = st.select_slider("Work Status", options=["WIP", "Ready", "Claimed"], key=f"ws_{k}")

            # --- Calculation Logic ---
            base_price = float(TIERS[selected_tier] * loads)
            supplies_total = float(det_price) + float(fab_price)
            grand_total = base_price + supplies_total + float(open_amt)

            # --- Display Totals ---
            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:10px;">
                <h4>🧾 Payment Summary</h4>
                <p>Base Laundry: ₱{base_price:,.2f}<br>
                Supplies: ₱{supplies_total:,.2f}<br>
                Misc: ₱{open_amt:,.2f}</p>
                <h3 style="color:#007bff;">Total Amount: ₱{grand_total:,.2f}</h3>
            </div>
            """, unsafe_allow_html=True)

            # --- Actions ---
            col_actions1, col_actions2 = st.columns(2)
            with col_actions1:
                update_click = st.form_submit_button("🔄 Update Total", type="secondary", use_container_width=True)
            with col_actions2:
                confirm_click = st.form_submit_button("✅ Confirm Order", type="primary", use_container_width=True)

            # --- Save Logic ---
            if confirm_click:
                if not cust_name:
                    st.error("⚠️ Customer Name is required.")
                else:
                    # Format supplies string
                    supplies_str = []
                    if det_price > 0 or det_brand:
                        supplies_str.append(f"Det: {det_brand} (₱{det_price})")
                    if fab_price > 0 or fab_brand:
                        supplies_str.append(f"Fab: {fab_brand} (₱{fab_price})")
                    
                    supplies_final = ", ".join(supplies_str) if supplies_str else "None"

                    new_entry = pd.DataFrame([{
                        "Order_ID": datetime.now().strftime("%y%m%d-%H%M%S"),
                        "Date": date.today(), 
                        "Customer": cust_name, 
                        "Contact": str(contact),
                        "Tier": selected_tier, 
                        "Garment_Type": garment, 
                        "Loads": loads,
                        "Additionals": supplies_total, 
                        "Misc_Amount": open_amt, 
                        "Amount": grand_total,
                        "Payment_Type": pay_type, 
                        "Payment_Status": pay_status,
                        "Work_Status": work_status, 
                        "Notes": f"{supplies_final} | {notes}"
                    }])
                    
                    # Append and Save
                    current_df = pd.read_csv(FILES["sales"])
                    save_data(pd.concat([current_df, new_entry], ignore_index=True))
                    
                    # --- SUCCESS HANDLING ---
                    # Store the message in session state so it survives the rerun
                    st.session_state.last_success_msg = f"✅ Success! Order for {cust_name} saved. (Total: ₱{grand_total:,.2f})"
                    
                    # Increment key to reset form, then rerun to show the empty form + success message
                    st.session_state.form_key += 1
                    st.rerun()

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
                            # Safe index finding
                            curr_work = fetched_job.iloc[0]["Work_Status"]
                            curr_pay = fetched_job.iloc[0]["Payment_Status"]
                            curr_type = fetched_job.iloc[0]["Payment_Type"]
                            
                            u_work = c1.selectbox("Work Status", ["WIP", "Ready", "Claimed"], index=["WIP", "Ready", "Claimed"].index(curr_work) if curr_work in ["WIP", "Ready", "Claimed"] else 0)
                            u_pay = c2.selectbox("Payment Status", ["Paid", "Unpaid"], index=["Paid", "Unpaid"].index(curr_pay) if curr_pay in ["Paid", "Unpaid"] else 0)
                            u_type = c3.selectbox("Payment Type", ["Cash", "GCash"], index=["Cash", "GCash"].index(curr_type) if curr_type in ["Cash", "GCash"] else 0)
                            
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

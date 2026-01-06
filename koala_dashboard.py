import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from typing import Optional
from datetime import datetime

# NOTE: page config is applied by the host app (e.g., `moon.py`) when imported.
# If run directly, we'll set the page config at the module entry point.

DEFAULT_CSV = Path.home() / "Downloads" / "Koala Guadalupe (Responses) - Form Responses 1.csv"

# Aliases for required metrics so users can upload files with slightly different column names
REQUIRED_ALIASES = {
    "paid": ["Total Paid", "Paid", "Amount Paid", "Paid Amount", "total_paid"],
    "unpaid": ["Total Unpaid", "Unpaid", "Amount Unpaid", "Unpaid Amount", "total_unpaid"],
    "loads": ["Total loads completed", "Total Loads", "Loads", "Total_Loads", "total_loads"],
    "time_in": ["Time In", "Time_In", "time_in", "TimeIn"],
    "time_out": ["Time Out", "Time_Out", "time_out", "TimeOut"]}


@st.cache_data
def read_csv(path_or_buffer) -> pd.DataFrame:
    # Accept both path strings and file-like buffers
    df = pd.read_csv(path_or_buffer)
    # Normalize column names (strip whitespace)
    df.columns = [c.strip() for c in df.columns]
    return df


def find_column(df: pd.DataFrame, aliases: list) -> Optional[str]:
    """Return first matching column name from aliases (case-insensitive), else None."""
    cols_lower = {c.lower(): c for c in df.columns}
    for a in aliases:
        if a.lower() in cols_lower:
            return cols_lower[a.lower()]
    return None


def coerce_numeric_currency(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.replace(r"[\$,]", "", regex=True).replace("", "0")
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def coerce_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


def format_currency(x: float) -> str:
    return f"${x:,.2f}"


def render_dashboard():
    """Render the Koala operations dashboard in the current Streamlit app context.
    This function is safe to import and call from another Streamlit app (e.g., `moon.py`).
    """
    st.title("Koala Laundry — Operations Dashboard")

    st.sidebar.header("Data source")
    st.sidebar.write("Upload a CSV with at least: **Total Paid**, **Total Unpaid**, **Total Loads** (column names can vary).")

    uploaded = st.sidebar.file_uploader("Upload CSV file", type=["csv"], accept_multiple_files=False)
    csv_path = st.sidebar.text_input("Or enter CSV path", value=str(DEFAULT_CSV))
    show_sample = st.sidebar.checkbox("Show sample CSV and download template")

    if show_sample:
        sample = pd.DataFrame({"Date": ["2025-01-01"], "Name": ["Alice"], "Total Paid": [20.0], "Total Unpaid": [5.0], "Total loads completed": [3]})
        st.sidebar.dataframe(sample)
        st.sidebar.download_button("Download sample CSV", sample.to_csv(index=False).encode("utf-8"), file_name="koala_sample.csv", mime="text/csv")

    # Load dataframe from upload or path
    df = None
    if uploaded is not None:
        try:
            df = read_csv(uploaded)
        except Exception as e:
            st.error(f"Error reading uploaded CSV: {e}")
            st.stop()
    else:
        path = Path(csv_path)
        if path.exists():
            try:
                df = read_csv(str(path))
            except Exception as e:
                st.error(f"Error reading CSV at {path}: {e}")
                st.stop()
        else:
            st.info("No CSV provided yet — upload a CSV or provide a valid path.")
            st.stop()

    st.subheader("Dataset preview")
    df = st.data_editor(df, width='stretch')

    # Attempt to auto-detect columns
    detected = {}
    for key, aliases in REQUIRED_ALIASES.items():
        detected[key] = find_column(df, aliases)

    # If any required fields are missing, allow user to map them manually
    st.sidebar.markdown("---")
    st.sidebar.header("Column mapping")

    col_options = list(df.columns)

    mapped = {}
    for key, current in detected.items():
        label = key.capitalize()
        default = current if current is not None else None
        mapped[key] = st.sidebar.selectbox(f"Column for {label}", options=[None] + col_options, index=(col_options.index(default) + 1 if default in col_options else 0))

    # Validate mapping
    missing = [k for k, v in mapped.items() if v is None or v not in df.columns]
    if missing:
        st.error(f"Missing mappings for: {', '.join(missing)}. Please map these columns in the sidebar.")
        st.stop()

    # Coerce types
    df[mapped["paid"]] = coerce_numeric_currency(df[mapped["paid"]])
    df[mapped["unpaid"]] = coerce_numeric_currency(df[mapped["unpaid"]])
    df[mapped["loads"]] = coerce_int(df[mapped["loads"]])

    # Coerce time columns to datetime
    df[mapped["time_in"]] = pd.to_datetime(df[mapped["time_in"]], errors='coerce')
    df[mapped["time_out"]] = pd.to_datetime(df[mapped["time_out"]], errors='coerce')

    # Compute duration in hours
    df['duration_hours'] = (df[mapped["time_out"]] - df[mapped["time_in"]]).dt.total_seconds() / 3600

    # Optional: parse Date if present
    if "Date" in df.columns:
        try:
            df["Date"] = pd.to_datetime(df["Date"])
            df['week'] = df['Date'].dt.isocalendar().week
            df['year'] = df['Date'].dt.year
        except Exception:
            pass

    # Compute total hours and payroll
    name_col = find_column(df, ["Name", "Employee", "Staff", "Worker"])
    if name_col and 'duration_hours' in df.columns:
        total_hours = df['duration_hours'].sum()
        rate_per_hour = 62.5
        total_payroll = total_hours * rate_per_hour
    else:
        total_hours = 0.0
        total_payroll = 0.0

    # KPIs
    paid_total = df[mapped["paid"]].sum()
    unpaid_total = df[mapped["unpaid"]].sum()
    loads_total = int(df[mapped["loads"]].sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Paid", format_currency(paid_total))
    col2.metric("Total Unpaid", format_currency(unpaid_total))
    col3.metric("Total Loads", f"{loads_total:,}")
    col4.metric("Total Payroll Amount", f"P{total_payroll:,.2f}")

    st.markdown("---")

    # Loads by staff
    name_col = find_column(df, ["Name", "Employee", "Staff", "Worker"])
    if name_col and mapped["loads"] in df.columns:
        loads_by_person = df.groupby(name_col)[mapped["loads"]].sum().reset_index().rename(columns={mapped["loads"]: "Total Loads"}).sort_values("Total Loads", ascending=False)
        fig2 = px.bar(loads_by_person, x=name_col, y="Total Loads", title="Total loads by staff", text="Total Loads")
        st.plotly_chart(fig2, width='stretch')

    # Hours worked by employee - Top 2 with weekly breakdown
    if name_col and 'duration_hours' in df.columns:
        # Compute total hours per employee to get top 2
        hours_by_employee = df.groupby(name_col)['duration_hours'].sum().reset_index().rename(columns={'duration_hours': 'Total Hours'}).sort_values("Total Hours", ascending=False)
        top_employees = hours_by_employee[name_col].head(2).tolist()
        
        # For each top employee, show weekly earnings for last 3 weeks including this week
        rate_per_hour = 62.5
        for i, emp in enumerate(top_employees, 1):
            emp_data = df[df[name_col] == emp]
            if 'week' in df.columns:
                weekly_hours = emp_data.groupby('week')['duration_hours'].sum().reset_index().rename(columns={'duration_hours': 'Total Hours'}).sort_values('week', ascending=False).head(3).sort_values('week')
                weekly_hours['Total Earnings'] = weekly_hours['Total Hours'] * rate_per_hour
                fig = px.bar(weekly_hours, x='week', y='Total Earnings', title=f"Weekly Earnings for {emp} (Last 3 Weeks)", text="Total Earnings")
                fig.update_traces(texttemplate='P%{text:.2f}', textposition='outside')
                st.plotly_chart(fig, width='stretch')
            else:
                st.warning("Week column not found in data. Cannot display weekly charts.")
                break

    # Earnings from hours
    if name_col and 'duration_hours' in df.columns:
        hours_by_employee = df.groupby(name_col)['duration_hours'].sum().reset_index().rename(columns={'duration_hours': 'Total Hours'}).sort_values("Total Hours", ascending=False)
        rate_per_hour = 62.5
        earnings_by_employee = hours_by_employee.copy()
        earnings_by_employee['Total Payroll Amount'] = earnings_by_employee['Total Hours'] * rate_per_hour
        fig4 = px.bar(earnings_by_employee, x=name_col, y="Total Payroll Amount", title="Total payroll amount from hours worked by employee")
        fig4.update_traces(texttemplate='P%{y:.2f}', textposition='outside')
        st.plotly_chart(fig4, width='stretch')

        total_hours = hours_by_employee['Total Hours'].sum()
        total_payroll = earnings_by_employee['Total Payroll Amount'].sum()
    else:
        total_hours = 0.0
        total_payroll = 0.0

    # Allow download of summary
    summary = pd.DataFrame({
        "metric": ["Total Paid", "Total Unpaid", "Total Loads", "Total Hours Worked", "Total Payroll Amount"],
        "value": [paid_total, unpaid_total, loads_total, total_hours, total_payroll]
    })

    st.download_button("Download summary CSV", summary.to_csv(index=False).encode("utf-8"), file_name="koala_summary.csv", mime="text/csv")

    # NOTE: PDF export functionality has been removed.
    st.info("PDF export has been removed from this dashboard. Use the "
            "'Download summary CSV' button above or external reporting tools to create a PDF if needed.")

    st.sidebar.markdown("---")
    st.sidebar.info("Run: `streamlit run koala_dashboard.py`")


if __name__ == "__main__":
    # When run directly, ensure a page config is set for this app
    st.set_page_config(page_title="Koala Dashboard", layout="wide")
    render_dashboard() 


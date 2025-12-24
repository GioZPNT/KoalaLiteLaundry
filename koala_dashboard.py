import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from typing import Optional

st.set_page_config(page_title="Koala Dashboard", layout="wide")

DEFAULT_CSV = Path.home() / "Downloads" / "Koala Guadalupe (Responses) - Form Responses 1.csv"

# Aliases for required metrics so users can upload files with slightly different column names
REQUIRED_ALIASES = {
    "paid": ["Total Paid", "Paid", "Amount Paid", "Paid Amount", "total_paid"],
    "unpaid": ["Total Unpaid", "Unpaid", "Amount Unpaid", "Unpaid Amount", "total_unpaid"],
    "loads": ["Total loads completed", "Total Loads", "Loads", "Total_Loads", "total_loads"]}


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


def main():
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
    st.dataframe(df.head(100), use_container_width=True)

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
    missing = [k for k, v in mapped.items() if not v]
    if missing:
        st.error(f"Missing mappings for: {', '.join(missing)}. Please map these columns in the sidebar.")
        st.stop()

    # Coerce types
    df[mapped["paid"]] = coerce_numeric_currency(df[mapped["paid"]])
    df[mapped["unpaid"]] = coerce_numeric_currency(df[mapped["unpaid"]])
    df[mapped["loads"]] = coerce_int(df[mapped["loads"]])

    # Optional: parse Date if present
    if "Date" in df.columns:
        try:
            df["Date"] = pd.to_datetime(df["Date"])
        except Exception:
            pass

    # KPIs
    paid_total = df[mapped["paid"]].sum()
    unpaid_total = df[mapped["unpaid"]].sum()
    loads_total = int(df[mapped["loads"]].sum())

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Paid", format_currency(paid_total))
    col2.metric("Total Unpaid", format_currency(unpaid_total))
    col3.metric("Total Loads", f"{loads_total:,}")

    st.markdown("---")

    # Paid vs Unpaid pie chart
    fig_pie = px.pie(values=[paid_total, unpaid_total], names=["Paid", "Unpaid"], title="Paid vs Unpaid", hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

    # Time series of payments by Date
    if "Date" in df.columns:
        payments = df.groupby("Date")[[mapped["paid"], mapped["unpaid"]]].sum().reset_index().sort_values("Date")
        payments = payments.rename(columns={mapped["paid"]: "Total Paid", mapped["unpaid"]: "Total Unpaid"})
        fig = px.line(payments, x="Date", y=["Total Paid", "Total Unpaid"], labels={"value": "Amount", "variable": "Type"}, title="Payments over time")
        st.plotly_chart(fig, use_container_width=True)

    # Loads by staff
    name_col = find_column(df, ["Name", "Employee", "Staff", "Worker"])
    if name_col and mapped["loads"] in df.columns:
        loads_by_person = df.groupby(name_col)[mapped["loads"]].sum().reset_index().rename(columns={mapped["loads"]: "Total Loads"}).sort_values("Total Loads", ascending=False)
        fig2 = px.bar(loads_by_person, x=name_col, y="Total Loads", title="Total loads by staff", text="Total Loads")
        st.plotly_chart(fig2, use_container_width=True)

    # Allow download of summary
    summary = pd.DataFrame({
        "metric": ["Total Paid", "Total Unpaid", "Total Loads"],
        "value": [paid_total, unpaid_total, loads_total]
    })

    st.download_button("Download summary CSV", summary.to_csv(index=False).encode("utf-8"), file_name="koala_summary.csv", mime="text/csv")

    st.sidebar.markdown("---")
    st.sidebar.info("Run: `streamlit run koala_dashboard.py`")


if __name__ == "__main__":
    main()

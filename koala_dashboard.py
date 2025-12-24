import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Koala Dashboard", layout="wide")

DEFAULT_CSV = Path.home() / "Downloads" / "Koala Guadalupe (Responses) - Form Responses 1.csv"

@st.cache_data
def load_data(path: str):
    df = pd.read_csv(path)

    # Normalize column names
    df.columns = [c.strip() for c in df.columns]

    # Parse dates
    if "Date" in df.columns:
        try:
            df["Date"] = pd.to_datetime(df["Date"])
        except Exception:
            pass

    # Clean monetary fields
    for col in ["Total Paid", "Total Unpaid"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"[\$,]", "", regex=True)
                .replace("", "0")
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Clean loads column
    loads_col = "Total loads completed"
    if loads_col in df.columns:
        df[loads_col] = pd.to_numeric(df[loads_col], errors="coerce").fillna(0).astype(int)

    return df


def format_currency(x):
    return f"${x:,.2f}"


def main():
    st.title("Koala Laundry — Operations Dashboard")

    st.sidebar.header("Data source")
    csv_path = st.sidebar.text_input("CSV path", value=str(DEFAULT_CSV))
    uploaded = st.sidebar.file_uploader("Or upload CSV file", type=["csv"]) 

    if uploaded is not None:
        df = pd.read_csv(uploaded)
    else:
        path = Path(csv_path)
        if not path.exists():
            st.error(f"CSV not found at: {path}\nPlease upload the CSV or correct the path.")
            st.stop()
        df = load_data(str(path))

    st.write("**Dataset preview**")
    st.dataframe(df.head(100), use_container_width=True)

    # KPIs
    paid_total = df.get("Total Paid", pd.Series([0])).sum()
    unpaid_total = df.get("Total Unpaid", pd.Series([0])).sum()
    loads_total = df.get("Total loads completed", pd.Series([0])).sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Paid", format_currency(paid_total))
    col2.metric("Total Unpaid", format_currency(unpaid_total))
    col3.metric("Total Loads Completed", f"{int(loads_total):,}")

    st.markdown("---")

    # Time series of payments by Date
    if "Date" in df.columns:
        payments = df.groupby("Date")["Total Paid", "Total Unpaid"].sum().reset_index()
        payments = payments.sort_values("Date")

        fig = px.line(payments, x="Date", y=["Total Paid", "Total Unpaid"], labels={"value":"Amount", "variable":"Type"}, title="Payments over time")
        st.plotly_chart(fig, use_container_width=True)

    # Loads by staff
    if "Name" in df.columns and "Total loads completed" in df.columns:
        loads_by_person = df.groupby("Name")["Total loads completed"].sum().reset_index().sort_values("Total loads completed", ascending=False)
        fig2 = px.bar(loads_by_person, x="Name", y="Total loads completed", title="Total loads by staff", text="Total loads completed")
        st.plotly_chart(fig2, use_container_width=True)

    # Allow download of summary
    summary = pd.DataFrame({
        "metric": ["Total Paid", "Total Unpaid", "Total loads completed"],
        "value": [paid_total, unpaid_total, loads_total]
    })

    st.download_button("Download summary CSV", summary.to_csv(index=False).encode("utf-8"), file_name="koala_summary.csv", mime="text/csv")

    st.sidebar.markdown("---")
    st.sidebar.info("Run: `streamlit run koala_dashboard.py`")


if __name__ == "__main__":
    main()

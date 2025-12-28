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
    st.dataframe(df.head(100), width='stretch')

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
    st.plotly_chart(fig_pie, width='stretch')

    # Time series of payments by Date
    if "Date" in df.columns:
        payments = df.groupby("Date")[[mapped["paid"], mapped["unpaid"]]].sum().reset_index().sort_values("Date")
        payments = payments.rename(columns={mapped["paid"]: "Total Paid", mapped["unpaid"]: "Total Unpaid"})
        fig = px.line(payments, x="Date", y=["Total Paid", "Total Unpaid"], labels={"value": "Amount", "variable": "Type"}, title="Payments over time")
        st.plotly_chart(fig, width='stretch')

    # Loads by staff
    name_col = find_column(df, ["Name", "Employee", "Staff", "Worker"])
    if name_col and mapped["loads"] in df.columns:
        loads_by_person = df.groupby(name_col)[mapped["loads"]].sum().reset_index().rename(columns={mapped["loads"]: "Total Loads"}).sort_values("Total Loads", ascending=False)
        fig2 = px.bar(loads_by_person, x=name_col, y="Total Loads", title="Total loads by staff", text="Total Loads")
        st.plotly_chart(fig2, width='stretch')

    # Allow download of summary
    summary = pd.DataFrame({
        "metric": ["Total Paid", "Total Unpaid", "Total Loads"],
        "value": [paid_total, unpaid_total, loads_total]
    })

    st.download_button("Download summary CSV", summary.to_csv(index=False).encode("utf-8"), file_name="koala_summary.csv", mime="text/csv")

    # --- PDF EXPORT: Create a PDF containing the summary and charts (exclude source data) ---
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.units import inch

    def fig_to_png_bytes(fig):
        """Convert a plotly figure to PNG bytes using kaleido."""
        try:
            return fig.to_image(format="png", engine="kaleido")
        except Exception as e:
            # Bubble up a clear error for debugging; in UI we'll show an error message
            raise RuntimeError(f"Failed converting figure to image: {e}")

    def generate_report_pdf(summary_df, figs: dict) -> bytes:
        """Build a PDF in memory with the title, the summary table, and the given figures.
        `figs` is a dict of (label, plotly_figure) pairs. Returns raw PDF bytes.
        """
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        width, height = letter

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2.0, height - inch * 0.75, "Koala Laundry — Operations Report")
        c.setFont("Helvetica", 10)
        c.drawCentredString(width / 2.0, height - inch * 0.95, datetime.now().strftime("Generated: %Y-%m-%d %H:%M:%S"))

        y = height - inch * 1.4

        # Summary table (text-based)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(inch * 0.75, y, "Summary")
        y -= 0.2 * inch
        c.setFont("Helvetica", 10)
        for _, row in summary_df.iterrows():
            metric = str(row["metric"])[:30]
            value = row["value"]
            c.drawString(inch * 0.9, y, f"{metric}: {value}")
            y -= 0.18 * inch
        y -= 0.12 * inch

        # Add each figure on its own region; start new page if needed
        for label, fig in figs.items():
            if fig is None:
                continue
            try:
                img_bytes = fig_to_png_bytes(fig)
                img = ImageReader(io.BytesIO(img_bytes))
                # If not enough space left, start a new page
                if y < inch * 2.0:
                    c.showPage()
                    y = height - inch * 1.0
                c.setFont("Helvetica-Bold", 11)
                c.drawString(inch * 0.75, y, label)
                y -= 0.15 * inch
                # Draw image scaled to page width with margins
                max_width = width - inch * 1.5
                iw, ih = img.getSize()
                scale = min(max_width / iw, (y - inch * 0.5) / ih, 1.0)
                disp_w = iw * scale
                disp_h = ih * scale
                c.drawImage(img, inch * 0.75, y - disp_h, width=disp_w, height=disp_h)
                y -= disp_h + 0.25 * inch
            except Exception as e:
                # Put a small note in the PDF about the failure to include the chart
                c.setFont("Helvetica-Oblique", 9)
                c.drawString(inch * 0.9, y, f"Could not render chart '{label}': {e}")
                y -= 0.18 * inch

        c.save()
        buf.seek(0)
        return buf.read()

    # Collect available figures
    figs_to_export = {"Paid vs Unpaid": fig_pie}
    if 'fig' in locals():
        figs_to_export["Payments over time"] = locals().get('fig')
    if 'fig2' in locals():
        figs_to_export["Total loads by staff"] = locals().get('fig2')

    try:
        pdf_bytes = generate_report_pdf(summary, figs_to_export)
        st.download_button(
            "Download report (PDF)",
            pdf_bytes,
            file_name=f"koala_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        # Show a helpful UI message without exposing a stack trace
        st.error(f"Unable to prepare PDF: {e}. Ensure 'kaleido' and 'reportlab' packages are installed.")

    st.sidebar.markdown("---")
    st.sidebar.info("Run: `streamlit run koala_dashboard.py`")


if __name__ == "__main__":
    # When run directly, ensure a page config is set for this app
    st.set_page_config(page_title="Koala Dashboard", layout="wide")
    render_dashboard() 


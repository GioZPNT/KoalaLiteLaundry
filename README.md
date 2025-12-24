# KoalaLiteLaundry — Dashboard

Quick instructions:

- Install dependencies: `pip install -r requirements.txt` (ensure `streamlit`, `pandas`, `plotly` are installed).
- Run dashboard (from within the project folder):
  - change directory: `cd KoalaLiteLaundry && streamlit run koala_dashboard.py`
  - or run from the repo root using the helper script: `./KoalaLiteLaundry/run_dashboard.sh` (make it executable with `chmod +x KoalaLiteLaundry/run_dashboard.sh`)
  - or run directly using the project's virtualenv Python (no activation required): `./.venv/bin/python -m streamlit run KoalaLiteLaundry/koala_dashboard.py --server.headless true`
- Upload a CSV using the sidebar upload control or provide a local path.
- The CSV should contain (or map to) columns for: `Total Paid`, `Total Unpaid`, and `Total Loads` (column names are flexible). A sample CSV `sample_koala.csv` is included.

If you need help mapping columns, use the sidebar "Column mapping" area.
#!/usr/bin/env bash
# Convenience script to run the dashboard from repo root
# Usage: ./run_dashboard.sh
set -e
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"
streamlit run koala_dashboard.py

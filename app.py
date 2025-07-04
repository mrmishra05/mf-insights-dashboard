import streamlit as st
import pandas as pd
import json
import os

# Import logic directly from comparator.py
from utils.comparator import generate_summary_table

st.set_page_config(page_title="MF Insights Dashboard", layout="wide")
st.title("📊 Mutual Fund Insights – Small & Mid Cap Holdings")

# Auto-generate processed data if it doesn't exist
processed_file = "data/processed/comparison_output.json"

if not os.path.exists(processed_file):
    st.info("Generating comparison data...")
    data = generate_summary_table()
    os.makedirs("data/processed", exist_ok=True)
    with open(processed_file, "w") as f:
        json.dump(data, f, indent=2)
else:
    with open(processed_file) as f:
        data = json.load(f)

# Convert to DataFrames
small_cap_df = pd.DataFrame(data["small_cap"])
mid_cap_df = pd.DataFrame(data["mid_cap"])

# Tabs
tab1, tab2 = st.tabs(["🔹 Top 10 Small Caps", "🔸 Top 10 Mid Caps"])

with tab1:
    st.subheader("Summary: Small Cap Stocks")
    st.dataframe(small_cap_df)
    st.download_button("Download CSV", small_cap_df.to_csv(index=False), "small_cap_summary.csv")

with tab2:
    st.subheader("Summary: Mid Cap Stocks")
    st.dataframe(mid_cap_df)
    st.download_button("Download CSV", mid_cap_df.to_csv(index=False), "mid_cap_summary.csv")

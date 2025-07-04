import streamlit as st
import pandas as pd
import json

from utils.comparator import generate_summary_table

st.set_page_config(page_title="MF Insights Dashboard", layout="wide")

st.title("📊 Mutual Fund Insights – Small & Mid Cap Holdings")

# Load processed data
with open("data/processed/comparison_output.json") as f:
    comparison_data = json.load(f)

small_cap_df = pd.DataFrame(comparison_data["small_cap"])
mid_cap_df = pd.DataFrame(comparison_data["mid_cap"])

tab1, tab2 = st.tabs(["🔹 Top 10 Small Caps", "🔸 Top 10 Mid Caps"])

with tab1:
    st.subheader("Summary: Small Cap Stocks")
    st.dataframe(small_cap_df)
    st.download_button("Download CSV", small_cap_df.to_csv(index=False), "small_cap_summary.csv")

with tab2:
    st.subheader("Summary: Mid Cap Stocks")
    st.dataframe(mid_cap_df)
    st.download_button("Download CSV", mid_cap_df.to_csv(index=False), "mid_cap_summary.csv")

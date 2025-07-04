from scraper.top_stocks import get_top_10_smallcaps, get_top_10_midcaps
from scraper.mf_holdings import load_holdings
import pandas as pd

def generate_summary_table():
    holdings = load_holdings()
    top_small = get_top_10_smallcaps()
    top_mid = get_top_10_midcaps()

    summary = {"small_cap": [], "mid_cap": []}

    for cap_type, top_stocks in [("small_cap", top_small), ("mid_cap", top_mid)]:
        rows = []
        for stock in top_stocks:
            fund_count = 0
            total_percent = 0
            sentiments = []

            for scheme, stocks in holdings.items():
                matched = [s for s in stocks if s["stock"].lower() == stock.lower()]
                if matched:
                    fund_count += 1
                    total_percent += matched[0]["percent_aum"]
                    sentiments.append(matched[0]["sentiment"])

            avg_aum = round(total_percent / fund_count, 2) if fund_count else 0
            dominant_sentiment = max(set(sentiments), key=sentiments.count) if sentiments else "Not Held"

            rows.append({
                "Stock": stock,
                "# Funds Holding": fund_count,
                "Avg % AUM": avg_aum,
                "Sentiment": dominant_sentiment
            })

        summary[cap_type] = rows

    return summary

# Generate and dump to file (used before Streamlit run)
if __name__ == "__main__":
    data = generate_summary_table()
    import json
    with open("data/processed/comparison_output.json", "w") as f:
        json.dump(data, f, indent=2)

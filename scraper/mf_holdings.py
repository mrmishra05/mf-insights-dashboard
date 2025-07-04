import json

def load_holdings():
    with open("data/raw/holdings_sbi.json") as f1, open("data/raw/holdings_hdfc.json") as f2:
        sbi_data = json.load(f1)
        hdfc_data = json.load(f2)
    return {"SBI Small Cap Fund": sbi_data, "HDFC Midcap Opportunities": hdfc_data}

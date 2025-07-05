import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup
import time
import re

# Set page configuration
st.set_page_config(
    page_title="Small & Mid Cap Mutual Fund Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("📊 Small & Mid Cap Mutual Fund Dashboard")
st.markdown("Analyze top mutual fund holdings in small and mid-cap companies")

# Sidebar for configuration
st.sidebar.header("Configuration")

# Google Sheets URL input
google_sheets_url = st.sidebar.text_input(
    "Google Sheets URL",
    value="https://docs.google.com/spreadsheets/d/18ItyhpfgMhM0T3aPAxcpaABgl4oNK7Aj/edit?gid=1216092121#gid=1216092121",
    help="Enter the URL of your Google Sheet containing mutual fund holdings data"
)

# Function to convert Google Sheets URL to CSV export URL
def convert_to_csv_url(sheets_url):
    """Convert Google Sheets URL to CSV export URL"""
    try:
        # Extract the spreadsheet ID from the URL
        if '/d/' in sheets_url:
            sheet_id = sheets_url.split('/d/')[1].split('/')[0]
        else:
            return None
        
        # Extract gid if present
        gid = "0"  # default
        if 'gid=' in sheets_url:
            gid = sheets_url.split('gid=')[1].split('#')[0].split('&')[0]
        
        # Create CSV export URL
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        return csv_url
    except Exception as e:
        st.error(f"Error converting URL: {e}")
        return None

# Function to load data from Google Sheets
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data_from_sheets(sheets_url):
    """Load data from Google Sheets"""
    try:
        csv_url = convert_to_csv_url(sheets_url)
        if not csv_url:
            return None
        
        # Read the CSV data
        df = pd.read_csv(csv_url)
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        return df
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        return None

# Function to get market cap from Yahoo Finance
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_market_cap_yfinance(company_name):
    """Get market cap from Yahoo Finance"""
    try:
        # Search for the ticker symbol
        search_query = f"{company_name} NSE"
        
        # Try different variations of the company name
        variations = [
            company_name,
            company_name.replace(" Ltd.", ""),
            company_name.replace(" Limited", ""),
            company_name.replace("Ltd.", ""),
            company_name.replace("Limited", ""),
            company_name.split()[0] if len(company_name.split()) > 1 else company_name
        ]
        
        for variation in variations:
            try:
                # Try with .NS suffix for NSE
                ticker_ns = f"{variation.upper().replace(' ', '')}.NS"
                stock = yf.Ticker(ticker_ns)
                info = stock.info
                
                if 'marketCap' in info and info['marketCap']:
                    return info['marketCap']
                
                # Try with .BO suffix for BSE
                ticker_bo = f"{variation.upper().replace(' ', '')}.BO"
                stock = yf.Ticker(ticker_bo)
                info = stock.info
                
                if 'marketCap' in info and info['marketCap']:
                    return info['marketCap']
                    
            except:
                continue
                
        return None
    except Exception as e:
        return None

# Function to categorize market cap based on SEBI definitions
def categorize_market_cap(market_cap_value):
    """Categorize market cap based on SEBI definitions (in INR crores)"""
    if market_cap_value is None:
        return "Unknown"
    
    # Convert to crores (assuming market_cap_value is in USD, convert to INR crores)
    # Approximate conversion: 1 USD = 83 INR, 1 crore = 10 million
    market_cap_inr_crores = (market_cap_value * 83) / 10000000
    
    if market_cap_inr_crores >= 20000:  # 20,000 crores and above
        return "Large Cap"
    elif market_cap_inr_crores >= 5000:  # 5,000 to 20,000 crores
        return "Mid Cap"
    else:  # Below 5,000 crores
        return "Small Cap"

# Function to process holdings data
def process_holdings_data(df):
    """Process the holdings data and add market cap categories"""
    if df is None or df.empty:
        return None
    
    # Create a copy to avoid modifying the original
    processed_df = df.copy()
    
    # Add market cap and category columns
    processed_df['Market Cap (USD)'] = None
    processed_df['Market Cap Category'] = None
    
    # Progress bar for market cap fetching
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_stocks = len(processed_df)
    
    for idx, row in processed_df.iterrows():
        if 'Stock Invested in' in row:
            company_name = row['Stock Invested in']
            
            # Update progress
            progress = (idx + 1) / total_stocks
            progress_bar.progress(progress)
            status_text.text(f"Fetching market cap for {company_name}... ({idx + 1}/{total_stocks})")
            
            # Get market cap
            market_cap = get_market_cap_yfinance(company_name)
            processed_df.at[idx, 'Market Cap (USD)'] = market_cap
            processed_df.at[idx, 'Market Cap Category'] = categorize_market_cap(market_cap)
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    return processed_df

# Main app logic
def main():
    # Load data
    if st.sidebar.button("Load Data", type="primary"):
        with st.spinner("Loading data from Google Sheets..."):
            df = load_data_from_sheets(google_sheets_url)
            
            if df is not None:
                st.session_state['raw_data'] = df
                st.success("Data loaded successfully!")
            else:
                st.error("Failed to load data. Please check your Google Sheets URL.")
    
    # Process data if available
    if 'raw_data' in st.session_state:
        df = st.session_state['raw_data']
        
        # Display raw data
        st.subheader("📋 Raw Holdings Data")
        st.dataframe(df, use_container_width=True)
        
        # Process data button
        if st.button("Process Data (Fetch Market Cap)", type="secondary"):
            with st.spinner("Processing data and fetching market cap information..."):
                processed_df = process_holdings_data(df)
                
                if processed_df is not None:
                    st.session_state['processed_data'] = processed_df
                    st.success("Data processed successfully!")
        
        # Display processed data and analysis
        if 'processed_data' in st.session_state:
            processed_df = st.session_state['processed_data']
            
            # Display processed data
            st.subheader("🔍 Processed Holdings Data with Market Cap Categories")
            st.dataframe(processed_df, use_container_width=True)
            
            # Analysis section
            st.subheader("📊 Analysis")
            
            # Filter for Small Cap and Mid Cap only
            small_mid_cap_df = processed_df[
                processed_df['Market Cap Category'].isin(['Small Cap', 'Mid Cap'])
            ].copy()
            
            if not small_mid_cap_df.empty:
                # Summary statistics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_holdings = len(small_mid_cap_df)
                    st.metric("Total Small & Mid Cap Holdings", total_holdings)
                
                with col2:
                    small_cap_count = len(small_mid_cap_df[small_mid_cap_df['Market Cap Category'] == 'Small Cap'])
                    st.metric("Small Cap Holdings", small_cap_count)
                
                with col3:
                    mid_cap_count = len(small_mid_cap_df[small_mid_cap_df['Market Cap Category'] == 'Mid Cap'])
                    st.metric("Mid Cap Holdings", mid_cap_count)
                
                with col4:
                    if '% of Total Holdings' in small_mid_cap_df.columns:
                        total_allocation = small_mid_cap_df['% of Total Holdings'].str.rstrip('%').astype(float).sum()
                        st.metric("Total AUM Allocation", f"{total_allocation:.2f}%")
                
                # Top holdings table
                st.subheader("🏆 Top Small & Mid Cap Holdings")
                
                # Sort by percentage of holdings if available
                if '% of Total Holdings' in small_mid_cap_df.columns:
                    small_mid_cap_df['Holdings %'] = small_mid_cap_df['% of Total Holdings'].str.rstrip('%').astype(float)
                    top_holdings = small_mid_cap_df.nlargest(20, 'Holdings %')
                else:
                    top_holdings = small_mid_cap_df.head(20)
                
                # Display top holdings
                display_columns = ['Stock Invested in', 'Sector', 'Market Cap Category']
                if '% of Total Holdings' in top_holdings.columns:
                    display_columns.append('% of Total Holdings')
                if 'Value(Mn)' in top_holdings.columns:
                    display_columns.append('Value(Mn)')
                
                st.dataframe(
                    top_holdings[display_columns],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Sector-wise analysis
                st.subheader("🏭 Sector-wise Distribution")
                if 'Sector' in small_mid_cap_df.columns:
                    sector_analysis = small_mid_cap_df.groupby('Sector').agg({
                        'Stock Invested in': 'count',
                        'Holdings %': 'sum' if 'Holdings %' in small_mid_cap_df.columns else 'count'
                    }).round(2)
                    sector_analysis.columns = ['Number of Holdings', 'Total Allocation %']
                    sector_analysis = sector_analysis.sort_values('Total Allocation %', ascending=False)
                    
                    st.dataframe(sector_analysis, use_container_width=True)
                
                # Market cap category distribution
                st.subheader("📈 Market Cap Category Distribution")
                cap_distribution = small_mid_cap_df['Market Cap Category'].value_counts()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.bar_chart(cap_distribution)
                
                with col2:
                    if 'Holdings %' in small_mid_cap_df.columns:
                        cap_allocation = small_mid_cap_df.groupby('Market Cap Category')['Holdings %'].sum()
                        st.bar_chart(cap_allocation)
            
            else:
                st.warning("No Small Cap or Mid Cap holdings found in the processed data.")
    
    else:
        st.info("👆 Please load data from your Google Sheet using the sidebar.")
        
        # Instructions
        st.subheader("📖 Instructions")
        st.markdown("""
        1. **Enter your Google Sheets URL** in the sidebar
        2. **Click 'Load Data'** to import your mutual fund holdings
        3. **Click 'Process Data'** to fetch market capitalization data for each stock
        4. **View the analysis** of your small and mid-cap holdings
        
        **Note:** The app will automatically categorize stocks as Small Cap, Mid Cap, or Large Cap based on SEBI definitions:
        - **Large Cap:** ₹20,000+ crores market cap
        - **Mid Cap:** ₹5,000 - ₹20,000 crores market cap  
        - **Small Cap:** Below ₹5,000 crores market cap
        """)

if __name__ == "__main__":
    main()


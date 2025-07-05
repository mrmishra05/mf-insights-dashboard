import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup
import time
import re
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Set page configuration
st.set_page_config(
    page_title="Multi-Scheme Mutual Fund Comparison Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("📊 Multi-Scheme Mutual Fund Comparison Dashboard")
st.markdown("Analyze and compare holdings across multiple mutual fund schemes")

# Sidebar for configuration
st.sidebar.header("Configuration")

# Google Sheets URL input
google_sheets_url = st.sidebar.text_input(
    "Google Sheets URL",
    value="https://docs.google.com/spreadsheets/d/18ItyhpfgMhM0T3aPAxcpaABgl4oNK7Aj/edit?gid=1216092121#gid=1216092121",
    help="Enter the URL of your Google Sheet containing mutual fund holdings data"
)

# Number of sheets to process
num_sheets = st.sidebar.number_input(
    "Number of Sheets to Process",
    min_value=1,
    max_value=20,
    value=10,
    help="Enter the number of sheets in your Google Sheets document"
)

# Function to get all sheet names and IDs from Google Sheets
def get_sheet_info(sheets_url):
    """Extract sheet information from Google Sheets URL"""
    try:
        # Extract the spreadsheet ID from the URL
        if '/d/' in sheets_url:
            sheet_id = sheets_url.split('/d/')[1].split('/')[0]
        else:
            return None, []
        
        # For simplicity, we'll assume sheets are named Sheet1, Sheet2, etc.
        # In a real implementation, you'd want to fetch the actual sheet names
        sheet_info = []
        for i in range(num_sheets):
            gid = str(i * 1000000000 + 1216092121) if i == 0 else str(i * 1000000000)  # Adjust as needed
            sheet_name = f"Sheet{i+1}"
            sheet_info.append({
                'name': sheet_name,
                'gid': gid,
                'url': f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            })
        
        return sheet_id, sheet_info
    except Exception as e:
        st.error(f"Error extracting sheet info: {e}")
        return None, []

# Function to load data from a specific sheet
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_sheet_data(sheet_url, sheet_name):
    """Load data from a specific Google Sheet"""
    try:
        df = pd.read_csv(sheet_url)
        df.columns = df.columns.str.strip()
        df['Sheet_Name'] = sheet_name  # Add sheet identifier
        return df
    except Exception as e:
        st.error(f"Error loading data from {sheet_name}: {e}")
        return None

# Function to load all sheets
def load_all_sheets(sheets_url):
    """Load data from all sheets"""
    sheet_id, sheet_info = get_sheet_info(sheets_url)
    
    if not sheet_id:
        return {}
    
    all_data = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, sheet in enumerate(sheet_info):
        status_text.text(f"Loading {sheet['name']}... ({i+1}/{len(sheet_info)})")
        progress_bar.progress((i + 1) / len(sheet_info))
        
        df = load_sheet_data(sheet['url'], sheet['name'])
        if df is not None:
            all_data[sheet['name']] = df
        
        time.sleep(0.1)  # Small delay to avoid rate limiting
    
    progress_bar.empty()
    status_text.empty()
    
    return all_data

# Function to get market cap from Yahoo Finance
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_market_cap_yfinance(company_name):
    """Get market cap from Yahoo Finance"""
    try:
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

# Function to categorize market cap
def categorize_market_cap(market_cap_value):
    """Categorize market cap based on SEBI definitions"""
    if market_cap_value is None:
        return "Unknown"
    
    market_cap_inr_crores = (market_cap_value * 83) / 10000000
    
    if market_cap_inr_crores >= 20000:
        return "Large Cap"
    elif market_cap_inr_crores >= 5000:
        return "Mid Cap"
    else:
        return "Small Cap"

# Function to process all sheets data
def process_all_sheets_data(all_data):
    """Process data from all sheets and add market cap categories"""
    processed_data = {}
    
    # Get unique stock names across all sheets
    all_stocks = set()
    for sheet_name, df in all_data.items():
        if 'Stock Invested in' in df.columns:
            all_stocks.update(df['Stock Invested in'].dropna().unique())
    
    # Get market cap for all unique stocks
    stock_market_caps = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_stocks_list = list(all_stocks)
    for i, stock in enumerate(all_stocks_list):
        status_text.text(f"Fetching market cap for {stock}... ({i+1}/{len(all_stocks_list)})")
        progress_bar.progress((i + 1) / len(all_stocks_list))
        
        market_cap = get_market_cap_yfinance(stock)
        stock_market_caps[stock] = {
            'market_cap': market_cap,
            'category': categorize_market_cap(market_cap)
        }
        
        time.sleep(0.1)
    
    progress_bar.empty()
    status_text.empty()
    
    # Process each sheet
    for sheet_name, df in all_data.items():
        processed_df = df.copy()
        
        # Add market cap columns
        if 'Stock Invested in' in df.columns:
            processed_df['Market Cap (USD)'] = processed_df['Stock Invested in'].map(
                lambda x: stock_market_caps.get(x, {}).get('market_cap')
            )
            processed_df['Market Cap Category'] = processed_df['Stock Invested in'].map(
                lambda x: stock_market_caps.get(x, {}).get('category')
            )
        
        processed_data[sheet_name] = processed_df
    
    return processed_data

# Function to create comparison analysis
def create_comparison_analysis(processed_data):
    """Create comprehensive comparison analysis"""
    
    # Combine all data
    all_holdings = []
    for sheet_name, df in processed_data.items():
        if 'Stock Invested in' in df.columns:
            df_copy = df.copy()
            df_copy['Scheme'] = sheet_name
            all_holdings.append(df_copy)
    
    if not all_holdings:
        return None
    
    combined_df = pd.concat(all_holdings, ignore_index=True)
    
    # Analysis 1: Common stocks across schemes
    stock_scheme_count = combined_df.groupby('Stock Invested in')['Scheme'].nunique().reset_index()
    stock_scheme_count.columns = ['Stock', 'Number_of_Schemes']
    stock_scheme_count = stock_scheme_count.sort_values('Number_of_Schemes', ascending=False)
    
    # Analysis 2: Holdings comparison with change analysis
    holdings_comparison = []
    
    for stock in stock_scheme_count['Stock'].unique():
        stock_data = combined_df[combined_df['Stock Invested in'] == stock]
        
        # Get market cap category
        market_cap_category = stock_data['Market Cap Category'].iloc[0] if not stock_data.empty else 'Unknown'
        
        stock_analysis = {
            'Stock': stock,
            'Market_Cap_Category': market_cap_category,
            'Number_of_Schemes': len(stock_data),
            'Schemes': ', '.join(stock_data['Scheme'].unique())
        }
        
        # Add scheme-wise holdings data
        for _, row in stock_data.iterrows():
            scheme = row['Scheme']
            
            # Extract percentage holding
            if '% of Total Holdings' in row:
                try:
                    pct_holding = float(str(row['% of Total Holdings']).rstrip('%'))
                    stock_analysis[f'{scheme}_Holdings_%'] = pct_holding
                except:
                    stock_analysis[f'{scheme}_Holdings_%'] = 0
            
            # Extract 1M change
            if '1M Change' in row:
                try:
                    change_1m = float(str(row['1M Change']).rstrip('%'))
                    stock_analysis[f'{scheme}_1M_Change_%'] = change_1m
                except:
                    stock_analysis[f'{scheme}_1M_Change_%'] = 0
            
            # Extract 1Y highest holding
            if '1Y Highest Holding' in row:
                try:
                    highest_1y = float(str(row['1Y Highest Holding']).rstrip('%'))
                    stock_analysis[f'{scheme}_1Y_Highest_%'] = highest_1y
                except:
                    stock_analysis[f'{scheme}_1Y_Highest_%'] = 0
            
            # Extract 1Y lowest holding
            if '1Y Lowest Holding' in row:
                try:
                    lowest_1y = float(str(row['1Y Lowest Holding']).rstrip('%'))
                    stock_analysis[f'{scheme}_1Y_Lowest_%'] = lowest_1y
                except:
                    stock_analysis[f'{scheme}_1Y_Lowest_%'] = 0
        
        holdings_comparison.append(stock_analysis)
    
    holdings_comparison_df = pd.DataFrame(holdings_comparison)
    
    return {
        'combined_df': combined_df,
        'stock_scheme_count': stock_scheme_count,
        'holdings_comparison': holdings_comparison_df
    }

# Main app logic
def main():
    # Load data
    if st.sidebar.button("Load All Sheets", type="primary"):
        with st.spinner("Loading data from all sheets..."):
            all_data = load_all_sheets(google_sheets_url)
            
            if all_data:
                st.session_state['all_data'] = all_data
                st.success(f"Successfully loaded {len(all_data)} sheets!")
                
                # Display sheet summary
                st.subheader("📄 Loaded Sheets Summary")
                sheet_summary = []
                for sheet_name, df in all_data.items():
                    sheet_summary.append({
                        'Sheet Name': sheet_name,
                        'Total Rows': len(df),
                        'Columns': ', '.join(df.columns.tolist()[:5]) + '...' if len(df.columns) > 5 else ', '.join(df.columns.tolist())
                    })
                
                st.dataframe(pd.DataFrame(sheet_summary), use_container_width=True)
            else:
                st.error("Failed to load data. Please check your Google Sheets URL.")
    
    # Process data if available
    if 'all_data' in st.session_state:
        all_data = st.session_state['all_data']
        
        # Process data button
        if st.button("Process All Data (Fetch Market Cap)", type="secondary"):
            with st.spinner("Processing all sheets and fetching market cap information..."):
                processed_data = process_all_sheets_data(all_data)
                
                if processed_data:
                    st.session_state['processed_data'] = processed_data
                    st.success("All data processed successfully!")
        
        # Display analysis if processed data is available
        if 'processed_data' in st.session_state:
            processed_data = st.session_state['processed_data']
            
            # Create comparison analysis
            with st.spinner("Creating comparison analysis..."):
                analysis_results = create_comparison_analysis(processed_data)
            
            if analysis_results:
                st.subheader("🔍 Comparative Analysis")
                
                # Tab-based layout for different analyses
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "📊 Overview", 
                    "🤝 Common Holdings", 
                    "📈 Holdings Comparison", 
                    "🔄 Change Analysis",
                    "📋 Individual Schemes"
                ])
                
                with tab1:
                    st.markdown("### 📊 Portfolio Overview")
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        total_unique_stocks = len(analysis_results['stock_scheme_count'])
                        st.metric("Total Unique Stocks", total_unique_stocks)
                    
                    with col2:
                        common_stocks = len(analysis_results['stock_scheme_count'][
                            analysis_results['stock_scheme_count']['Number_of_Schemes'] > 1
                        ])
                        st.metric("Common Stocks (>1 scheme)", common_stocks)
                    
                    with col3:
                        max_overlap = analysis_results['stock_scheme_count']['Number_of_Schemes'].max()
                        st.metric("Max Schemes per Stock", max_overlap)
                    
                    with col4:
                        avg_stocks_per_scheme = len(analysis_results['combined_df']) / len(processed_data)
                        st.metric("Avg Stocks per Scheme", f"{avg_stocks_per_scheme:.1f}")
                    
                    # Market cap distribution
                    st.markdown("#### Market Cap Distribution")
                    cap_dist = analysis_results['combined_df']['Market Cap Category'].value_counts()
                    
                    fig = px.pie(
                        values=cap_dist.values, 
                        names=cap_dist.index,
                        title="Market Cap Distribution Across All Holdings"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    st.markdown("### 🤝 Common Holdings Analysis")
                    
                    # Filter for common stocks
                    common_stocks_df = analysis_results['stock_scheme_count'][
                        analysis_results['stock_scheme_count']['Number_of_Schemes'] > 1
                    ].copy()
                    
                    if not common_stocks_df.empty:
                        # Scheme overlap chart
                        fig = px.bar(
                            common_stocks_df.head(20),
                            x='Number_of_Schemes',
                            y='Stock',
                            orientation='h',
                            title="Top 20 Stocks by Number of Schemes"
                        )
                        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Common stocks table
                        st.markdown("#### Common Stocks Details")
                        st.dataframe(common_stocks_df, use_container_width=True)
                    else:
                        st.info("No common stocks found across schemes.")
                
                with tab3:
                    st.markdown("### 📈 Holdings Comparison")
                    
                    # Filter for stocks with multiple schemes
                    multi_scheme_stocks = analysis_results['holdings_comparison'][
                        analysis_results['holdings_comparison']['Number_of_Schemes'] > 1
                    ].copy()
                    
                    if not multi_scheme_stocks.empty:
                        # Stock selection for detailed view
                        selected_stock = st.selectbox(
                            "Select a stock for detailed comparison:",
                            multi_scheme_stocks['Stock'].unique()
                        )
                        
                        if selected_stock:
                            stock_data = multi_scheme_stocks[
                                multi_scheme_stocks['Stock'] == selected_stock
                            ].iloc[0]
                            
                            st.markdown(f"#### {selected_stock}")
                            st.markdown(f"**Market Cap Category:** {stock_data['Market_Cap_Category']}")
                            st.markdown(f"**Present in {stock_data['Number_of_Schemes']} schemes:** {stock_data['Schemes']}")
                            
                            # Extract holdings data for visualization
                            holdings_data = []
                            for col in multi_scheme_stocks.columns:
                                if col.endswith('_Holdings_%'):
                                    scheme = col.replace('_Holdings_%', '')
                                    holding_pct = stock_data[col] if pd.notna(stock_data[col]) else 0
                                    holdings_data.append({
                                        'Scheme': scheme,
                                        'Holding_%': holding_pct
                                    })
                            
                            if holdings_data:
                                holdings_df = pd.DataFrame(holdings_data)
                                holdings_df = holdings_df[holdings_df['Holding_%'] > 0]
                                
                                if not holdings_df.empty:
                                    fig = px.bar(
                                        holdings_df,
                                        x='Scheme',
                                        y='Holding_%',
                                        title=f"Holdings Percentage - {selected_stock}"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                        
                        # Full comparison table
                        st.markdown("#### Full Holdings Comparison")
                        st.dataframe(multi_scheme_stocks, use_container_width=True)
                    else:
                        st.info("No stocks found in multiple schemes.")
                
                with tab4:
                    st.markdown("### 🔄 Change Analysis")
                    
                    # 1M Change analysis
                    st.markdown("#### 1-Month Change Analysis")
                    
                    change_data = []
                    for _, row in analysis_results['holdings_comparison'].iterrows():
                        stock = row['Stock']
                        for col in analysis_results['holdings_comparison'].columns:
                            if col.endswith('_1M_Change_%'):
                                scheme = col.replace('_1M_Change_%', '')
                                change_val = row[col] if pd.notna(row[col]) else 0
                                if change_val != 0:
                                    change_data.append({
                                        'Stock': stock,
                                        'Scheme': scheme,
                                        '1M_Change_%': change_val
                                    })
                    
                    if change_data:
                        change_df = pd.DataFrame(change_data)
                        
                        # Top gainers and losers
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("##### Top Gainers (1M)")
                            top_gainers = change_df.nlargest(10, '1M_Change_%')
                            st.dataframe(top_gainers, use_container_width=True)
                        
                        with col2:
                            st.markdown("##### Top Losers (1M)")
                            top_losers = change_df.nsmallest(10, '1M_Change_%')
                            st.dataframe(top_losers, use_container_width=True)
                        
                        # Change distribution
                        fig = px.histogram(
                            change_df,
                            x='1M_Change_%',
                            nbins=20,
                            title="Distribution of 1-Month Changes"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                with tab5:
                    st.markdown("### 📋 Individual Scheme Analysis")
                    
                    # Scheme selector
                    selected_scheme = st.selectbox(
                        "Select a scheme to analyze:",
                        list(processed_data.keys())
                    )
                    
                    if selected_scheme:
                        scheme_data = processed_data[selected_scheme]
                        
                        # Scheme overview
                        st.markdown(f"#### {selected_scheme} - Overview")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            total_holdings = len(scheme_data)
                            st.metric("Total Holdings", total_holdings)
                        
                        with col2:
                            small_mid_cap = len(scheme_data[
                                scheme_data['Market Cap Category'].isin(['Small Cap', 'Mid Cap'])
                            ])
                            st.metric("Small & Mid Cap", small_mid_cap)
                        
                        with col3:
                            if '% of Total Holdings' in scheme_data.columns:
                                total_allocation = scheme_data['% of Total Holdings'].str.rstrip('%').astype(float).sum()
                                st.metric("Total Allocation", f"{total_allocation:.1f}%")
                        
                        # Holdings table
                        st.markdown("#### Holdings Details")
                        display_columns = ['Stock Invested in', 'Sector', 'Market Cap Category']
                        
                        # Add available columns
                        available_cols = ['% of Total Holdings', '1M Change', '1Y Highest Holding', '1Y Lowest Holding', 'Value(Mn)']
                        for col in available_cols:
                            if col in scheme_data.columns:
                                display_columns.append(col)
                        
                        st.dataframe(
                            scheme_data[display_columns],
                            use_container_width=True
                        )
    
    else:
        st.info("👆 Please load data from all sheets using the sidebar.")
        
        # Instructions
        st.subheader("📖 Instructions")
        st.markdown("""
        1. **Enter your Google Sheets URL** in the sidebar
        2. **Set the number of sheets** you want to process
        3. **Click 'Load All Sheets'** to import data from all sheets
        4. **Click 'Process All Data'** to fetch market cap data and perform analysis
        5. **Explore the different tabs** for comprehensive analysis:
           - **Overview:** Summary statistics and market cap distribution
           - **Common Holdings:** Stocks present in multiple schemes
           - **Holdings Comparison:** Side-by-side comparison of holdings percentages
           - **Change Analysis:** 1-month change trends and patterns
           - **Individual Schemes:** Detailed view of each scheme
        
        **Features:**
        - ✅ Compare holdings across multiple mutual fund schemes
        - ✅ Identify common stocks and their allocation patterns
        - ✅ Analyze 1-month changes and 1-year high/low data
        - ✅ Market cap categorization (Small/Mid/Large Cap)
        - ✅ Interactive visualizations and detailed tables
        """)

if __name__ == "__main__":
    main()

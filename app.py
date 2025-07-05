import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup
import time
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Set page configuration
st.set_page_config(
    page_title="Consolidated Mutual Fund Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("📊 Consolidated Mutual Fund Analysis Dashboard")
st.markdown("Analyze and compare holdings across multiple mutual fund schemes from a single consolidated sheet")

# Sidebar for configuration
st.sidebar.header("Configuration")

# Google Sheets URL input
google_sheets_url = st.sidebar.text_input(
    "Google Sheets URL",
    value="https://docs.google.com/spreadsheets/d/1lXMwJBjmCTKA8RK81fzDwty5IvjQhaDGCZDRkeSqxZc/edit?gid=1477439265#gid=1477439265",
    help="Enter the URL of your consolidated Google Sheet"
)

# Function to convert Google Sheets URL to CSV export URL
def convert_to_csv_url(sheets_url):
    """Convert Google Sheets URL to CSV export URL"""
    try:
        if '/d/' in sheets_url:
            sheet_id = sheets_url.split('/d/')[1].split('/')[0]
            
            # Extract GID if present
            gid = "0"  # Default GID
            if 'gid=' in sheets_url:
                gid = sheets_url.split('gid=')[1].split('&')[0].split('#')[0]
            
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            return csv_url
        else:
            return None
    except Exception as e:
        st.error(f"Error converting URL: {e}")
        return None

# Function to load consolidated data
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_consolidated_data(sheets_url):
    """Load data from consolidated Google Sheet"""
    try:
        csv_url = convert_to_csv_url(sheets_url)
        if not csv_url:
            return None
        
        df = pd.read_csv(csv_url)
        df.columns = df.columns.str.strip()
        
        # Clean data
        df = df.dropna(how='all')  # Remove completely empty rows
        df = df.reset_index(drop=True)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Function to get market cap from Yahoo Finance
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_market_cap_yfinance(company_name):
    """Get market cap from Yahoo Finance"""
    try:
        if pd.isna(company_name) or company_name == "":
            return None
            
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
                ticker_ns = f"{variation.upper().replace(' ', '').replace('.', '')}.NS"
                stock = yf.Ticker(ticker_ns)
                info = stock.info
                
                if 'marketCap' in info and info['marketCap']:
                    return info['marketCap']
                
                # Try with .BO suffix for BSE
                ticker_bo = f"{variation.upper().replace(' ', '').replace('.', '')}.BO"
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
    
    # Convert USD to INR (approximate rate)
    market_cap_inr_crores = (market_cap_value * 83) / 10000000
    
    if market_cap_inr_crores >= 20000:
        return "Large Cap"
    elif market_cap_inr_crores >= 5000:
        return "Mid Cap"
    else:
        return "Small Cap"

# Function to process consolidated data
def process_consolidated_data(df):
    """Process consolidated data and add market cap information"""
    if df is None or df.empty:
        return None
    
    # Identify the scheme column (assuming it's the first column or named 'Scheme')
    scheme_col = None
    stock_col = None
    
    # Try to identify columns automatically
    for col in df.columns:
        if 'scheme' in col.lower() or 'fund' in col.lower():
            scheme_col = col
        elif 'stock' in col.lower() or 'company' in col.lower():
            stock_col = col
    
    # If not found, use the first few columns
    if scheme_col is None and len(df.columns) > 0:
        scheme_col = df.columns[0]
    if stock_col is None and len(df.columns) > 1:
        stock_col = df.columns[1]
    
    if scheme_col is None or stock_col is None:
        st.error("Could not identify scheme and stock columns. Please check your data structure.")
        return None
    
    # Get unique stocks for market cap fetching
    unique_stocks = df[stock_col].dropna().unique()
    
    # Progress bar for market cap fetching
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    stock_market_caps = {}
    
    for i, stock in enumerate(unique_stocks):
        status_text.text(f"Fetching market cap for {stock}... ({i+1}/{len(unique_stocks)})")
        progress_bar.progress((i + 1) / len(unique_stocks))
        
        market_cap = get_market_cap_yfinance(stock)
        stock_market_caps[stock] = {
            'market_cap': market_cap,
            'category': categorize_market_cap(market_cap)
        }
        
        time.sleep(0.1)  # Small delay to avoid rate limiting
    
    progress_bar.empty()
    status_text.empty()
    
    # Add market cap information to dataframe
    processed_df = df.copy()
    processed_df['Market_Cap_USD'] = processed_df[stock_col].map(
        lambda x: stock_market_caps.get(x, {}).get('market_cap')
    )
    processed_df['Market_Cap_Category'] = processed_df[stock_col].map(
        lambda x: stock_market_caps.get(x, {}).get('category')
    )
    
    return processed_df, scheme_col, stock_col

# Function to create comprehensive analysis
def create_comprehensive_analysis(df, scheme_col, stock_col):
    """Create comprehensive analysis of the consolidated data"""
    
    # Basic statistics
    total_entries = len(df)
    unique_schemes = df[scheme_col].nunique()
    unique_stocks = df[stock_col].nunique()
    
    # Scheme-wise statistics
    scheme_stats = df.groupby(scheme_col).agg({
        stock_col: 'count',
        'Market_Cap_Category': lambda x: x.value_counts().to_dict()
    }).reset_index()
    scheme_stats.columns = ['Scheme', 'Total_Holdings', 'Market_Cap_Distribution']
    
    # Stock-wise statistics (which stocks appear in multiple schemes)
    stock_stats = df.groupby(stock_col).agg({
        scheme_col: ['count', 'nunique', list],
        'Market_Cap_Category': 'first'
    }).reset_index()
    stock_stats.columns = ['Stock', 'Total_Appearances', 'Unique_Schemes', 'Scheme_List', 'Market_Cap_Category']
    stock_stats = stock_stats.sort_values('Unique_Schemes', ascending=False)
    
    # Market cap distribution
    market_cap_dist = df['Market_Cap_Category'].value_counts()
    
    # Scheme overlap analysis
    scheme_overlap = df.groupby([scheme_col, stock_col]).size().reset_index(name='Count')
    
    return {
        'basic_stats': {
            'total_entries': total_entries,
            'unique_schemes': unique_schemes,
            'unique_stocks': unique_stocks
        },
        'scheme_stats': scheme_stats,
        'stock_stats': stock_stats,
        'market_cap_dist': market_cap_dist,
        'scheme_overlap': scheme_overlap
    }

# Function to create visualizations
def create_visualizations(analysis_results, df, scheme_col, stock_col):
    """Create various visualizations"""
    
    # 1. Market Cap Distribution
    fig_market_cap = px.pie(
        values=analysis_results['market_cap_dist'].values,
        names=analysis_results['market_cap_dist'].index,
        title="Market Cap Distribution Across All Holdings"
    )
    
    # 2. Scheme-wise Holdings Count
    scheme_counts = df.groupby(scheme_col).size().reset_index(name='Holdings_Count')
    fig_scheme_holdings = px.bar(
        scheme_counts,
        x='Holdings_Count',
        y=scheme_col,
        orientation='h',
        title="Number of Holdings per Scheme"
    )
    fig_scheme_holdings.update_layout(yaxis={'categoryorder': 'total ascending'})
    
    # 3. Common Stocks Analysis
    common_stocks = analysis_results['stock_stats'][
        analysis_results['stock_stats']['Unique_Schemes'] > 1
    ].head(20)
    
    fig_common_stocks = px.bar(
        common_stocks,
        x='Unique_Schemes',
        y='Stock',
        orientation='h',
        title="Top 20 Stocks by Number of Schemes"
    )
    fig_common_stocks.update_layout(yaxis={'categoryorder': 'total ascending'})
    
    # 4. Scheme-wise Market Cap Distribution
    scheme_market_cap = df.groupby([scheme_col, 'Market_Cap_Category']).size().reset_index(name='Count')
    fig_scheme_market_cap = px.bar(
        scheme_market_cap,
        x=scheme_col,
        y='Count',
        color='Market_Cap_Category',
        title="Market Cap Distribution by Scheme"
    )
    fig_scheme_market_cap.update_xaxes(tickangle=45)
    
    return {
        'market_cap_dist': fig_market_cap,
        'scheme_holdings': fig_scheme_holdings,
        'common_stocks': fig_common_stocks,
        'scheme_market_cap': fig_scheme_market_cap
    }

# Main app logic
def main():
    # Load data button
    if st.sidebar.button("Load Consolidated Data", type="primary"):
        with st.spinner("Loading consolidated data..."):
            df = load_consolidated_data(google_sheets_url)
            
            if df is not None and not df.empty:
                st.session_state['raw_data'] = df
                st.success(f"✅ Successfully loaded {len(df)} rows from consolidated sheet")
                
                # Show data preview
                st.subheader("📄 Data Preview")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Show column information
                st.subheader("📋 Column Information")
                col_info = []
                for col in df.columns:
                    col_info.append({
                        'Column': col,
                        'Type': str(df[col].dtype),
                        'Non-Null Count': df[col].notna().sum(),
                        'Unique Values': df[col].nunique()
                    })
                st.dataframe(pd.DataFrame(col_info), use_container_width=True)
                
            else:
                st.error("❌ Failed to load data. Please check your Google Sheets URL.")
    
    # Process data if available
    if 'raw_data' in st.session_state:
        df = st.session_state['raw_data']
        
        # Process data button
        if st.sidebar.button("Process Data & Fetch Market Cap", type="secondary"):
            with st.spinner("Processing data and fetching market cap information..."):
                result = process_consolidated_data(df)
                
                if result is not None:
                    processed_df, scheme_col, stock_col = result
                    st.session_state['processed_data'] = processed_df
                    st.session_state['scheme_col'] = scheme_col
                    st.session_state['stock_col'] = stock_col
                    st.success("✅ Data processed successfully!")
                    
                    # Show processing summary
                    st.subheader("🔄 Processing Summary")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Scheme Column", scheme_col)
                    with col2:
                        st.metric("Stock Column", stock_col)
                    with col3:
                        market_cap_added = processed_df['Market_Cap_USD'].notna().sum()
                        st.metric("Market Cap Found", f"{market_cap_added}/{len(processed_df)}")
    
    # Display analysis if processed data is available
    if 'processed_data' in st.session_state:
        processed_df = st.session_state['processed_data']
        scheme_col = st.session_state['scheme_col']
        stock_col = st.session_state['stock_col']
        
        # Create analysis
        with st.spinner("Creating comprehensive analysis..."):
            analysis_results = create_comprehensive_analysis(processed_df, scheme_col, stock_col)
            visualizations = create_visualizations(analysis_results, processed_df, scheme_col, stock_col)
        
        # Display results in tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Overview",
            "🔍 Scheme Analysis", 
            "🤝 Common Holdings",
            "📈 Market Cap Analysis",
            "🔄 Cross-Scheme Analysis",
            "📋 Raw Data"
        ])
        
        with tab1:
            st.markdown("### 📊 Portfolio Overview")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Entries", analysis_results['basic_stats']['total_entries'])
            with col2:
                st.metric("Unique Schemes", analysis_results['basic_stats']['unique_schemes'])
            with col3:
                st.metric("Unique Stocks", analysis_results['basic_stats']['unique_stocks'])
            with col4:
                common_stocks_count = len(analysis_results['stock_stats'][
                    analysis_results['stock_stats']['Unique_Schemes'] > 1
                ])
                st.metric("Common Stocks", common_stocks_count)
            
            # Market cap distribution
            st.plotly_chart(visualizations['market_cap_dist'], use_container_width=True)
            
            # Scheme holdings
            st.plotly_chart(visualizations['scheme_holdings'], use_container_width=True)
        
        with tab2:
            st.markdown("### 🔍 Individual Scheme Analysis")
            
            # Scheme selector
            selected_scheme = st.selectbox(
                "Select a scheme to analyze:",
                processed_df[scheme_col].unique()
            )
            
            if selected_scheme:
                scheme_data = processed_df[processed_df[scheme_col] == selected_scheme]
                
                # Scheme metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Holdings", len(scheme_data))
                with col2:
                    small_mid_cap = len(scheme_data[
                        scheme_data['Market_Cap_Category'].isin(['Small Cap', 'Mid Cap'])
                    ])
                    st.metric("Small & Mid Cap", small_mid_cap)
                with col3:
                    large_cap = len(scheme_data[scheme_data['Market_Cap_Category'] == 'Large Cap'])
                    st.metric("Large Cap", large_cap)
                
                # Scheme-specific market cap distribution
                scheme_cap_dist = scheme_data['Market_Cap_Category'].value_counts()
                fig_scheme_cap = px.pie(
                    values=scheme_cap_dist.values,
                    names=scheme_cap_dist.index,
                    title=f"Market Cap Distribution - {selected_scheme}"
                )
                st.plotly_chart(fig_scheme_cap, use_container_width=True)
                
                # Holdings table
                st.markdown("#### Holdings Details")
                st.dataframe(scheme_data, use_container_width=True)
        
        with tab3:
            st.markdown("### 🤝 Common Holdings Analysis")
            
            # Common stocks visualization
            st.plotly_chart(visualizations['common_stocks'], use_container_width=True)
            
            # Detailed common stocks table
            common_stocks_df = analysis_results['stock_stats'][
                analysis_results['stock_stats']['Unique_Schemes'] > 1
            ].copy()
            
            if not common_stocks_df.empty:
                st.markdown("#### Common Stocks Details")
                
                # Expand scheme lists for better readability
                common_stocks_df['Schemes'] = common_stocks_df['Scheme_List'].apply(
                    lambda x: ', '.join(x) if isinstance(x, list) else str(x)
                )
                
                display_df = common_stocks_df[['Stock', 'Unique_Schemes', 'Market_Cap_Category', 'Schemes']]
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info("No common stocks found across schemes.")
        
        with tab4:
            st.markdown("### 📈 Market Cap Analysis")
            
            # Market cap distribution by scheme
            st.plotly_chart(visualizations['scheme_market_cap'], use_container_width=True)
            
            # Market cap statistics
            st.markdown("#### Market Cap Statistics by Scheme")
            market_cap_stats = processed_df.groupby(scheme_col)['Market_Cap_Category'].value_counts().unstack(fill_value=0)
            market_cap_stats['Total'] = market_cap_stats.sum(axis=1)
            
            # Calculate percentages
            for col in market_cap_stats.columns[:-1]:
                market_cap_stats[f'{col}_Pct'] = (market_cap_stats[col] / market_cap_stats['Total'] * 100).round(1)
            
            st.dataframe(market_cap_stats, use_container_width=True)
        
        with tab5:
            st.markdown("### 🔄 Cross-Scheme Analysis")
            
            # Stock overlap heatmap
            st.markdown("#### Stock Overlap Between Schemes")
            
            # Create overlap matrix
            schemes = processed_df[scheme_col].unique()
            overlap_matrix = pd.DataFrame(index=schemes, columns=schemes)
            
            for scheme1 in schemes:
                stocks1 = set(processed_df[processed_df[scheme_col] == scheme1][stock_col])
                for scheme2 in schemes:
                    stocks2 = set(processed_df[processed_df[scheme_col] == scheme2][stock_col])
                    overlap = len(stocks1.intersection(stocks2))
                    overlap_matrix.loc[scheme1, scheme2] = overlap
            
            # Convert to numeric
            overlap_matrix = overlap_matrix.astype(float)
            
            # Create heatmap
            fig_heatmap = px.imshow(
                overlap_matrix,
                title="Stock Overlap Matrix Between Schemes",
                labels=dict(x="Scheme", y="Scheme", color="Common Stocks"),
                aspect="auto"
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            # Overlap statistics
            st.markdown("#### Overlap Statistics")
            overlap_stats = []
            for i, scheme1 in enumerate(schemes):
                for j, scheme2 in enumerate(schemes):
                    if i < j:  # Only upper triangle
                        overlap = overlap_matrix.loc[scheme1, scheme2]
                        overlap_stats.append({
                            'Scheme 1': scheme1,
                            'Scheme 2': scheme2,
                            'Common Stocks': int(overlap)
                        })
            
            overlap_stats_df = pd.DataFrame(overlap_stats).sort_values('Common Stocks', ascending=False)
            st.dataframe(overlap_stats_df, use_container_width=True)
        
        with tab6:
            st.markdown("### 📋 Raw Data")
            
            # Filters
            st.markdown("#### Filters")
            col1, col2 = st.columns(2)
            
            with col1:
                scheme_filter = st.multiselect(
                    "Filter by Scheme:",
                    processed_df[scheme_col].unique(),
                    default=[]
                )
            
            with col2:
                market_cap_filter = st.multiselect(
                    "Filter by Market Cap Category:",
                    processed_df['Market_Cap_Category'].unique(),
                    default=[]
                )
            
            # Apply filters
            filtered_df = processed_df.copy()
            if scheme_filter:
                filtered_df = filtered_df[filtered_df[scheme_col].isin(scheme_filter)]
            if market_cap_filter:
                filtered_df = filtered_df[filtered_df['Market_Cap_Category'].isin(market_cap_filter)]
            
            # Display filtered data
            st.markdown(f"#### Filtered Data ({len(filtered_df)} rows)")
            st.dataframe(filtered_df, use_container_width=True)
            
            # Download button
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download Filtered Data as CSV",
                data=csv,
                file_name=f"mutual_fund_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    else:
        st.info("👆 Please load and process data using the sidebar buttons.")
        
        # Instructions
        st.subheader("📖 Instructions")
        st.markdown("""
        ## How to Use This Dashboard
        
        1. **Load Data**: Click 'Load Consolidated Data' to import your consolidated sheet
        2. **Process Data**: Click 'Process Data & Fetch Market Cap' to enrich data with market cap information
        3. **Explore Analysis**: Navigate through different tabs for comprehensive analysis
        
        ## Expected Data Format
        Your consolidated sheet should have:
        - **First column**: Scheme/Fund names
        - **Second column**: Stock/Company names  
        - **Additional columns**: Any other relevant data (holdings %, sector, etc.)
        
        ## Features
        - ✅ **Automatic column detection** for schemes and stocks
        - ✅ **Market cap categorization** (Small/Mid/Large Cap)
        - ✅ **Cross-scheme analysis** and overlap detection
        - ✅ **Interactive visualizations** with filtering capabilities
        - ✅ **Data export** functionality
        - ✅ **Comprehensive statistics** and insights
        
        ## Sample Analysis Includes
        - Portfolio overview with key metrics
        - Individual scheme analysis
        - Common holdings identification
        - Market cap distribution analysis
        - Cross-scheme overlap heatmap
        - Raw data with filtering options
        """)

if __name__ == "__main__":
    main()

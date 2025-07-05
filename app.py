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

# Function to process consolidated data without market cap fetching
def process_consolidated_data_basic(df):
    """Process consolidated data without market cap information"""
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
    
    # Add placeholder market cap columns
    processed_df = df.copy()
    processed_df['Market_Cap_Category'] = 'Not Available'
    
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
        stock_col: 'count'
    }).reset_index()
    scheme_stats.columns = ['Scheme', 'Total_Holdings']
    
    # Stock-wise statistics (which stocks appear in multiple schemes)
    stock_stats = df.groupby(stock_col).agg({
        scheme_col: ['count', 'nunique', list]
    }).reset_index()
    stock_stats.columns = ['Stock', 'Total_Appearances', 'Unique_Schemes', 'Scheme_List']
    stock_stats = stock_stats.sort_values('Unique_Schemes', ascending=False)
    
    # Market cap distribution (will show "Not Available" for all)
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
    
    # 1. Scheme-wise Holdings Count
    scheme_counts = df.groupby(scheme_col).size().reset_index(name='Holdings_Count')
    fig_scheme_holdings = px.bar(
        scheme_counts,
        x='Holdings_Count',
        y=scheme_col,
        orientation='h',
        title="Number of Holdings per Scheme"
    )
    fig_scheme_holdings.update_layout(yaxis={'categoryorder': 'total ascending'})
    
    # 2. Common Stocks Analysis
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
    
    # 3. Holdings distribution
    holdings_dist = df.groupby(scheme_col).size().reset_index(name='Count')
    fig_holdings_dist = px.pie(
        holdings_dist,
        values='Count',
        names=scheme_col,
        title="Holdings Distribution Across Schemes"
    )
    
    return {
        'scheme_holdings': fig_scheme_holdings,
        'common_stocks': fig_common_stocks,
        'holdings_dist': fig_holdings_dist
    }

# Main app logic
def main():
    # Load data button
    if st.sidebar.button("Load Consolidated Data", type="primary"):
        with st.spinner("Loading consolidated data..."):
            df = load_consolidated_data(google_sheets_url)
            
            if df is not None and not df.empty:
                # Automatically process the data
                with st.spinner("Processing data..."):
                    result = process_consolidated_data_basic(df)
                    
                    if result is not None:
                        processed_df, scheme_col, stock_col = result
                        st.session_state['processed_data'] = processed_df
                        st.session_state['scheme_col'] = scheme_col
                        st.session_state['stock_col'] = stock_col
                        st.session_state['raw_data'] = df
                        
                        st.success(f"✅ Successfully loaded and processed {len(df)} rows from consolidated sheet")
                        
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
                        
                        # Show processing summary
                        st.subheader("🔄 Processing Summary")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Scheme Column", scheme_col)
                        with col2:
                            st.metric("Stock Column", stock_col)
                        with col3:
                            st.metric("Total Entries", len(processed_df))
                        
                        # Automatically trigger rerun to show the dashboard
                        st.rerun()
                    else:
                        st.error("❌ Failed to process data. Please check your data structure.")
            else:
                st.error("❌ Failed to load data. Please check your Google Sheets URL.")
    
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
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Overview",
            "🔍 Scheme Analysis", 
            "🤝 Common Holdings",
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
            
            # Holdings distribution
            st.plotly_chart(visualizations['holdings_dist'], use_container_width=True)
            
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
                    st.metric("Unique Stocks", scheme_data[stock_col].nunique())
                with col3:
                    # Count how many of this scheme's stocks appear in other schemes
                    scheme_stocks = set(scheme_data[stock_col])
                    other_schemes_stocks = set(processed_df[processed_df[scheme_col] != selected_scheme][stock_col])
                    common_with_others = len(scheme_stocks.intersection(other_schemes_stocks))
                    st.metric("Stocks in Other Schemes", common_with_others)
                
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
                
                display_df = common_stocks_df[['Stock', 'Unique_Schemes', 'Schemes']]
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info("No common stocks found across schemes.")
        
        with tab4:
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
        
        with tab5:
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
                if stock_col in processed_df.columns:
                    stock_filter = st.multiselect(
                        "Filter by Stock:",
                        processed_df[stock_col].unique()[:50],  # Limit to first 50 for performance
                        default=[]
                    )
                else:
                    stock_filter = []
            
            # Apply filters
            filtered_df = processed_df.copy()
            if scheme_filter:
                filtered_df = filtered_df[filtered_df[scheme_col].isin(scheme_filter)]
            if stock_filter:
                filtered_df = filtered_df[filtered_df[stock_col].isin(stock_filter)]
            
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
        st.info("👆 Please load your consolidated data using the sidebar button.")
        
        # Instructions
        st.subheader("📖 Instructions")
        st.markdown("""
        ## How to Use This Dashboard
        
        1. **Enter Google Sheets URL**: Paste your consolidated sheet URL in the sidebar
        2. **Load Data**: Click 'Load Consolidated Data' to import and automatically process your data
        3. **Explore Analysis**: Navigate through different tabs for comprehensive analysis
        
        ## Expected Data Format
        Your consolidated sheet should have:
        - **First column**: Scheme/Fund names
        - **Second column**: Stock/Company names  
        - **Additional columns**: Any other relevant data (holdings %, sector, etc.)
        
        ## Features
        - ✅ **Automatic processing** - No manual steps required
        - ✅ **Automatic column detection** for schemes and stocks
        - ✅ **Cross-scheme analysis** and overlap detection
        - ✅ **Interactive visualizations** with filtering capabilities
        - ✅ **Data export** functionality
        - ✅ **Comprehensive statistics** and insights
        
        ## Sample Analysis Includes
        - Portfolio overview with key metrics
        - Individual scheme analysis
        - Common holdings identification
        - Cross-scheme overlap heatmap
        - Raw data with filtering options
        
        **Note**: Market cap analysis has been disabled for faster processing. Data loads automatically after clicking 'Load Consolidated Data'.
        """)

# Optional: Add market cap fetching as a separate feature
if 'processed_data' in st.session_state:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Optional Features")
    
    if st.sidebar.button("🔍 Fetch Market Cap Data", help="This will take time as it fetches market cap for each stock"):
        # Here you can add the market cap fetching logic if needed
        st.sidebar.info("Market cap fetching feature can be added here if needed")

if __name__ == "__main__":
    main()

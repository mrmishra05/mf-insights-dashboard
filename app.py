import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# Set page configuration
st.set_page_config(
    page_title="🎯 Smart Mutual Fund Analysis Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .conviction-high { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .conviction-medium { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .conviction-low { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
</style>
""", unsafe_allow_html=True)

# Title with enhanced styling
st.markdown("""
# 🎯 Smart Mutual Fund Analysis Dashboard
### Discover High-Conviction Picks & Portfolio Convergence Insights
""")

# Sidebar for configuration
st.sidebar.header("🎛️ Dashboard Controls")

# Google Sheets URL input
google_sheets_url = st.sidebar.text_input(
    "📊 Google Sheets URL",
    value="https://docs.google.com/spreadsheets/d/1lXMwJBjmCTKA8RK81fzDwty5IvjQhaDGCZDRkeSqxZc/edit?gid=1272310356#gid=1272310356",
    help="Enter the URL of your consolidated Google Sheet"
)

# Function to convert Google Sheets URL to CSV export URL
def convert_to_csv_url(sheets_url):
    """Convert Google Sheets URL to CSV export URL"""
    try:
        if '/d/' in sheets_url:
            sheet_id = sheets_url.split('/d/')[1].split('/')[0]
            gid = "0"
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
@st.cache_data(ttl=300)
def load_consolidated_data(sheets_url):
    """Load data from consolidated Google Sheet"""
    try:
        csv_url = convert_to_csv_url(sheets_url)
        if not csv_url:
            return None
           
        df = pd.read_csv(csv_url)
        df.columns = df.columns.str.strip()
        df = df.dropna(how='all')
        df = df.reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Enhanced data processing function
def process_consolidated_data_enhanced(df):
    """Enhanced processing with conviction analysis, data type, and fund type derivation"""
    if df is None or df.empty:
        return None
       
    # Auto-detect columns
    scheme_col = None
    stock_col = None
    data_type_col = None
       
    for col in df.columns:
        if 'scheme' in col.lower() or 'fund' in col.lower():
            scheme_col = col
        elif 'stock' in col.lower() or 'company' in col.lower():
            stock_col = col
        elif 'data type' in col.lower() or 'type' in col.lower() and ('holdings' in df[col].astype(str).str.lower().unique() or 'new' in df[col].astype(str).str.lower().unique()):
            data_type_col = col
           
    if scheme_col is None and len(df.columns) > 0:
        scheme_col = df.columns[0]
    if stock_col is None and len(df.columns) > 1:
        stock_col = df.columns[1]
    if data_type_col is None:
        st.warning("Could not auto-detect 'Data Type' column. Please ensure it's present and correctly named.")
        # Attempt to use a common default if not found
        if 'Data Type' in df.columns:
            data_type_col = 'Data Type'
        else:
            st.warning("No 'Data Type' column found. Additions/Removals analysis will not be available.")


    if scheme_col is None or stock_col is None:
        st.error("Could not identify scheme and stock columns. Please ensure your sheet has 'Scheme/Fund' and 'Stock/Company' columns.")
        return None
       
    processed_df = df.copy()

    # Normalize 'Data Type' column values if found
    if data_type_col:
        processed_df[data_type_col] = processed_df[data_type_col].astype(str).str.strip().str.lower()
        processed_df['Is_New_Addition'] = processed_df[data_type_col] == 'new'
        processed_df['Is_Removed'] = processed_df[data_type_col] == 'removed'
    else:
        processed_df['Is_New_Addition'] = False
        processed_df['Is_Removed'] = False

    # Derive 'Fund_Type' based on scheme names
    def derive_fund_type(scheme_name):
        scheme_name_lower = str(scheme_name).lower()
        if 'smallcap' in scheme_name_lower or 'small cap' in scheme_name_lower:
            return 'Small Cap'
        elif 'midcap' in scheme_name_lower or 'mid cap' in scheme_name_lower:
            return 'Mid Cap'
        elif 'largecap' in scheme_name_lower or 'large cap' in scheme_name_lower:
            return 'Large Cap'
        elif 'value' in scheme_name_lower:
            return 'Value Fund'
        elif 'flexi' in scheme_name_lower or 'flexicap' in scheme_name_lower:
            return 'Flexi Cap'
        elif 'multi cap' in scheme_name_lower or 'multicap' in scheme_name_lower:
            return 'Multi Cap'
        elif 'momentum' in scheme_name_lower:
            return 'Momentum Fund'
        elif 'focused' in scheme_name_lower:
            return 'Focused Fund'
        elif 'balanced' in scheme_name_lower or 'hybrid' in scheme_name_lower:
            return 'Hybrid Fund'
        else:
            return 'Other'

    processed_df['Fund_Type'] = processed_df[scheme_col].apply(derive_fund_type)

    # Calculate conviction metrics
    stock_conviction = processed_df.groupby(stock_col).agg({
        scheme_col: ['count', 'nunique', list]
    }).reset_index()
    stock_conviction.columns = ['Stock', 'Total_Appearances', 'Scheme_Count', 'Schemes_List']
       
    # Calculate conviction score (percentage of schemes holding this stock)
    total_schemes = processed_df[scheme_col].nunique()
    stock_conviction['Conviction_Score'] = (stock_conviction['Scheme_Count'] / total_schemes * 100).round(1)
       
    # Categorize conviction levels
    def get_conviction_category(score):
        if score >= 50:
            return "🟢 High Conviction"
        elif score >= 25:
            return "🟡 Medium Conviction"
        else:
            return "🔵 Low Conviction"
           
    stock_conviction['Conviction_Category'] = stock_conviction['Conviction_Score'].apply(get_conviction_category)
       
    # Sort by conviction score
    stock_conviction = stock_conviction.sort_values('Conviction_Score', ascending=False)
       
    processed_df['Market_Cap_Category'] = 'Not Available' # Placeholder for future enhancement
       
    return processed_df, scheme_col, stock_col, data_type_col, stock_conviction, total_schemes

# Function to create conviction gauge (kept for potential use, but not directly used in new tabs)
def create_conviction_gauge(conviction_score, title):
    """Create a conviction gauge chart"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = conviction_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 16}},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 25], 'color': "lightgray"},
                {'range': [25, 50], 'color': "yellow"},
                {'range': [50, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    fig.update_layout(height=300)
    return fig

# Function to create enhanced visualizations
def create_enhanced_visualizations(stock_conviction, df, scheme_col, stock_col, min_schemes, selected_fund_type):
    """Create enhanced interactive visualizations, now with fund type filter"""
       
    # Apply fund type filter to the main DataFrame first, then recalculate conviction for relevant stocks
    if selected_fund_type and selected_fund_type != "All":
        filtered_df_by_fund_type = df[df['Fund_Type'] == selected_fund_type]
        
        # Recalculate conviction based only on selected fund type schemes
        if not filtered_df_by_fund_type.empty:
            temp_stock_conviction = filtered_df_by_fund_type.groupby(stock_col).agg({
                scheme_col: ['count', 'nunique', list]
            }).reset_index()
            temp_stock_conviction.columns = ['Stock', 'Total_Appearances', 'Scheme_Count', 'Schemes_List']
            
            total_schemes_in_type = filtered_df_by_fund_type[scheme_col].nunique()
            if total_schemes_in_type > 0:
                temp_stock_conviction['Conviction_Score'] = (temp_stock_conviction['Scheme_Count'] / total_schemes_in_type * 100).round(1)
            else:
                temp_stock_conviction['Conviction_Score'] = 0
            
            def get_conviction_category(score): # Redefine locally to avoid global dependency issues if not passed
                if score >= 50: return "🟢 High Conviction"
                elif score >= 25: return "🟡 Medium Conviction"
                else: return "🔵 Low Conviction"

            temp_stock_conviction['Conviction_Category'] = temp_stock_conviction['Conviction_Score'].apply(get_conviction_category)
            stock_conviction_for_charts = temp_stock_conviction.sort_values('Conviction_Score', ascending=False)
        else:
            stock_conviction_for_charts = pd.DataFrame(columns=stock_conviction.columns) # Empty if no data
    else:
        stock_conviction_for_charts = stock_conviction.copy() # Use original if no filter

    # Filter based on minimum schemes
    filtered_conviction = stock_conviction_for_charts[stock_conviction_for_charts['Scheme_Count'] >= min_schemes].copy()
       
    # 1. High Conviction Stocks Bar Chart
    fig_conviction = px.bar(
        filtered_conviction.head(20),
        x='Conviction_Score',
        y='Stock',
        color='Conviction_Category',
        title=f"🎯 Top 20 High Conviction Stocks (Min {min_schemes} Schemes, Type: {selected_fund_type})",
        labels={'Conviction_Score': 'Conviction Score (%)', 'Stock': 'Stock'},
        color_discrete_map={
            "🟢 High Conviction": "#38ef7d",
            "🟡 Medium Conviction": "#f5576c", 
            "🔵 Low Conviction": "#4facfe"
        }
    )
    fig_conviction.update_layout(yaxis={'categoryorder': 'total ascending'})
       
    # 2. Conviction Distribution
    conviction_dist = filtered_conviction['Conviction_Category'].value_counts()
    fig_dist = px.pie(
        values=conviction_dist.values,
        names=conviction_dist.index,
        title=f"🎯 Conviction Distribution (Min {min_schemes} Schemes, Type: {selected_fund_type})",
        color_discrete_map={
            "🟢 High Conviction": "#38ef7d",
            "🟡 Medium Conviction": "#f5576c",
            "🔵 Low Conviction": "#4facfe"
        }
    )
       
    # 3. Scheme Overlap Heatmap (always based on full dataset to show overall convergence)
    schemes = df[scheme_col].unique()
    overlap_matrix = pd.DataFrame(index=schemes, columns=schemes)
       
    for scheme1 in schemes:
        stocks1 = set(df[df[scheme_col] == scheme1][stock_col])
        for scheme2 in schemes:
            stocks2 = set(df[df[scheme_col] == scheme2][stock_col])
            overlap = len(stocks1.intersection(stocks2))
            overlap_matrix.loc[scheme1, scheme2] = overlap
       
    overlap_matrix = overlap_matrix.astype(float)
       
    fig_heatmap = px.imshow(
        overlap_matrix,
        title="🔄 Portfolio Convergence Heatmap",
        labels=dict(x="Scheme", y="Scheme", color="Common Stocks"),
        aspect="auto",
        color_continuous_scale="Viridis"
    )
       
    return fig_conviction, fig_dist, fig_heatmap, filtered_conviction


# Main app logic
def main():
    # Load data button
    if st.sidebar.button("🚀 Load & Analyze Data", type="primary"):
        with st.spinner("Loading and analyzing data..."):
            df = load_consolidated_data(google_sheets_url)
               
            if df is not None and not df.empty:
                result = process_consolidated_data_enhanced(df)
                   
                if result is not None:
                    processed_df, scheme_col, stock_col, data_type_col, stock_conviction, total_schemes = result
                       
                    # Store in session state
                    st.session_state['processed_data'] = processed_df
                    st.session_state['scheme_col'] = scheme_col
                    st.session_state['stock_col'] = stock_col
                    st.session_state['data_type_col'] = data_type_col
                    st.session_state['stock_conviction'] = stock_conviction
                    st.session_state['total_schemes'] = total_schemes
                    st.session_state['raw_data'] = df
                       
                    st.success(f"✅ Successfully analyzed {len(df)} holdings across {total_schemes} schemes")
                    st.rerun()
                else:
                    st.error("❌ Failed to process data")
            else:
                st.error("❌ Failed to load data. Please check the URL and sheet content.")
           
    # Display enhanced dashboard if data is available
    if 'processed_data' in st.session_state:
        processed_df = st.session_state['processed_data']
        scheme_col = st.session_state['scheme_col']
        stock_col = st.session_state['stock_col']
        data_type_col = st.session_state['data_type_col']
        stock_conviction = st.session_state['stock_conviction']
        total_schemes = st.session_state['total_schemes']
           
        # Interactive Controls
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎛️ Analysis Controls")
           
        # Conviction threshold slider
        min_schemes = st.sidebar.slider(
            "🎯 Minimum Schemes for High Conviction",
            min_value=1, # Changed min_value to 1 to allow for more granular filtering
            max_value=max(1, min(15, total_schemes)), # Ensure max_value is at least 1
            value=max(1, min(5, total_schemes)), # Ensure value is at least 1
            help="Stocks held by at least this many schemes"
        )
           
        # Conviction score threshold
        min_conviction_score = st.sidebar.slider(
            "📊 Minimum Conviction Score (%)",
            min_value=0,
            max_value=100,
            value=20,
            help="Minimum percentage of schemes holding the stock"
        )

        # New Fund Type Filter
        fund_types = ["All"] + sorted(processed_df['Fund_Type'].unique().tolist())
        selected_fund_type = st.sidebar.selectbox(
            "📈 Filter by Fund Type (Derived)",
            options=fund_types,
            help="Filter high conviction picks by fund category."
        )
           
        # Generate enhanced visualizations
        fig_conviction, fig_dist, fig_heatmap, filtered_conviction = create_enhanced_visualizations(
            stock_conviction, processed_df, scheme_col, stock_col, min_schemes, selected_fund_type
        )
           
        # Dashboard Tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([ # Added a new tab
            "🏠 Executive Summary",
            "🎯 High Conviction Picks", 
            "🆕 Additions & Removals", # New Tab
            "🔄 Portfolio Convergence",
            "📈 Concentration Analysis",
            "📋 Data Explorer"
        ])
           
        with tab1:
            st.markdown("## 🏠 Executive Summary")
               
            # Key Metrics
            col1, col2, col3, col4 = st.columns(4)
               
            with col1:
                st.metric("Total Schemes", total_schemes)
               
            with col2:
                unique_stocks = processed_df[stock_col].nunique()
                st.metric("Unique Stocks", unique_stocks)
               
            with col3:
                high_conviction_count = len(stock_conviction[stock_conviction['Conviction_Score'] >= 50])
                st.metric("🟢 High Conviction Stocks", high_conviction_count)
               
            with col4:
                avg_conviction = stock_conviction['Conviction_Score'].mean()
                st.metric("Average Conviction Score", f"{avg_conviction:.1f}%")
               
            # Top insights
            st.markdown("### 🎯 Key Insights")
               
            # Top conviction stock
            if not stock_conviction.empty:
                top_stock = stock_conviction.iloc[0]
                st.info(f"**🏆 Top Conviction Stock:** {top_stock['Stock']} held by {top_stock['Scheme_Count']} schemes ({top_stock['Conviction_Score']:.1f}%)")
            else:
                st.info("No stocks found for analysis.")
               
            # Conviction distribution
            st.markdown("### 📊 Conviction Distribution Overview")
            col1, col2 = st.columns(2)
               
            with col1:
                st.plotly_chart(fig_dist, use_container_width=True)
               
            with col2:
                # Top 5 conviction stocks gauge
                st.markdown("#### 🎯 Top 5 Conviction Scores")
                if not stock_conviction.empty:
                    for i in range(min(5, len(stock_conviction))):
                        stock = stock_conviction.iloc[i]
                        progress_color = "🟢" if stock['Conviction_Score'] >= 50 else "🟡" if stock['Conviction_Score'] >= 25 else "🔵"
                        st.write(f"{progress_color} **{stock['Stock']}**: {stock['Conviction_Score']:.1f}%")
                        st.progress(stock['Conviction_Score'] / 100)
                else:
                    st.write("No top conviction stocks to display.")
           
        with tab2:
            st.markdown("## 🎯 High Conviction Analysis")
               
            # Filter controls
            col1, col2 = st.columns(2)
               
            with col1:
                st.markdown(f"**Showing stocks held by ≥{min_schemes} schemes**")
               
            with col2:
                st.markdown(f"**Conviction Score ≥{min_conviction_score}%**")
               
            # Apply conviction score filter
            display_conviction = filtered_conviction[
                filtered_conviction['Conviction_Score'] >= min_conviction_score
            ].copy()
               
            # High conviction chart
            st.plotly_chart(fig_conviction, use_container_width=True)
               
            # Detailed conviction table
            st.markdown("### 📋 Detailed Conviction Analysis")
               
            # Prepare display dataframe
            if not display_conviction.empty:
                display_df = display_conviction.copy()
                display_df['Schemes'] = display_df['Schemes_List'].apply(
                    lambda x: ', '.join(x) if isinstance(x, list) else str(x)
                )
                   
                # Style the dataframe
                def style_conviction(val):
                    if "🟢" in val:
                        return 'background-color: #38ef7d; color: white'
                    elif "🟡" in val:
                        return 'background-color: #f5576c; color: white'
                    else:
                        return 'background-color: #4facfe; color: white'
                       
                styled_df = display_df[['Stock', 'Scheme_Count', 'Conviction_Score', 'Conviction_Category', 'Schemes']].style.applymap(
                    style_conviction, subset=['Conviction_Category']
                )
                   
                st.dataframe(styled_df, use_container_width=True)
                   
                # Download high conviction picks
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download High Conviction Picks",
                    data=csv,
                    file_name=f"high_conviction_picks_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No high conviction stocks found with the current filters.")

        with tab3: # New Tab: Additions & Removals
            st.markdown("## 🆕 Additions & Removals Analysis")

            if data_type_col:
                new_additions = processed_df[processed_df['Is_New_Addition'] == True].copy()
                removed_stocks = processed_df[processed_df['Is_Removed'] == True].copy()

                st.markdown("### ✨ New Additions")
                if not new_additions.empty:
                    st.write(f"Found **{len(new_additions)}** new stock additions.")
                    
                    # Group by stock for easier viewing if a stock was added by multiple schemes
                    new_additions_summary = new_additions.groupby(stock_col).agg(
                        Schemes_Adding=(scheme_col, lambda x: list(x)),
                        Number_of_Schemes_Adding=(scheme_col, 'nunique')
                    ).reset_index()
                    new_additions_summary['Schemes_Adding'] = new_additions_summary['Schemes_Adding'].apply(lambda x: ', '.join(x))
                    new_additions_summary = new_additions_summary.sort_values('Number_of_Schemes_Adding', ascending=False)

                    st.dataframe(new_additions_summary, use_container_width=True)
                    csv_additions = new_additions_summary.to_csv(index=False)
                    st.download_button(
                        label="📥 Download New Additions",
                        data=csv_additions,
                        file_name=f"new_additions_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No new stock additions found in the data.")

                st.markdown("### 🗑️ Removed Stocks")
                if not removed_stocks.empty:
                    st.write(f"Found **{len(removed_stocks)}** removed stocks.")

                    # Group by stock for easier viewing if a stock was removed by multiple schemes
                    removed_summary = removed_stocks.groupby(stock_col).agg(
                        Schemes_Removing=(scheme_col, lambda x: list(x)),
                        Number_of_Schemes_Removing=(scheme_col, 'nunique')
                    ).reset_index()
                    removed_summary['Schemes_Removing'] = removed_summary['Schemes_Removing'].apply(lambda x: ', '.join(x))
                    removed_summary = removed_summary.sort_values('Number_of_Schemes_Removing', ascending=False)
                    
                    st.dataframe(removed_summary, use_container_width=True)
                    csv_removals = removed_summary.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Removed Stocks",
                        data=csv_removals,
                        file_name=f"removed_stocks_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No removed stocks found in the data.")
            else:
                st.warning("The 'Data Type' column was not found. Please ensure your Google Sheet has a column named 'Data Type' with values like 'Holdings', 'New', or 'Removed' for this analysis.")


        with tab4: # Original tab3, now tab4
            st.markdown("## 🔄 Portfolio Convergence Analysis")
               
            # Convergence heatmap
            st.plotly_chart(fig_heatmap, use_container_width=True)
               
            # Convergence statistics
            st.markdown("### 📊 Convergence Statistics")
               
            # Calculate convergence metrics
            schemes = processed_df[scheme_col].unique()
            convergence_stats = []
               
            for i, scheme1 in enumerate(schemes):
                for j, scheme2 in enumerate(schemes):
                    if i < j:
                        stocks1 = set(processed_df[processed_df[scheme_col] == scheme1][stock_col])
                        stocks2 = set(processed_df[processed_df[scheme_col] == scheme2][stock_col])
                           
                        common_stocks = len(stocks1.intersection(stocks2))
                        total_unique = len(stocks1.union(stocks2))
                           
                        # Jaccard similarity
                        jaccard_similarity = (common_stocks / total_unique * 100) if total_unique > 0 else 0
                           
                        convergence_stats.append({
                            'Scheme 1': scheme1,
                            'Scheme 2': scheme2,
                            'Common Stocks': common_stocks,
                            'Convergence Score': round(jaccard_similarity, 1)
                        })
               
            convergence_df = pd.DataFrame(convergence_stats).sort_values('Convergence Score', ascending=False)
               
            # Top convergent pairs
            st.markdown("#### 🤝 Most Convergent Scheme Pairs")
            if not convergence_df.empty:
                top_convergent = convergence_df.head(10)
                   
                for _, row in top_convergent.iterrows():
                    score = row['Convergence Score']
                    color = "🟢" if score >= 50 else "🟡" if score >= 25 else "🔵"
                    st.write(f"{color} **{row['Scheme 1']}** ↔ **{row['Scheme 2']}**: {score}% similarity ({row['Common Stocks']} common stocks)")
            else:
                st.info("Not enough schemes to calculate convergence.")
           
        with tab5: # Original tab4, now tab5
            st.markdown("## 📈 Concentration Analysis")
               
            # Scheme-wise concentration
            st.markdown("### 🎯 Scheme-wise Holdings Concentration")
               
            scheme_holdings = processed_df.groupby(scheme_col).size().reset_index(name='Holdings_Count')
            scheme_holdings = scheme_holdings.sort_values('Holdings_Count', ascending=False)
               
            fig_concentration = px.bar(
                scheme_holdings,
                x='Holdings_Count',
                y=scheme_col,
                orientation='h',
                title="📊 Holdings Count by Scheme",
                labels={'Holdings_Count': 'Number of Holdings', scheme_col: 'Scheme'}
            )
            fig_concentration.update_layout(yaxis={'categoryorder': 'total ascending'})
               
            st.plotly_chart(fig_concentration, use_container_width=True)
               
            # Concentration metrics
            col1, col2 = st.columns(2)
               
            with col1:
                st.markdown("#### 📊 Concentration Metrics")
                if not scheme_holdings.empty:
                    avg_holdings = scheme_holdings['Holdings_Count'].mean()
                    max_holdings = scheme_holdings['Holdings_Count'].max()
                    min_holdings = scheme_holdings['Holdings_Count'].min()
                       
                    st.metric("Average Holdings per Scheme", f"{avg_holdings:.1f}")
                    st.metric("Maximum Holdings", max_holdings)
                    st.metric("Minimum Holdings", min_holdings)
                else:
                    st.info("No scheme holdings data available.")
               
            with col2:
                st.markdown("#### 🎯 Risk Assessment")
                if not scheme_holdings.empty:
                    # Calculate concentration risk
                    avg_holdings = scheme_holdings['Holdings_Count'].mean()
                    high_concentration_schemes = scheme_holdings[scheme_holdings['Holdings_Count'] > avg_holdings * 1.5]
                    low_concentration_schemes = scheme_holdings[scheme_holdings['Holdings_Count'] < avg_holdings * 0.5]
                       
                    if not high_concentration_schemes.empty:
                        st.warning(f"⚠️ {len(high_concentration_schemes)} schemes have high concentration (>{avg_holdings*1.5:.0f} holdings)")
                       
                    if not low_concentration_schemes.empty:
                        st.info(f"ℹ️ {len(low_concentration_schemes)} schemes have low concentration (<{avg_holdings*0.5:.0f} holdings)")
                else:
                    st.info("No scheme holdings data to assess risk.")
           
        with tab6: # Original tab5, now tab6
            st.markdown("## 📋 Data Explorer")
               
            # Advanced filters
            st.markdown("### 🔍 Advanced Filters")
               
            col1, col2, col3 = st.columns(3)
               
            with col1:
                scheme_filter = st.multiselect(
                    "Filter by Scheme:",
                    processed_df[scheme_col].unique(),
                    default=[]
                )
               
            with col2:
                stock_filter = st.multiselect(
                    "Filter by Stock:",
                    processed_df[stock_col].unique()[:100], # Limit for performance
                    default=[]
                )
               
            with col3:
                conviction_filter_explorer = st.selectbox( # Renamed to avoid conflict
                    "Filter by Conviction Category:",
                    ["All", "🟢 High Conviction", "🟡 Medium Conviction", "🔵 Low Conviction"],
                    index=0
                )
               
            # Apply filters
            filtered_df_explorer = processed_df.copy() # Renamed to avoid conflict
               
            if scheme_filter:
                filtered_df_explorer = filtered_df_explorer[filtered_df_explorer[scheme_col].isin(scheme_filter)]
               
            if stock_filter:
                filtered_df_explorer = filtered_df_explorer[filtered_df_explorer[stock_col].isin(stock_filter)]
               
            if conviction_filter_explorer != "All":
                conviction_stocks_explorer = stock_conviction[ # Renamed to avoid conflict
                    stock_conviction['Conviction_Category'] == conviction_filter_explorer
                ]['Stock'].tolist()
                filtered_df_explorer = filtered_df_explorer[filtered_df_explorer[stock_col].isin(conviction_stocks_explorer)]
               
            # Display filtered data
            st.markdown(f"### 📊 Filtered Data ({len(filtered_df_explorer)} rows)")
            st.dataframe(filtered_df_explorer, use_container_width=True)
               
            # Download filtered data
            if not filtered_df_explorer.empty:
                csv = filtered_df_explorer.to_csv(index=False)
                st.download_button(
                    label="📥 Download Filtered Data",
                    data=csv,
                    file_name=f"filtered_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
           
    else:
        # Welcome screen
        st.markdown("## 🚀 Welcome to Smart Mutual Fund Analysis")
           
        st.info("👆 Click **'Load & Analyze Data'** in the sidebar to begin analysis")
           
        # Feature highlights
        st.markdown("### ✨ Key Features")
           
        col1, col2 = st.columns(2)
           
        with col1:
            st.markdown("""
            **🎯 High Conviction Analysis**
            - Dynamic threshold controls
            - Conviction scoring system
            - Color-coded insights
            - **NEW: Filter by Fund Type!**
               
            **🆕 Additions & Removals**
            - Track new stock entries
            - Monitor recent stock exits
            - Helps identify emerging trends or concerns
            """)
           
        with col2:
            st.markdown("""
            **🔄 Portfolio Convergence**
            - Scheme similarity analysis
            - Interactive heatmaps
            - Convergence scoring
               
            **📈 Concentration Analysis**
            - Risk assessment metrics
            - Holdings distribution
            - Automated alerts
               
            **📊 Interactive Dashboard**
            - Real-time filtering
            - Export capabilities
            - Mobile-friendly design
            """)

# Gold Mining Analysis Functions (These functions are provided but not yet integrated into the UI.
# You can add a new tab for "Advanced Insights" and use these there if you wish.)
def calculate_conviction_momentum(stock_conviction):
    """Find stocks gaining momentum across schemes"""
    # Calculate momentum score based on scheme adoption rate
    stock_conviction_copy = stock_conviction.copy()
    stock_conviction_copy['Momentum_Score'] = (
        stock_conviction_copy['Scheme_Count'] / stock_conviction_copy['Total_Appearances']
    ) * 100 # This might be total appearances or historical appearances. For now, using total.
    
    # Identify emerging winners
    # This logic assumes 'Total_Appearances' might indicate historical presence.
    # If it's just the current count, this momentum score might not be very meaningful without time-series data.
    # For now, it will identify stocks frequently appearing relative to their total mentions.
    emerging_winners = stock_conviction_copy[
        (stock_conviction_copy['Conviction_Score'] >= 30) & 
        (stock_conviction_copy['Momentum_Score'] >= 80)
    ]
    
    return emerging_winners

def find_hidden_gems(processed_df, stock_conviction, scheme_col, stock_col):
    """Find undervalued high-conviction picks"""
       
    # Stocks held by quality schemes but not mainstream
    # Define "quality schemes" - e.g., schemes with high average conviction in their holdings, or long track record
    # For simplicity, let's consider schemes with above-average holdings count as "quality" for this example.
    scheme_holdings_count = processed_df.groupby(scheme_col).size()
    avg_holdings = scheme_holdings_count.mean()
    quality_schemes = scheme_holdings_count[scheme_holdings_count > avg_holdings].index.tolist()
       
    hidden_gems = []
    for _, stock_row in stock_conviction.iterrows():
        stock = stock_row['Stock']
        stock_schemes = processed_df[processed_df[stock_col] == stock][scheme_col].unique()
           
        # Check if held by quality schemes but low overall conviction
        quality_holdings = len([s for s in stock_schemes if s in quality_schemes])
        conviction_score = stock_row['Conviction_Score']
           
        # Adjust logic for identifying "hidden gems"
        # A stock is a "hidden gem" if it's held by a decent number of quality schemes
        # but its overall conviction score across ALL schemes is not yet very high (indicating it's not mainstream yet)
        if quality_holdings >= 2 and conviction_score < 30: # Held by at least 2 quality schemes, but overall < 30% conviction
            hidden_gems.append({
                'Stock': stock,
                'Quality_Scheme_Count': quality_holdings,
                'Conviction_Score': conviction_score,
                'Schemes_Holding': ', '.join(stock_schemes),
                'Quality_Schemes_Holding': ', '.join([s for s in stock_schemes if s in quality_schemes])
            })
           
    return pd.DataFrame(hidden_gems).sort_values('Conviction_Score', ascending=False) # Sort by conviction for easier review

def detect_consensus_breakouts(stock_conviction, threshold=25):
    """Identify stocks crossing conviction thresholds (implying recent increase in adoption)"""
       
    breakout_stocks = stock_conviction[
        (stock_conviction['Conviction_Score'] >= threshold) &
        (stock_conviction['Scheme_Count'] >= 3) # Minimum 3 schemes to consider a "breakout"
    ].copy()
       
    # This function would be more powerful with historical data to compare current conviction vs. past.
    # For now, it identifies stocks that meet current high conviction criteria and a minimum scheme count.
    breakout_stocks['Breakout_Strength'] = (
        breakout_stocks['Conviction_Score'] * breakout_stocks['Scheme_Count']
    ) / 100
       
    return breakout_stocks.sort_values('Breakout_Strength', ascending=False)

def track_smart_money(processed_df, stock_conviction, scheme_col, stock_col):
    """Identify which schemes are consistently picking winners (high-conviction stocks)"""
       
    scheme_performance = {}
       
    # Define what a "winner" or "high-conviction pick" is
    high_conviction_threshold = 40 # Stocks with conviction score >= 40% are "winners"
    high_conviction_stocks_list = stock_conviction[
        stock_conviction['Conviction_Score'] >= high_conviction_threshold
    ]['Stock'].tolist()

    for scheme in processed_df[scheme_col].unique():
        scheme_holdings_df = processed_df[processed_df[scheme_col] == scheme]
        scheme_stocks = scheme_holdings_df[stock_col].unique()
           
        num_high_conviction_holdings = len(
            [s for s in scheme_stocks if s in high_conviction_stocks_list]
        )
           
        total_holdings_for_scheme = len(scheme_stocks)
        
        # Percentage of scheme's holdings that are high conviction picks
        quality_ratio = (num_high_conviction_holdings / total_holdings_for_scheme * 100) if total_holdings_for_scheme > 0 else 0
           
        scheme_performance[scheme] = {
            'Total_Holdings': total_holdings_for_scheme,
            'High_Conviction_Holdings_Count': num_high_conviction_holdings,
            'Quality_Pick_Ratio': quality_ratio # Percentage of their holdings that are high conviction
        }
           
    return pd.DataFrame(scheme_performance).T.sort_values('Quality_Pick_Ratio', ascending=False)

def create_consensus_portfolio(stock_conviction, top_n=20, min_conviction=30):
    """Create optimal portfolio based on fund manager consensus"""
       
    consensus_picks = stock_conviction[
        stock_conviction['Conviction_Score'] >= min_conviction
    ].head(top_n)
       
    # Calculate optimal weights based on conviction
    if not consensus_picks.empty:
        total_conviction = consensus_picks['Conviction_Score'].sum()
        consensus_picks = consensus_picks.copy()
        consensus_picks['Optimal_Weight'] = (
            consensus_picks['Conviction_Score'] / total_conviction * 100
        ).round(2)
    else:
        consensus_picks['Optimal_Weight'] = 0
       
    return consensus_picks[['Stock', 'Conviction_Score', 'Scheme_Count', 'Optimal_Weight']]

def identify_risk_flags(processed_df, stock_conviction, scheme_col, stock_col):
    """Identify potential risk situations"""
       
    risk_flags = []
       
    # Over-concentration risk (across the entire dataset of holdings)
    total_holdings_entries = len(processed_df) # Total entries in the raw data
    
    # Calculate "overall weight" of each stock in the entire dataset (based on appearances)
    stock_counts = processed_df[stock_col].value_counts(normalize=True) * 100

    for stock, percentage in stock_counts.items():
        if percentage > 10:  # If a single stock accounts for >10% of ALL entries
            risk_flags.append({
                'Stock': stock,
                'Risk_Type': 'Overall Data Concentration',
                'Risk_Level': 'HIGH' if percentage > 20 else 'MEDIUM', # Higher threshold for overall dataset
                'Details': f'{percentage:.1f}% of all holdings entries across all schemes'
            })
       
    # Herd mentality risk (too many schemes holding the same high-conviction stocks)
    high_conviction_stocks = stock_conviction[stock_conviction['Conviction_Score'] > 75] # Very high conviction
    if len(high_conviction_stocks) >= total_schemes * 0.2: # If more than 20% of unique stocks are very high conviction
        risk_flags.append({
            'Stock': 'PORTFOLIO',
            'Risk_Type': 'Herd Mentality / Lack of Diversification',
            'Risk_Level': 'MEDIUM',
            'Details': f'{len(high_conviction_stocks)} stocks with >75% conviction, potentially limiting unique ideas.'
        })

    # Schemes with very few holdings (potential lack of diversification at scheme level)
    scheme_holdings = processed_df.groupby(scheme_col).size()
    schemes_with_few_holdings = scheme_holdings[scheme_holdings < 10] # Example: Schemes with less than 10 holdings
    if not schemes_with_few_holdings.empty:
        for scheme_name, count in schemes_with_few_holdings.items():
             risk_flags.append({
                'Stock': 'N/A',
                'Risk_Type': 'Scheme Under-Diversification',
                'Risk_Level': 'LOW',
                'Details': f'Scheme "{scheme_name}" has only {count} holdings, consider checking its mandate.'
             })
       
    return pd.DataFrame(risk_flags)

def optimize_diversification(processed_df, stock_conviction, scheme_col, stock_col):
    """Find optimal diversification opportunities by identifying underrepresented quality stocks"""
       
    # Find stocks with a decent conviction score (e.g., 20-40%) but not yet "mainstream" (good for diversification)
    underrepresented_quality = stock_conviction[
        (stock_conviction['Conviction_Score'] >= 20) &
        (stock_conviction['Conviction_Score'] < 50) & # Not yet high conviction
        (stock_conviction['Scheme_Count'] >= 3) # Held by at least 3 schemes
    ].copy()
       
    return underrepresented_quality.sort_values('Conviction_Score', ascending=False)


if __name__ == "__main__":
    main()

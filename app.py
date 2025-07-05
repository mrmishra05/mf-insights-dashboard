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
    value="https://docs.google.com/spreadsheets/d/1lXMwJBjmCTKA8RK81fzDwty5IvjQhaDGCZDRkeSqxZc/edit?gid=1477439265#gid=1477439265",
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
    """Enhanced processing with conviction analysis"""
    if df is None or df.empty:
        return None
    
    # Auto-detect columns
    scheme_col = None
    stock_col = None
    
    for col in df.columns:
        if 'scheme' in col.lower() or 'fund' in col.lower():
            scheme_col = col
        elif 'stock' in col.lower() or 'company' in col.lower():
            stock_col = col
    
    if scheme_col is None and len(df.columns) > 0:
        scheme_col = df.columns[0]
    if stock_col is None and len(df.columns) > 1:
        stock_col = df.columns[1]
    
    if scheme_col is None or stock_col is None:
        st.error("Could not identify scheme and stock columns.")
        return None
    
    # Calculate conviction metrics
    stock_conviction = df.groupby(stock_col).agg({
        scheme_col: ['count', 'nunique', list]
    }).reset_index()
    stock_conviction.columns = ['Stock', 'Total_Appearances', 'Scheme_Count', 'Schemes_List']
    
    # Calculate conviction score (percentage of schemes holding this stock)
    total_schemes = df[scheme_col].nunique()
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
    
    processed_df = df.copy()
    processed_df['Market_Cap_Category'] = 'Not Available'
    
    return processed_df, scheme_col, stock_col, stock_conviction, total_schemes

# Function to create conviction gauge
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
def create_enhanced_visualizations(stock_conviction, df, scheme_col, stock_col, min_schemes):
    """Create enhanced interactive visualizations"""
    
    # Filter based on minimum schemes
    filtered_conviction = stock_conviction[stock_conviction['Scheme_Count'] >= min_schemes].copy()
    
    # 1. High Conviction Stocks Bar Chart
    fig_conviction = px.bar(
        filtered_conviction.head(20),
        x='Conviction_Score',
        y='Stock',
        color='Conviction_Category',
        title=f"🎯 Top 20 High Conviction Stocks (Min {min_schemes} Schemes)",
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
        title=f"🎯 Conviction Distribution (Min {min_schemes} Schemes)",
        color_discrete_map={
            "🟢 High Conviction": "#38ef7d",
            "🟡 Medium Conviction": "#f5576c",
            "🔵 Low Conviction": "#4facfe"
        }
    )
    
    # 3. Scheme Overlap Heatmap
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
                    processed_df, scheme_col, stock_col, stock_conviction, total_schemes = result
                    
                    # Store in session state
                    st.session_state['processed_data'] = processed_df
                    st.session_state['scheme_col'] = scheme_col
                    st.session_state['stock_col'] = stock_col
                    st.session_state['stock_conviction'] = stock_conviction
                    st.session_state['total_schemes'] = total_schemes
                    st.session_state['raw_data'] = df
                    
                    st.success(f"✅ Successfully analyzed {len(df)} holdings across {total_schemes} schemes")
                    st.rerun()
                else:
                    st.error("❌ Failed to process data")
            else:
                st.error("❌ Failed to load data")
    
    # Display enhanced dashboard if data is available
    if 'processed_data' in st.session_state:
        processed_df = st.session_state['processed_data']
        scheme_col = st.session_state['scheme_col']
        stock_col = st.session_state['stock_col']
        stock_conviction = st.session_state['stock_conviction']
        total_schemes = st.session_state['total_schemes']
        
        # Interactive Controls
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎛️ Analysis Controls")
        
        # Conviction threshold slider
        min_schemes = st.sidebar.slider(
            "🎯 Minimum Schemes for High Conviction",
            min_value=2,
            max_value=min(15, total_schemes),
            value=min(5, total_schemes),
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
        
        # Generate enhanced visualizations
        fig_conviction, fig_dist, fig_heatmap, filtered_conviction = create_enhanced_visualizations(
            stock_conviction, processed_df, scheme_col, stock_col, min_schemes
        )
        
        # Dashboard Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏠 Executive Summary",
            "🎯 High Conviction Picks", 
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
            top_stock = stock_conviction.iloc[0]
            st.info(f"**🏆 Top Conviction Stock:** {top_stock['Stock']} held by {top_stock['Scheme_Count']} schemes ({top_stock['Conviction_Score']:.1f}%)")
            
            # Conviction distribution
            st.markdown("### 📊 Conviction Distribution Overview")
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(fig_dist, use_container_width=True)
            
            with col2:
                # Top 5 conviction stocks gauge
                st.markdown("#### 🎯 Top 5 Conviction Scores")
                for i in range(min(5, len(stock_conviction))):
                    stock = stock_conviction.iloc[i]
                    progress_color = "🟢" if stock['Conviction_Score'] >= 50 else "🟡" if stock['Conviction_Score'] >= 25 else "🔵"
                    st.write(f"{progress_color} **{stock['Stock']}**: {stock['Conviction_Score']:.1f}%")
                    st.progress(stock['Conviction_Score'] / 100)
        
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
            if not display_df.empty:
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download High Conviction Picks",
                    data=csv,
                    file_name=f"high_conviction_picks_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with tab3:
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
            top_convergent = convergence_df.head(10)
            
            for _, row in top_convergent.iterrows():
                score = row['Convergence Score']
                color = "🟢" if score >= 50 else "🟡" if score >= 25 else "🔵"
                st.write(f"{color} **{row['Scheme 1']}** ↔ **{row['Scheme 2']}**: {score}% similarity ({row['Common Stocks']} common stocks)")
        
        with tab4:
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
                avg_holdings = scheme_holdings['Holdings_Count'].mean()
                max_holdings = scheme_holdings['Holdings_Count'].max()
                min_holdings = scheme_holdings['Holdings_Count'].min()
                
                st.metric("Average Holdings per Scheme", f"{avg_holdings:.1f}")
                st.metric("Maximum Holdings", max_holdings)
                st.metric("Minimum Holdings", min_holdings)
            
            with col2:
                st.markdown("#### 🎯 Risk Assessment")
                
                # Calculate concentration risk
                high_concentration_schemes = scheme_holdings[scheme_holdings['Holdings_Count'] > avg_holdings * 1.5]
                low_concentration_schemes = scheme_holdings[scheme_holdings['Holdings_Count'] < avg_holdings * 0.5]
                
                if not high_concentration_schemes.empty:
                    st.warning(f"⚠️ {len(high_concentration_schemes)} schemes have high concentration (>{avg_holdings*1.5:.0f} holdings)")
                
                if not low_concentration_schemes.empty:
                    st.info(f"ℹ️ {len(low_concentration_schemes)} schemes have low concentration (<{avg_holdings*0.5:.0f} holdings)")
        
        with tab5:
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
                    processed_df[stock_col].unique()[:50],
                    default=[]
                )
            
            with col3:
                conviction_filter = st.selectbox(
                    "Filter by Conviction:",
                    ["All", "🟢 High Conviction", "🟡 Medium Conviction", "🔵 Low Conviction"],
                    index=0
                )
            
            # Apply filters
            filtered_df = processed_df.copy()
            
            if scheme_filter:
                filtered_df = filtered_df[filtered_df[scheme_col].isin(scheme_filter)]
            
            if stock_filter:
                filtered_df = filtered_df[filtered_df[stock_col].isin(stock_filter)]
            
            if conviction_filter != "All":
                conviction_stocks = stock_conviction[
                    stock_conviction['Conviction_Category'] == conviction_filter
                ]['Stock'].tolist()
                filtered_df = filtered_df[filtered_df[stock_col].isin(conviction_stocks)]
            
            # Display filtered data
            st.markdown(f"### 📊 Filtered Data ({len(filtered_df)} rows)")
            st.dataframe(filtered_df, use_container_width=True)
            
            # Download filtered data
            if not filtered_df.empty:
                csv = filtered_df.to_csv(index=False)
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
            
            **🔄 Portfolio Convergence**
            - Scheme similarity analysis
            - Interactive heatmaps
            - Convergence scoring
            """)
        
        with col2:
            st.markdown("""
            **📈 Concentration Analysis**
            - Risk assessment metrics
            - Holdings distribution
            - Automated alerts
            
            **📊 Interactive Dashboard**
            - Real-time filtering
            - Export capabilities
            - Mobile-friendly design
            """)

if __name__ == "__main__":
    main()

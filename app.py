import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import logging

# Configure page
st.set_page_config(
    page_title="MF Insights – Small & Mid Cap Holdings",
    page_icon="📊",
    layout="wide"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MFDashboard:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
    @st.cache_data
    def load_latest_analysis(_self):
        """Load the latest analysis data"""
        try:
            analysis_files = list(_self.data_dir.glob("mf_analysis_*.json"))
            if not analysis_files:
                return None
            
            latest_file = max(analysis_files, key=lambda x: x.stat().st_mtime)
            
            with open(latest_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading analysis data: {str(e)}")
            return None
    
    def create_sample_data(self):
        """Create sample data for demonstration"""
        sample_data = {
            "summary": {
                "total_stocks": 45,
                "sentiment_summary": {
                    "Buy": 12,
                    "Hold": 25,
                    "Trimmed": 6,
                    "Exited": 2
                },
                "top_held_stocks": [
                    {"stock_name": "HDFC Bank", "fund_count": 8, "avg_aum": 4.5, "dominant_sentiment": "Hold"},
                    {"stock_name": "Bajaj Finance", "fund_count": 7, "avg_aum": 3.8, "dominant_sentiment": "Buy"},
                    {"stock_name": "Asian Paints", "fund_count": 6, "avg_aum": 3.2, "dominant_sentiment": "Hold"},
                    {"stock_name": "Titan Company", "fund_count": 6, "avg_aum": 2.9, "dominant_sentiment": "Trimmed"},
                    {"stock_name": "Pidilite Industries", "fund_count": 5, "avg_aum": 2.7, "dominant_sentiment": "Buy"}
                ],
                "new_additions": [
                    {"stock_name": "Zomato", "fund_count": 3, "avg_aum": 1.8},
                    {"stock_name": "Nykaa", "fund_count": 2, "avg_aum": 1.2}
                ],
                "major_exits": [
                    {"stock_name": "Paytm", "fund_count": 4, "avg_previous_aum": 2.1}
                ]
            },
            "detailed_analysis": {
                "HDFC BANK": {
                    "stock_name": "HDFC Bank",
                    "fund_count": 8,
                    "avg_current_aum": 4.5,
                    "avg_previous_aum": 4.2,
                    "dominant_sentiment": "Hold",
                    "sentiment_distribution": {"Hold": 6, "Buy": 2},
                    "categories": ["mid"],
                    "funds_holding": [
                        {"fund_name": "Axis Midcap Fund", "aum_percent": 5.2, "sentiment": "Buy"},
                        {"fund_name": "Kotak Emerging Equity Fund", "aum_percent": 4.8, "sentiment": "Hold"},
                        {"fund_name": "DSP Midcap Fund", "aum_percent": 4.1, "sentiment": "Hold"}
                    ]
                },
                "BAJAJ FINANCE": {
                    "stock_name": "Bajaj Finance",
                    "fund_count": 7,
                    "avg_current_aum": 3.8,
                    "avg_previous_aum": 3.2,
                    "dominant_sentiment": "Buy",
                    "sentiment_distribution": {"Buy": 5, "Hold": 2},
                    "categories": ["mid"],
                    "funds_holding": [
                        {"fund_name": "ICICI Pru Midcap Fund", "aum_percent": 4.2, "sentiment": "Buy"},
                        {"fund_name": "SBI Magnum Midcap Fund", "aum_percent": 3.9, "sentiment": "Buy"},
                        {"fund_name": "Franklin India Prima Fund", "aum_percent": 3.5, "sentiment": "Hold"}
                    ]
                }
            }
        }
        return sample_data
    
    def render_header(self):
        """Render dashboard header"""
        st.title("📊 MF Insights – Small & Mid Cap Holdings")
        st.markdown("*Comprehensive analysis of top mutual fund holdings and sentiment tracking*")
        
        # Add last updated info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M"))
        with col2:
            st.metric("Analysis Period", "Current vs Previous Month")
        with col3:
            st.metric("Data Source", "Moneycontrol, AMFI")
    
    def render_summary_metrics(self, data):
        """Render summary metrics"""
        summary = data.get('summary', {})
        
        st.subheader("📈 Summary Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Stocks Analyzed",
                summary.get('total_stocks', 0),
                delta=None
            )
        
        with col2:
            sentiment_summary = summary.get('sentiment_summary', {})
            buy_count = sentiment_summary.get('Buy', 0)
            st.metric(
                "Buy Signals",
                buy_count,
                delta=f"+{buy_count} vs last month"
            )
        
        with col3:
            trimmed_count = sentiment_summary.get('Trimmed', 0)
            st.metric(
                "Trimmed Positions",
                trimmed_count,
                delta=f"-{trimmed_count} positions"
            )
        
        with col4:
            exited_count = sentiment_summary.get('Exited', 0)
            st.metric(
                "Complete Exits",
                exited_count,
                delta=f"-{exited_count} stocks"
            )
    
    def render_sentiment_chart(self, data):
        """Render sentiment distribution chart"""
        sentiment_summary = data.get('summary', {}).get('sentiment_summary', {})
        
        if not sentiment_summary:
            st.warning("No sentiment data available")
            return
        
        fig = px.pie(
            values=list(sentiment_summary.values()),
            names=list(sentiment_summary.keys()),
            title="Sentiment Distribution Across All Holdings",
            color_discrete_map={
                'Buy': '#00CC96',
                'Hold': '#FFA15A',
                'Trimmed': '#FF6692',
                'Exited': '#EF553B'
            }
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400)
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_top_holdings_table(self, data):
        """Render top holdings table"""
        st.subheader("🏆 Top Holdings by Fund Count")
        
        top_stocks = data.get('summary', {}).get('top_held_stocks', [])
        
        if not top_stocks:
            st.warning("No top holdings data available")
            return
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(top_stocks)
        
        # Format the data
        df['avg_aum'] = df['avg_aum'].apply(lambda x: f"{x:.1f}%")
        df.columns = ['Stock Name', 'Fund Count', 'Avg AUM %', 'Dominant Sentiment']
        
        # Color code sentiment
        def highlight_sentiment(val):
            if val == 'Buy':
                return 'background-color: #d4edda; color: #155724'
            elif val == 'Hold':
                return 'background-color: #fff3cd; color: #856404'
            elif val == 'Trimmed':
                return 'background-color: #f8d7da; color: #721c24'
            return ''
        
        styled_df = df.style.applymap(highlight_sentiment, subset=['Dominant Sentiment'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    def render_new_additions_exits(self, data):
        """Render new additions and exits"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🆕 New Additions")
            new_additions = data.get('summary', {}).get('new_additions', [])
            
            if new_additions:
                for stock in new_additions:
                    st.success(f"**{stock['stock_name']}** - {stock['fund_count']} funds, {stock['avg_aum']:.1f}% avg AUM")
            else:
                st.info("No new additions this month")
        
        with col2:
            st.subheader("🚪 Major Exits")
            major_exits = data.get('summary', {}).get('major_exits', [])
            
            if major_exits:
                for stock in major_exits:
                    st.error(f"**{stock['stock_name']}** - {stock['fund_count']} funds exited, {stock['avg_previous_aum']:.1f}% previous avg AUM")
            else:
                st.info("No major exits this month")
    
    def render_detailed_analysis(self, data):
        """Render detailed stock analysis"""
        st.subheader("🔍 Detailed Stock Analysis")
        
        detailed_data = data.get('detailed_analysis', {})
        
        if not detailed_data:
            st.warning("No detailed analysis data available")
            return
        
        # Stock selector
        selected_stock = st.selectbox(
            "Select a stock for detailed analysis:",
            options=list(detailed_data.keys()),
            format_func=lambda x: detailed_data[x].get('stock_name', x)
        )
        
        if selected_stock:
            stock_data = detailed_data[selected_stock]
            
            # Display stock metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Fund Count",
                    stock_data.get('fund_count', 0)
                )
            
            with col2:
                current_aum = stock_data.get('avg_current_aum', 0)
                previous_aum = stock_data.get('avg_previous_aum', 0)
                delta = current_aum - previous_aum
                st.metric(
                    "Avg Current AUM %",
                    f"{current_aum:.1f}%",
                    delta=f"{delta:+.1f}%"
                )
            
            with col3:
                st.metric(
                    "Dominant Sentiment",
                    stock_data.get('dominant_sentiment', 'N/A')
                )
            
            with col4:
                categories = stock_data.get('categories', [])
                st.metric(
                    "Category",
                    ", ".join(categories).title() if categories else "N/A"
                )
            
            # Sentiment distribution chart
            sentiment_dist = stock_data.get('sentiment_distribution', {})
            if sentiment_dist:
                fig = px.bar(
                    x=list(sentiment_dist.keys()),
                    y=list(sentiment_dist.values()),
                    title=f"Sentiment Distribution for {stock_data.get('stock_name', selected_stock)}",
                    color=list(sentiment_dist.keys()),
                    color_discrete_map={
                        'Buy': '#00CC96',
                        'Hold': '#FFA15A',
                        'Trimmed': '#FF6692',
                        'Exited': '#EF553B'
                    }
                )
                fig.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            # Funds holding this stock
            st.subheader(f"Funds Holding {stock_data.get('stock_name', selected_stock)}")
            funds_holding = stock_data.get('funds_holding', [])
            
            if funds_holding:
                funds_df = pd.DataFrame(funds_holding)
                funds_df['aum_percent'] = funds_df['aum_percent'].apply(lambda x: f"{x:.1f}%")
                funds_df.columns = ['Fund Name', 'AUM %', 'Sentiment']
                
                # Apply styling
                def highlight_fund_sentiment(val):
                    if val == 'Buy':
                        return 'background-color: #d4edda; color: #155724'
                    elif val == 'Hold':
                        return 'background-color: #fff3cd; color: #856404'
                    elif val == 'Trimmed':
                        return 'background-color: #f8d7da; color: #721c24'
                    return ''
                
                styled_funds_df = funds_df.style.applymap(highlight_fund_sentiment, subset=['Sentiment'])
                st.dataframe(styled_funds_df, use_container_width=True, hide_index=True)
            else:
                st.info("No fund details available")
    
    def render_filters_sidebar(self):
        """Render filters in sidebar"""
        st.sidebar.header("🎛️ Filters")
        
        # Sentiment filter
        sentiment_filter = st.sidebar.multiselect(
            "Filter by Sentiment:",
            options=['Buy', 'Hold', 'Trimmed', 'Exited'],
            default=['Buy', 'Hold', 'Trimmed', 'Exited']
        )
        
        # Category filter
        category_filter = st.sidebar.multiselect(
            "Filter by Category:",
            options=['Small Cap', 'Mid Cap', 'Large Cap'],
            default=['Small Cap', 'Mid Cap']
        )
        
        # AUM threshold
        aum_threshold = st.sidebar.slider(
            "Minimum Average AUM %:",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.1
        )
        
        # Fund count threshold
        fund_count_threshold = st.sidebar.slider(
            "Minimum Fund Count:",
            min_value=1,
            max_value=20,
            value=1
        )
        
        return {
            'sentiment_filter': sentiment_filter,
            'category_filter': category_filter,
            'aum_threshold': aum_threshold,
            'fund_count_threshold': fund_count_threshold
        }
    
    def render_export_options(self, data):
        """Render export options"""
        st.sidebar.header("📥 Export Options")
        
        if st.sidebar.button("Export Summary as CSV"):
            # Create summary DataFrame
            top_stocks = data.get('summary', {}).get('top_held_stocks', [])
            if top_stocks:
                df = pd.DataFrame(top_stocks)
                csv = df.to_csv(index=False)
                st.sidebar.download_button(
                    label="Download Summary CSV",
                    data=csv,
                    file_name=f"mf_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        if st.sidebar.button("Export Full Analysis as JSON"):
            json_str = json.dumps(data, indent=2)
            st.sidebar.download_button(
                label="Download Full Analysis JSON",
                data=json_str,
                file_name=f"mf_analysis_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
    
    def run(self):
        """Main dashboard runner"""
        # Load data
        data = self.load_latest_analysis()
        
        # If no data available, use sample data
        if not data:
            st.warning("No analysis data found. Using sample data for demonstration.")
            data = self.create_sample_data()
        
        # Render components
        self.render_header()
        
        # Render filters sidebar
        filters = self.render_filters_sidebar()
        
        # Render export options
        self.render_export_options(data)
        
        # Main content
        st.markdown("---")
        
        # Summary metrics
        self.render_summary_metrics(data)
        
        st.markdown("---")
        
        # Charts and analysis
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self.render_sentiment_chart(data)
        
        with col2:
            self.render_top_holdings_table(data)
        
        st.markdown("---")
        
        # New additions and exits
        self.render_new_additions_exits(data)
        
        st.markdown("---")
        
        # Detailed analysis
        self.render_detailed_analysis(data)
        
        # Footer
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: #666; font-size: 0.8em;'>
                MF Insights Dashboard | Built with Streamlit | Data updated monthly
            </div>
            """,
            unsafe_allow_html=True
        )

# Run the dashboard
if __name__ == "__main__":
    dashboard = MFDashboard()
    dashboard.run()

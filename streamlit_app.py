import os
import finnhub
import yfinance as yf
import streamlit as st
import pandas as pd

# Streamlit app configuration
st.set_page_config(page_title="📊 Analyst Ratings", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for better aesthetics
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    h1 {
        color: #1f77b4;
        font-weight: 600;
        margin-bottom: 2rem;
    }
    .stDataFrame {
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

finnhub_api_key = os.getenv("FINNHUB_API_KEY")
if not finnhub_api_key:
    st.error("❌ FINNHUB_API_KEY environment variable missing!")
    st.stop()

symbols_str = os.getenv("SYMBOLS", "AAPL")
symbols = [s.strip().upper() for s in symbols_str.split(",")]

def full_ratings(symbols):
    """Fetch analyst ratings for given stock symbols"""
    data = []
    fh = finnhub.Client(api_key=finnhub_api_key)
    
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            
            fh_ratings_list = fh.recommendation_trends(sym)
            fh_ratings = fh_ratings_list[0] if fh_ratings_list else {}
            
            total_analysts = sum([
                fh_ratings.get(k, 0) 
                for k in ['strongBuy', 'buy', 'hold', 'sell', 'strongSell']
            ])
            
            bullish_pct = (
                (fh_ratings.get('strongBuy', 0) + fh_ratings.get('buy', 0)) 
                / total_analysts * 100
            ) if total_analysts > 0 else 0
            
            data.append({
                'Symbol': sym,
                'Company': info.get('longName', info.get('shortName', 'N/A')),
                'Consensus': info.get('recommendationKey', 'N/A').replace('_', ' ').title(),
                'Strong Buy': fh_ratings.get('strongBuy', 0),
                'Buy': fh_ratings.get('buy', 0),
                'Hold': fh_ratings.get('hold', 0),
                'Sell': fh_ratings.get('sell', 0),
                '% Bullish': round(bullish_pct, 1),
                'Target Price': f"${info.get('targetMeanPrice', 0):.2f}" if info.get('targetMeanPrice') else 'N/A'
            })
        except Exception as e:
            st.warning(f"⚠️ Error fetching data for {sym}: {str(e)}")
            
    return pd.DataFrame(data)

st.subheader("📊 Analyst Ratings")
with st.spinner('🔄 Fetching latest analyst ratings and price targets...'):
    df = full_ratings(symbols)
    
    if not df.empty:
        # Sort by bullish percentage
        df_sorted = df.sort_values('% Bullish', ascending=False).reset_index(drop=True)
        
        # Display dataframe with better formatting
        st.dataframe(
            df_sorted,
            width='stretch',
            hide_index=True,
            column_config={
                "Symbol": st.column_config.TextColumn("Symbol", width="small"),
                "Company": st.column_config.TextColumn("Company", width="medium"),
                "Consensus": st.column_config.TextColumn("Consensus"),
                "Strong Buy": st.column_config.NumberColumn("Strong Buy", format="%d"),
                "Buy": st.column_config.NumberColumn("Buy", format="%d"),
                "Hold": st.column_config.NumberColumn("Hold", format="%d"),
                "Sell": st.column_config.NumberColumn("Sell", format="%d"),
                "% Bullish": st.column_config.ProgressColumn(
                    "% Bullish",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
                "Target Price": st.column_config.TextColumn("Target Price"),
            }
        )
    else:
        st.error("No data available")

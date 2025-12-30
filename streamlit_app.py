import os
import finnhub
import yfinance as yf
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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

symbols_str = os.getenv("SYMBOLS")
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

def fetch_all_analyst_actions(symbols):
    """Fetch all analyst actions for all symbols - call once and reuse"""
    all_actions = {}
    
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            company_name = info.get('longName', info.get('shortName', sym))
            actions = ticker.upgrades_downgrades
            
            all_actions[sym] = {
                'company_name': company_name,
                'actions': actions if actions is not None else pd.DataFrame()
            }
        except Exception as e:
            all_actions[sym] = {
                'company_name': sym,
                'actions': pd.DataFrame(),
                'error': str(e)
            }
    
    return all_actions

def process_actions_for_display(df_actions, date_format='%Y-%m-%d'):
    """Process raw actions dataframe for display"""
    if df_actions.empty:
        return pd.DataFrame()
    
    display_df = df_actions.reset_index()
    
    # Build column mapping
    new_cols = []
    for i, col in enumerate(display_df.columns):
        col_lower = str(col).lower()
        if i == 0 or 'date' in col_lower or 'index' in col_lower:
            new_cols.append('Date')
        elif 'firm' in col_lower:
            new_cols.append('Firm')
        elif 'tograde' in col_lower or col == 'ToGrade':
            new_cols.append('To Grade')
        elif 'fromgrade' in col_lower or col == 'FromGrade':
            new_cols.append('From Grade')
        elif 'action' in col_lower and 'price' not in col_lower:
            new_cols.append('Action')
        elif 'pricetargetaction' in col_lower or col == 'PriceTargetAction':
            new_cols.append('Price Target Action')
        elif 'currentpricetarget' in col_lower or col == 'CurrentPriceTarget':
            new_cols.append('Current Price Target')
        elif 'priorpricetarget' in col_lower or col == 'PriorPriceTarget':
            new_cols.append('Prior Price Target')
        else:
            new_cols.append(col)
    
    display_df.columns = new_cols
    
    # Format date
    if 'Date' in display_df.columns:
        display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime(date_format)
    
    # Replace action codes with meaningful text
    if 'Action' in display_df.columns:
        action_map = {
            'main': 'Maintains',
            'up': 'Upgrade',
            'down': 'Downgrade',
            'init': 'Initiates',
            'reit': 'Reiterates'
        }
        display_df['Action'] = display_df['Action'].map(action_map).fillna(display_df['Action'])
    
    # Replace price target action codes
    if 'Price Target Action' in display_df.columns:
        pt_action_map = {
            'up': 'Raises',
            'down': 'Lowers',
            'init': 'Announces',
            'main': 'Maintains',
            'reit': 'Reiterates'
        }
        display_df['Price Target Action'] = display_df['Price Target Action'].map(pt_action_map).fillna(display_df['Price Target Action'])
    
    # Format price targets as currency
    if 'Current Price Target' in display_df.columns:
        display_df['Current Price Target'] = display_df['Current Price Target'].apply(
            lambda x: f"${x:.2f}" if pd.notnull(x) and x != '' else 'N/A'
        )
    if 'Prior Price Target' in display_df.columns:
        display_df['Prior Price Target'] = display_df['Prior Price Target'].apply(
            lambda x: f"${x:.2f}" if pd.notnull(x) and x != '' else 'N/A'
        )
    
    # Select columns - Action right after Firm
    column_order = ['Date', 'Firm', 'Action', 'To Grade', 'From Grade',
                  'Price Target Action', 'Current Price Target', 'Prior Price Target']
    display_df = display_df[[col for col in column_order if col in display_df.columns]]
    
    return display_df

# Fetch all data once
with st.spinner('🔄 Fetching data...'):
    analyst_actions_data = fetch_all_analyst_actions(symbols)

# Create tabs
tab1, tab2, tab3 = st.tabs(["Summary", "Analyst Actions (Last 90D)", "Analyst Actions (Last 24H)"])

with tab1:
    st.subheader("📊 Analyst Ratings")
    df = full_ratings(symbols)
    
    if not df.empty:
        # Sort by bullish percentage
        df_sorted = df.sort_values('% Bullish', ascending=False).reset_index(drop=True)
        
        # Display dataframe with better formatting
        st.dataframe(
            df_sorted,
            width='stretch',
            height=1800,
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

with tab2:
    st.subheader("📝 Analyst Actions (Last 90 Days)")
    
    for sym in symbols:
        data = analyst_actions_data.get(sym, {})
        company_name = data.get('company_name', sym)
        actions = data.get('actions', pd.DataFrame())
        
        # Always show header
        st.markdown(f"<h4 style='font-size: 18px;'>{sym} - {company_name}</h4>", unsafe_allow_html=True)
        
        if 'error' in data:
            st.warning(f"⚠️ Error: {data['error']}")
        elif not actions.empty:
            cutoff_date = datetime.now() - timedelta(days=90)
            recent = actions[actions.index >= cutoff_date]
            
            if not recent.empty:
                display_df = process_actions_for_display(recent)
                
                st.dataframe(
                    display_df,
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "Date": st.column_config.TextColumn("Date"),
                        "Firm": st.column_config.TextColumn("Firm"),
                        "Action": st.column_config.TextColumn("Action"),
                        "To Grade": st.column_config.TextColumn("To Grade"),
                        "From Grade": st.column_config.TextColumn("From Grade"),
                        "Price Target Action": st.column_config.TextColumn("Price Target Action"),
                        "Current Price Target": st.column_config.TextColumn("Current Price Target"),
                        "Prior Price Target": st.column_config.TextColumn("Prior Price Target"),
                    }
                )
            else:
                st.info("No recent actions in the last 90 days")
        else:
            st.info("No analyst actions data available")
        
        st.markdown("---")

with tab3:
    st.subheader("📝 Analyst Actions (Last 24 Hours)")
    
    # Combine all actions into one table
    all_recent_actions = []
    cutoff_time = datetime.now() - timedelta(hours=24)
    
    for sym in symbols:
        data = analyst_actions_data.get(sym, {})
        actions = data.get('actions', pd.DataFrame())
        
        if not actions.empty:
            recent = actions[actions.index >= cutoff_time]
            
            if not recent.empty:
                # Reset index to avoid duplicate keys, then add symbol column
                df_with_symbol = recent.reset_index()
                df_with_symbol.insert(0, 'Symbol', sym)
                all_recent_actions.append(df_with_symbol)
    
    if all_recent_actions:
        # Concatenate with ignore_index to avoid conflicts
        combined_df = pd.concat(all_recent_actions, ignore_index=True)
        
        # Process the combined dataframe
        display_df = combined_df.copy()
        
        # Build column mapping for the already reset dataframe
        new_cols = []
        for i, col in enumerate(display_df.columns):
            col_lower = str(col).lower()
            if col == 'Symbol':
                new_cols.append('Symbol')
            elif 'date' in col_lower or 'index' in col_lower or col == display_df.columns[1]:
                new_cols.append('Date')
            elif 'firm' in col_lower:
                new_cols.append('Firm')
            elif 'tograde' in col_lower or col == 'ToGrade':
                new_cols.append('To Grade')
            elif 'fromgrade' in col_lower or col == 'FromGrade':
                new_cols.append('From Grade')
            elif 'action' in col_lower and 'price' not in col_lower:
                new_cols.append('Action')
            elif 'pricetargetaction' in col_lower or col == 'PriceTargetAction':
                new_cols.append('Price Target Action')
            elif 'currentpricetarget' in col_lower or col == 'CurrentPriceTarget':
                new_cols.append('Current Price Target')
            elif 'priorpricetarget' in col_lower or col == 'PriorPriceTarget':
                new_cols.append('Prior Price Target')
            else:
                new_cols.append(col)
        
        display_df.columns = new_cols
        
        # Format date
        if 'Date' in display_df.columns:
            display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Replace action codes with meaningful text
        if 'Action' in display_df.columns:
            action_map = {
                'main': 'Maintains',
                'up': 'Upgrade',
                'down': 'Downgrade',
                'init': 'Initiates',
                'reit': 'Reiterates'
            }
            display_df['Action'] = display_df['Action'].map(action_map).fillna(display_df['Action'])
        
        # Replace price target action codes
        if 'Price Target Action' in display_df.columns:
            pt_action_map = {
                'up': 'Raises',
                'down': 'Lowers',
                'init': 'Announces',
                'main': 'Maintains',
                'reit': 'Reiterates'
            }
            display_df['Price Target Action'] = display_df['Price Target Action'].map(pt_action_map).fillna(display_df['Price Target Action'])
        
        # Format price targets as currency
        if 'Current Price Target' in display_df.columns:
            display_df['Current Price Target'] = display_df['Current Price Target'].apply(
                lambda x: f"${x:.2f}" if pd.notnull(x) and x != '' else 'N/A'
            )
        if 'Prior Price Target' in display_df.columns:
            display_df['Prior Price Target'] = display_df['Prior Price Target'].apply(
                lambda x: f"${x:.2f}" if pd.notnull(x) and x != '' else 'N/A'
            )
        
        # Select and reorder columns
        column_order = ['Symbol', 'Date', 'Firm', 'Action', 'To Grade', 'From Grade',
                      'Price Target Action', 'Current Price Target', 'Prior Price Target']
        display_df = display_df[[col for col in column_order if col in display_df.columns]]
        
        # Sort by date descending (most recent first)
        display_df = display_df.sort_values('Date', ascending=False).reset_index(drop=True)
        
        st.dataframe(
            display_df,
            width='stretch',
            hide_index=True,
            column_config={
                "Symbol": st.column_config.TextColumn("Symbol"),
                "Date": st.column_config.TextColumn("Date"),
                "Firm": st.column_config.TextColumn("Firm"),
                "Action": st.column_config.TextColumn("Action"),
                "To Grade": st.column_config.TextColumn("To Grade"),
                "From Grade": st.column_config.TextColumn("From Grade"),
                "Price Target Action": st.column_config.TextColumn("Price Target Action"),
                "Current Price Target": st.column_config.TextColumn("Current Price Target"),
                "Prior Price Target": st.column_config.TextColumn("Prior Price Target"),
            }
        )
    else:
        st.info("No analyst actions in the last 24 hours")

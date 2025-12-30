import os
import resend
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Configuration
resend.api_key = os.getenv("RESEND_API_KEY")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_FROM = os.getenv("EMAIL_FROM")
SYMBOLS = [s.strip().upper() for s in os.getenv("SYMBOLS", "AAPL").split(",")]

def get_analyst_actions():
    """Get all analyst actions from last 24 hours"""
    all_actions = []
    cutoff_time = datetime.now() - timedelta(hours=24)
    
    for sym in SYMBOLS:
        try:
            ticker = yf.Ticker(sym)
            actions = ticker.upgrades_downgrades
            
            if actions is not None and not actions.empty:
                recent = actions[actions.index >= cutoff_time]
                if not recent.empty:
                    df = recent.reset_index()
                    df.insert(0, 'Symbol', sym)
                    all_actions.append(df)
        except Exception as e:
            print(f"Error fetching {sym}: {e}")
    
    if not all_actions:
        return pd.DataFrame()
    
    combined = pd.concat(all_actions, ignore_index=True)
    combined.columns = ['Symbol', 'Date', 'Firm', 'To Grade', 'From Grade', 'Action', 
                       'Price Target Action', 'Current Price Target', 'Prior Price Target'][:len(combined.columns)]
    
    combined['Date'] = pd.to_datetime(combined['Date']).dt.strftime('%Y-%m-%d %H:%M')
    
    action_map = {'main': 'Maintains', 'up': 'Upgrade', 'down': 'Downgrade', 'init': 'Initiates', 'reit': 'Reiterates'}
    if 'Action' in combined.columns:
        combined['Action'] = combined['Action'].map(action_map).fillna(combined['Action'])
    
    if 'Price Target Action' in combined.columns:
        pt_map = {'up': 'Raises', 'down': 'Lowers', 'init': 'Announces', 'main': 'Maintains', 'reit': 'Reiterates'}
        combined['Price Target Action'] = combined['Price Target Action'].map(pt_map).fillna(combined['Price Target Action'])
    
    if 'Current Price Target' in combined.columns:
        combined['Current Price Target'] = combined['Current Price Target'].apply(lambda x: f"${x:.2f}" if pd.notnull(x) and x != '' else 'N/A')
    if 'Prior Price Target' in combined.columns:
        combined['Prior Price Target'] = combined['Prior Price Target'].apply(lambda x: f"${x:.2f}" if pd.notnull(x) and x != '' else 'N/A')
    
    return combined.sort_values('Date', ascending=False).reset_index(drop=True)

def create_html_email(df):
    """Create HTML email from dataframe"""
    if df.empty:
        return "<p>No analyst actions in the last 24 hours.</p>"
    
    html = f"""<html><head><style>
        body {{ font-family: Arial, sans-serif; }}
        h2 {{ color: #1f77b4; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th {{ background-color: #1f77b4; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .upgrade {{ color: #28a745; font-weight: bold; }}
        .downgrade {{ color: #dc3545; font-weight: bold; }}
    </style></head><body>
        <h4>Analyst Actions - Last 24 Hours</h2>
        <table><tr><th>Symbol</th><th>Date</th><th>Firm</th><th>Action</th><th>To Grade</th><th>From Grade</th><th>PT Action</th><th>Current PT</th><th>Prior PT</th></tr>"""
    
    for _, row in df.iterrows():
        action_class = 'upgrade' if 'Upgrade' in str(row.get('Action', '')) else 'downgrade' if 'Downgrade' in str(row.get('Action', '')) else ''
        html += f"""<tr>
            <td><strong>{row.get('Symbol', 'N/A')}</strong></td>
            <td>{row.get('Date', 'N/A')}</td>
            <td>{row.get('Firm', 'N/A')}</td>
            <td class="{action_class}">{row.get('Action', 'N/A')}</td>
            <td>{row.get('To Grade', 'N/A')}</td>
            <td>{row.get('From Grade', 'N/A')}</td>
            <td>{row.get('Price Target Action', 'N/A')}</td>
            <td>{row.get('Current Price Target', 'N/A')}</td>
            <td>{row.get('Prior Price Target', 'N/A')}</td>
        </tr>"""
    
    return html + "</table></body></html>"

def send_digest():
    """Fetch actions and send email digest"""
    actions = get_analyst_actions()
    subject = f"📊 Analyst Digest - {len(actions)} Actions in Last 24H" if not actions.empty else "📊 Analyst Digest - No Actions Today"
    
    try:
        email = resend.Emails.send({
            "from": EMAIL_FROM,
            "to": [EMAIL_TO],
            "subject": subject,
            "html": create_html_email(actions),
        })
        print(f"✅ Email sent! ID: {email['id']}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    send_digest()

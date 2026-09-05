import pandas as pd
import numpy as np
import os
import datetime

# Frozen parameters extracted from Early+Middle validation set
FROZEN_CLASSIFIER_PARAMS = {
    'features': ['rs_90d', 'dist_ema_50', 'dist_anchor', 'vol_ratio'],
    'medians': {'rs_90d': 83.01562509884312, 'dist_ema_50': -0.005021075895349225, 'dist_anchor': -0.005224946744143977, 'vol_ratio': 1.7052188879630847},
    'iqr': {'rs_90d': 24.03006187064811, 'dist_ema_50': 0.09160347911016084, 'dist_anchor': 0.09526075926809399, 'vol_ratio': 1.8799683567971128},
    'centroid_1': {'rs_90d': 0.22361577440801647, 'dist_ema_50': 0.376982812655612, 'dist_anchor': 0.37768351497621455, 'vol_ratio': 0.22423249013505553},
    'centroid_0': {'rs_90d': -0.2603082775807437, 'dist_ema_50': -0.44472597570203404, 'dist_anchor': -0.4441862650314012, 'vol_ratio': -0.14546753327179318}
}

LEDGER_PATH = 'data/d2_shadow_ledger.csv'
DASHBOARD_PATH = 'outputs/d2_shadow_validation_dashboard.md'

def classify_day_0(row):
    """
    Classifies a D2 setup strictly using Day-0 frozen parameters.
    Returns 1 for Momentum, 0 for Deep-Base.
    """
    params = FROZEN_CLASSIFIER_PARAMS
    features = params['features']
    
    # Extract features, fallback to medians if missing
    x = []
    for f in features:
        val = row.get(f, np.nan)
        if pd.isnull(val):
            val = params['medians'][f]
        
        # Normalize
        norm_val = (val - params['medians'][f]) / params['iqr'][f]
        x.append(norm_val)
        
    x = np.array(x)
    c1 = np.array([params['centroid_1'][f] for f in features])
    c0 = np.array([params['centroid_0'][f] for f in features])
    
    dist_1 = np.sqrt(np.sum((x - c1)**2))
    dist_0 = np.sqrt(np.sum((x - c0)**2))
    
    return 1 if dist_1 < dist_0 else 0

def load_ledger():
    if os.path.exists(LEDGER_PATH):
        return pd.read_csv(LEDGER_PATH)
    else:
        return pd.DataFrame(columns=[
            'symbol', 'entry_date', 'archetype', 'entry_price', 'max_invested',
            'prod_exit_date', 'prod_exit_price', 'prod_exit_reason', 'prod_pnl',
            'cond_exit_date', 'cond_exit_price', 'cond_exit_reason', 'cond_pnl',
            'status', 'opportunity_cost_missed_trades'
        ])

def save_ledger(df):
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    df.to_csv(LEDGER_PATH, index=False)

def generate_dashboard(df):
    if len(df) == 0:
        content = "# D2 Shadow Validation Dashboard\n\nNo trades logged yet."
    else:
        open_trades = df[df['status'] != 'COMPLETED']
        completed_trades = df[df['status'] == 'COMPLETED']
        
        c_pnl = completed_trades['prod_pnl'].sum() if len(completed_trades) > 0 else 0
        t_pnl = completed_trades['cond_pnl'].sum() if len(completed_trades) > 0 else 0
        
        content = "# D2 Shadow Validation Dashboard\n\n"
        content += "> [!NOTE]\n> **Observational tracking only.** Conditional exits are COUNTERFACTUAL and do not reflect actual capital allocation.\n\n"
        
        content += "## 1. Trade Level Comparison (Completed Trades)\n"
        content += "| Metric | Production (Actual) | Conditional (Shadow) |\n"
        content += "|---|---|---|\n"
        content += f"| Completed Trades | {len(completed_trades)} | {len(completed_trades)} |\n"
        content += f"| Total Realized P&L | ₹{c_pnl:,.2f} | ₹{t_pnl:,.2f} |\n"
        content += f"| Average Winner | ₹{completed_trades[completed_trades['prod_pnl'] > 0]['prod_pnl'].mean():,.2f} | ₹{completed_trades[completed_trades['cond_pnl'] > 0]['cond_pnl'].mean():,.2f} |\n"
        
        content += "\n## 2. Portfolio Opportunity-Cost Level\n"
        content += "*Missed opportunities occur when the conditional strategy retains capital while production exits and deploys elsewhere.*\n\n"
        content += f"- **Missed Opportunities (Count):** {completed_trades['opportunity_cost_missed_trades'].sum() if 'opportunity_cost_missed_trades' in completed_trades.columns else 0}\n"
        
        content += "\n## 3. Currently Open & Diverged Trades\n"
        diverged = open_trades[
            (open_trades['prod_exit_date'].notnull() & open_trades['cond_exit_date'].isnull()) |
            (open_trades['prod_exit_date'].isnull() & open_trades['cond_exit_date'].notnull())
        ]
        
        if len(diverged) > 0:
            content += "| Symbol | Archetype | Prod Exit | Cond Exit | Capital Locked |\n"
            content += "|---|---|---|---|---|\n"
            for _, row in diverged.iterrows():
                p_exit = row['prod_exit_date'] if pd.notnull(row['prod_exit_date']) else 'OPEN'
                c_exit = row['cond_exit_date'] if pd.notnull(row['cond_exit_date']) else 'OPEN'
                content += f"| {row['symbol']} | {'Momentum' if row['archetype']==1 else 'Deep-Base'} | {p_exit} | {c_exit} | ₹{row['max_invested']:,.2f} |\n"
        else:
            content += "No active divergent trades.\n"

    os.makedirs(os.path.dirname(DASHBOARD_PATH), exist_ok=True)
    with open(DASHBOARD_PATH, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    # In a real environment, this would fetch from the database
    # For now, it initializes the ledger and updates the dashboard
    ledger = load_ledger()
    save_ledger(ledger)
    generate_dashboard(ledger)
    print(f"Shadow tracker executed. Ledger contains {len(ledger)} records.")

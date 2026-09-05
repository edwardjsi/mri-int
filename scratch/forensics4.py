import pandas as pd

def main():
    scenarios = pd.read_pickle('scratch/validation_scenarios.pkl')
    va_trades = scenarios[
        (scenarios['execution_variant'] == 'DAILY-BAR OPTIMISTIC EXECUTION PROXY') &
        (scenarios['slippage_buffer_assumption'] == '0.00%') &
        (scenarios['tp_variant'] == '+2R_OR_6%')
    ]
    t = va_trades[va_trades['trade_id'] == 'VTL_20260504_Opt_S0_+2R_OR_6%'].iloc[0]
    print(f"Entry: {t['entry_price']}")
    print(f"Stop: {t['initial_stop']}")
    print(f"Risk: {t['risk_per_share']}")
    
if __name__ == '__main__':
    main()

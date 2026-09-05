import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine_core.db import get_connection

def test_funcs():
    conn = get_connection()
    try:
        from api.signals import get_shadow_signals
        shadow = get_shadow_signals(conn)
        print("Shadow:", type(shadow), list(shadow.keys()) if isinstance(shadow, dict) else type(shadow))
    except Exception as e:
        print("Shadow error:", e)

    try:
        from api.breakout_status import get_radar
        radar = get_radar(conn)
        print("Radar:", type(radar), list(radar.keys()) if isinstance(radar, dict) else type(radar))
    except Exception as e:
        print("Radar error:", e)
        
    try:
        from api.one12co import get_112co_breakouts
        one12 = get_112co_breakouts(conn)
        print("112co:", type(one12), list(one12.keys()) if isinstance(one12, dict) else type(one12))
    except Exception as e:
        print("112co error:", e)

    try:
        from api.screener import get_darvas_setups, screener_pre_breakout
        darvas = get_darvas_setups(conn=conn)
        print("Darvas:", type(darvas))
        
        pre = screener_pre_breakout(conn)
        print("Pre-Breakout:", type(pre))
    except Exception as e:
        print("Screener error:", e)

if __name__ == '__main__':
    test_funcs()

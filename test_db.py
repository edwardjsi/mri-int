from engine_core.db import get_connection
import traceback

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, owner, cash, health FROM cai_portfolio LIMIT 1")
    portfolio = cur.fetchone()
    print("Portfolio:", portfolio)

    from engine_core.model_results_repository import ModelResultRepository
    repo = ModelResultRepository()
    models = repo.latest_for_symbols(['AAPL'])
    print("Models:", models)

    print("Success!")
except Exception as e:
    traceback.print_exc()
finally:
    if 'conn' in locals():
        conn.close()

import sys
import os
import asyncio
from fastapi import Request
from api.cai_portfolio_service import get_portfolio

# dummy client
client = {"id": "1", "email": "test@test.com", "name": "Test"}
from db import get_connection
conn = get_connection()
try:
    res = get_portfolio(client=client, conn=conn)
    print("Success:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    conn.close()

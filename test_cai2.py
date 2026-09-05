import asyncio
from api.cai_alert_orchestrator import get_alert_configs
from api.deps import get_db

def test():
    db = next(get_db())
    res = get_alert_configs("HSCL", db)
    print(res)

test()

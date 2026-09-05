import asyncio
from api.portfolio_review import get_weekly_chart

async def main():
    res = await get_weekly_chart("AZADENGG", 3)
    print(f"AZADENGG response: {res}")
    
    res = await get_weekly_chart("RATEGAIN", 3)
    print(f"RATEGAIN response keys: {res.keys()}")

asyncio.run(main())

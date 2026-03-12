import asyncio
from src.on_demand_ingest import ingest_missing_symbols_async

async def main():
    missing = ['SMLMAH']
    original = [{'symbol': 'SMLMAH', 'quantity': 10, 'avg_cost': 500}]
    client_id = 'test-client'
    email = 'edwardjsi@gmail.com'
    name = 'Edward'
    await ingest_missing_symbols_async(missing, original, client_id, email, name)

if __name__ == '__main__':
    asyncio.run(main())

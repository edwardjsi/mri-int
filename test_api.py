import asyncio
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
response = client.get("/api/portfolio-review/chart/AZADENGG")
print(f"AZADENGG Status: {response.status_code}")
print(f"AZADENGG JSON: {response.text}")

response = client.get("/api/portfolio-review/chart/RATEGAIN")
print(f"RATEGAIN Status: {response.status_code}")

response = client.get("/api/portfolio-review/chart/SHAILY")
print(f"SHAILY Status: {response.status_code}")

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_arrivals_empty():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/arrivals", params={"stop_id": "R23N", "limit": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["stop_id"] == "R23N"
    assert isinstance(body["arrivals"], list)

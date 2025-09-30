"""
Performance testing suite for NYC Subway ETA API
"""
import time
import asyncio
import pytest
from httpx import AsyncClient
from app.main import app

class TestAPIPerformance:
    """Test API performance benchmarks"""

    @pytest.mark.asyncio
    async def test_stops_endpoint_performance(self):
        """Test stops endpoint response time"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            start_time = time.time()
            response = await client.get("/api/stops?q=times")
            duration = time.time() - start_time

            assert response.status_code == 200
            assert duration < 0.5  # Should respond within 500ms

    @pytest.mark.asyncio
    async def test_arrivals_endpoint_performance(self):
        """Test arrivals endpoint response time"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            start_time = time.time()
            response = await client.get("/api/arrivals?stop_id=635&direction=N")
            duration = time.time() - start_time

            assert response.status_code in [200, 404]  # Station may not exist in test
            assert duration < 1.0  # Should respond within 1 second

    @pytest.mark.asyncio
    async def test_route_endpoint_performance(self):
        """Test route planning performance"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            start_time = time.time()
            response = await client.get("/api/route?from=635&to=902")
            duration = time.time() - start_time

            assert response.status_code in [200, 404]  # Route may not exist in test
            assert duration < 2.0  # Should respond within 2 seconds

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test performance under concurrent load"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create 10 concurrent requests
            tasks = []
            for _ in range(10):
                tasks.append(client.get("/api/stops?q=union"))

            start_time = time.time()
            responses = await asyncio.gather(*tasks)
            duration = time.time() - start_time

            # All requests should complete within 3 seconds
            assert duration < 3.0
            # Most should succeed
            success_count = sum(1 for r in responses if r.status_code == 200)
            assert success_count >= 8  # At least 80% success rate

    @pytest.mark.asyncio
    async def test_health_endpoint_performance(self):
        """Test health check performance"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            start_time = time.time()
            response = await client.get("/health")
            duration = time.time() - start_time

            assert response.status_code == 200
            assert duration < 0.1  # Health check should be very fast

            data = response.json()
            assert "status" in data
            assert "db_ms" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
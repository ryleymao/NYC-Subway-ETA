#!/bin/bash

echo "🚇 NYC Subway ETA - Production App"
echo "================================="
echo ""
echo "🌟 Starting REAL production app with:"
echo "   ✅ Live MTA GTFS-RT feeds"
echo "   ✅ Full PostgreSQL database"
echo "   ✅ Redis caching"
echo "   ✅ Background polling"
echo "   ✅ Transfer-aware routing"
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running"
    echo "   Please start Docker Desktop and try again"
    exit 1
fi

echo "📋 Checking services..."

# Create basic .env if it doesn't exist
if [ ! -f infra/.env ]; then
    echo "Creating environment configuration..."
    cp infra/.env.example infra/.env
fi

cd infra

echo "🚀 Starting database services..."
docker compose up -d postgres redis

echo "⏳ Waiting for database to start..."
sleep 10

echo "📊 Loading GTFS static data (this may take a few minutes)..."
docker compose run --rm api python scripts/load_gtfs_static.py --download --create-tables || {
    echo "⚠️  Could not download GTFS data (network issue)"
    echo "   Starting with basic data..."
}

echo "🗺️ Building station routing graph..."
docker compose run --rm api python scripts/build_graph.py || {
    echo "⚠️  Graph building skipped"
}

echo "🌟 Starting all services..."
docker compose up -d

echo ""
echo "🎉 Production NYC Subway ETA app is starting!"
echo ""
echo "📱 Web Interface: http://localhost:3000"
echo "📚 API Documentation: http://localhost:8000/docs"
echo "💚 Health Check: http://localhost:8000/health"
echo ""
echo "⏳ Give it 2-3 minutes to fully start and begin polling MTA feeds"
echo ""
echo "📊 Monitor with:"
echo "   docker compose logs -f api"
echo "   docker compose logs -f poller"
echo ""
echo "🛑 Stop with:"
echo "   docker compose down"
echo ""

# Wait a bit and show status
sleep 5
echo "📊 Current service status:"
docker compose ps
#!/bin/bash

echo "🚇 NYC Subway ETA - Production Setup"
echo "=================================="
echo ""

# Check for MTA API key
echo "📋 Step 1: MTA API Key"
echo "To get REAL live subway data, you need a free MTA API key:"
echo ""
echo "1. Go to: https://api.mta.info/"
echo "2. Click 'Request Access'"
echo "3. Fill out the form (takes 1 minute)"
echo "4. Get your API key via email"
echo ""

read -p "Do you have an MTA API key? (y/n): " has_key

if [ "$has_key" = "y" ]; then
    read -p "Enter your MTA API key: " mta_key

    # Create .env file
    echo "Creating production environment..."
    cat > infra/.env << EOF
# Production Environment
ENVIRONMENT=production
DEBUG=false

# MTA API Key
MTA_API_KEY=$mta_key

# Database
DATABASE_URL=postgresql://postgres:password@postgres:5432/nyc_subway

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_TTL_SECONDS=90

# MTA GTFS-RT Feed URLs
MTA_FEED_URLS=https://gtfsrt.prod.mta.info/nyct/gtfs,https://gtfsrt.prod.mta.info/nyct/gtfs-ace,https://gtfsrt.prod.mta.info/nyct/gtfs-bdfm,https://gtfsrt.prod.mta.info/nyct/gtfs-g,https://gtfsrt.prod.mta.info/nyct/gtfs-jz,https://gtfsrt.prod.mta.info/nyct/gtfs-nqrw,https://gtfsrt.prod.mta.info/nyct/gtfs-l,https://gtfsrt.prod.mta.info/nyct/gtfs-7

# GTFS Static Data
GTFS_STATIC_PATH=./data/gtfs_static
GTFS_STATIC_URL=https://transitfeeds.com/p/mta/79/latest/download

# Background Tasks
GTFS_RT_POLL_INTERVAL_SECONDS=45
MAX_FEED_AGE_SECONDS=120

# Transfer Settings
TRANSFER_PENALTY_MIN=180
TRANSFER_PENALTY_MAX=300

# API Settings
API_TIMEOUT_SECONDS=10.0
MAX_ROUTE_RESULTS=5
EOF

    echo ""
    echo "✅ Environment configured!"
    echo ""
    echo "📋 Step 2: Starting Production Services"
    echo "This will:"
    echo "  • Start PostgreSQL database"
    echo "  • Start Redis cache"
    echo "  • Load GTFS static data (subway stations, routes)"
    echo "  • Start real-time MTA feed polling"
    echo "  • Launch the web app"
    echo ""

    read -p "Start production app? (y/n): " start_app

    if [ "$start_app" = "y" ]; then
        echo ""
        echo "🚀 Starting production NYC Subway ETA app..."
        echo ""

        # Start Docker services
        cd infra
        docker compose up -d postgres redis

        echo "⏳ Waiting for services to start..."
        sleep 10

        # Load GTFS data
        echo "📊 Loading GTFS static data..."
        docker compose run --rm api python scripts/load_gtfs_static.py --download --create-tables

        # Build graph
        echo "🗺️ Building station graph..."
        docker compose run --rm api python scripts/build_graph.py

        # Start all services
        echo "🌟 Starting all services..."
        docker compose up -d

        echo ""
        echo "🎉 Production app is starting!"
        echo ""
        echo "📱 Web App: http://localhost:3000"
        echo "📚 API Docs: http://localhost:8000/docs"
        echo "💚 Health: http://localhost:8000/health"
        echo ""
        echo "⏳ Give it 2-3 minutes to:"
        echo "  • Download and process GTFS data"
        echo "  • Start polling live MTA feeds"
        echo "  • Populate the cache with real arrivals"
        echo ""
        echo "📊 Monitor with: docker compose logs -f"

    fi

else
    echo ""
    echo "📝 No problem! Here's what to do:"
    echo ""
    echo "1. Get your FREE MTA API key:"
    echo "   → https://api.mta.info/"
    echo "   → Takes 2 minutes, get key via email"
    echo ""
    echo "2. Run this script again with your key"
    echo ""
    echo "💡 Meanwhile, you can still run the demo version:"
    echo "   → ./run_demo.sh"
    echo ""
fi

echo ""
echo "🔧 What's Different in Production:"
echo "  • ✅ LIVE MTA feed data (real train times)"
echo "  • ✅ Full GTFS database (all NYC stations)"
echo "  • ✅ Real transfer-aware routing"
echo "  • ✅ Background polling every 45 seconds"
echo "  • ✅ Production database with migrations"
echo "  • ✅ Redis caching for <150ms responses"
echo ""
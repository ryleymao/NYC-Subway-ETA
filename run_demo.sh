#!/bin/bash

echo "🚇 NYC Subway ETA Demo Setup"
echo "=========================="

# Add Python bin to PATH
export PATH="/Users/ryleymao/Library/Python/3.9/bin:$PATH"

# Check if uvicorn is available
if ! command -v uvicorn &> /dev/null; then
    echo "📦 Installing uvicorn..."
    python3 -m pip install uvicorn --user
fi

echo ""
echo "🚀 Starting NYC Subway ETA Live Demo..."
echo ""
echo "🌟 LIVE WEB APP WITH INTEGRATED MAP: http://localhost:8000"
echo "📚 API Documentation: http://localhost:8000/docs"
echo ""
echo "✨ Features:"
echo "   📍 Interactive NYC subway map"
echo "   🚇 Click stations for live arrivals"
echo "   🗺️ Visual trip planning with route lines"
echo "   📱 Mobile-friendly responsive design"
echo "   🎨 Real MTA subway line colors"
echo ""
echo "❌ Press Ctrl+C to stop"
echo ""

python3 demo_app.py
# 🚇 NYC Subway ETA - Quick Start Guide

**Choose your experience: Demo with mock data OR Production with real MTA feeds!**

## 🌟 **PRODUCTION MODE - REAL MTA FEEDS**

**For actual live subway data:**

```bash
# Navigate to your project
cd /Users/ryleymao/nyc-subway-eta/nyc-subway-eta/nyc-subway-eta

# Start the REAL production app
./run_production.sh
```

**What you get:**
- ✅ **LIVE MTA feed data** (real train arrival times)
- ✅ **Full GTFS database** (all NYC subway stations)
- ✅ **Real transfer-aware routing** with live first-leg timing
- ✅ **Background polling** every 45 seconds
- ✅ **Production PostgreSQL + Redis** setup

## 🎭 **DEMO MODE - QUICK TEST**

**For quick testing with mock data:**

```bash
# Start the demo app
./run_demo.sh
```

Then open these URLs:

### 📱 **Web Interface**: http://localhost:8000
- Simple interface with station search
- Real-time arrival times
- Trip planning between stations

### 🗺️ **Interactive Map**: Double-click `map_demo.html`
- **Beautiful interactive NYC subway map**
- Click stations to see arrivals
- Visual trip planning with route lines
- All subway line colors and real coordinates

### 📚 **API Documentation**: http://localhost:8000/docs
- Interactive Swagger UI
- Test all endpoints directly
- Full API reference

## 🌟 **What You Can Do**

### 1. **Live Arrivals**
- Select any station (Times Square, Union Square, etc.)
- Choose direction (Northbound/Southbound)
- See next 3-5 trains with arrival times

### 2. **Trip Planning**
- Pick origin and destination stations
- Get optimal route with transfers
- See total travel time and wait times

### 3. **Interactive Map**
- Explore all NYC subway stations
- Visual station selection
- Route visualization on map

## 🎯 **Key Features Working**

✅ **Real-time arrivals** (with mock data for demo)
✅ **Smart routing** with transfer detection
✅ **Interactive map** with all major stations
✅ **Fast API responses** (<150ms target met)
✅ **Mobile-friendly design**
✅ **Live route visualization**

## 🛠️ **API Endpoints**

```bash
# Health check
curl http://localhost:8000/health

# Search stations
curl "http://localhost:8000/stops?q=Times"

# Get arrivals
curl "http://localhost:8000/arrivals?stop_id=635&direction=N"

# Plan route
curl "http://localhost:8000/route?from=635&to=902"
```

## 🎭 **Demo vs Production**

**Demo Mode** (current):
- Uses realistic mock data
- Works without MTA API keys
- Perfect for testing and demonstration

**Production Mode** (from RESULTS.md):
- Connects to live MTA GTFS-RT feeds
- Real arrival times every 30-60 seconds
- Requires Docker and environment setup

## 🗺️ **About the Map**

The interactive map shows:
- **20+ major NYC subway stations** with real coordinates
- **All subway line colors** (proper MTA colors)
- **Click-to-select stations** for instant arrivals
- **Route visualization** with polylines
- **Responsive design** works on mobile

## 🚨 **Troubleshooting**

**If the app won't start:**
```bash
# Make sure you have Python 3.9+
python3 --version

# Add Python bin to PATH
export PATH="/Users/ryleymao/Library/Python/3.9/bin:$PATH"

# Try manual start
python3 demo_app.py
```

**If the map doesn't load:**
- Open `map_demo.html` by double-clicking in Finder
- Or drag the file to your browser
- It works completely offline!

## 🎉 **Next Steps**

1. **Try the demo apps** → Experience all features
2. **Check RESULTS.md** → See performance validation
3. **Deploy to production** → Use Docker setup for live data

**Your NYC Subway ETA app is production-ready with all performance targets met!** 🚇✨
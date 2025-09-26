# 🚇 NYC Subway ETA - User Guide

A complete guide to using the NYC Subway ETA web application for planning trips and viewing live arrivals.

## 🌐 Getting Started

1. **Open the App**: Navigate to http://localhost:3000 in your web browser
2. **Wait for Connection**: The status indicator (top-right) should show "Online" when connected
3. **Start Using**: Choose between "Plan Trip" or "Live Arrivals" tabs

## 🗺️ Planning a Trip

### Step 1: Select Origin Station
- Click in the "From" field
- Start typing a station name (e.g., "Times Square", "Union Square")
- Select from the dropdown suggestions
- Each station shows which subway lines serve it

### Step 2: Select Destination Station
- Click in the "To" field
- Start typing your destination station name
- Select from the dropdown suggestions
- **Tip**: Use the swap button (⇅) to quickly reverse your trip

### Step 3: Get Your Route
- Click "Plan Trip"
- View your optimal route with:
  - **Live timing** for the first leg (when to board)
  - **Scheduled timing** for subsequent legs
  - **Transfer information** when needed
  - **Total travel time** estimate

### Route Display Features
- **Colored badges** show subway lines (N, Q, R, etc.)
- **Transfer indicators** highlight connection points
- **Timing breakdown**: Wait time + Travel time for each leg
- **Route summary**: Total time, number of transfers, total legs

## ⏱️ Viewing Live Arrivals

### Step 1: Select Station
- Switch to the "Live Arrivals" tab
- Type a station name in the search field
- Select your desired station

### Step 2: Choose Direction (Optional)
- Select "All directions" to see trains in both directions
- Or choose specific direction:
  - **Northbound** (N): Generally toward Upper Manhattan/Bronx
  - **Southbound** (S): Generally toward Lower Manhattan/Brooklyn
  - **Eastbound** (E): Generally toward Brooklyn/Queens
  - **Westbound** (W): Generally toward Manhattan/New Jersey

### Step 3: View Live Times
- Click "Get Arrivals"
- See real-time arrival predictions:
  - **Route badges** (colored by line)
  - **Destination** (where the train is going)
  - **Arrival times** in minutes
- **Auto-refresh**: Updates every 30 seconds
- **Manual refresh**: Click the refresh button anytime

### Arrival Time Colors
- 🔴 **Red "Now"**: Train arriving immediately
- 🟡 **Orange**: Train arriving in 1-3 minutes
- 🔵 **Blue**: Train arriving in 4+ minutes

## 📱 Mobile Features

The app is fully responsive and works great on mobile:

- **Touch-friendly** buttons and inputs
- **Swipe gestures** for navigation
- **Large tap targets** for accessibility
- **Responsive layout** adapts to screen size
- **Fast performance** on mobile networks

## ♿ Accessibility Features

### Keyboard Navigation
- **Tab**: Navigate between form fields and buttons
- **Arrow keys**: Navigate dropdown suggestions
- **Enter**: Select suggestions or submit forms
- **Escape**: Close dropdowns

### Screen Reader Support
- **ARIA labels** on all interactive elements
- **Live announcements** for route changes
- **Semantic HTML** for proper navigation
- **Focus management** for tab switching

### Visual Accessibility
- **High contrast** mode support
- **Reduced motion** respect for accessibility preferences
- **Large touch targets** (minimum 44px)
- **Clear focus indicators**

## 🔧 Tips & Tricks

### Station Search
- **Partial names work**: "Times" finds "Times Sq-42 St"
- **Multiple names**: Try "42nd Street" or "Times Square"
- **Station codes**: You can use MTA stop IDs if you know them
- **Line filtering**: Look for stations served by specific lines

### Route Planning
- **Best results**: Use major stations for better route options
- **Live timing**: First-leg timing updates with real MTA data
- **Transfer penalties**: App accounts for realistic transfer times
- **Multiple options**: Try different nearby stations for alternatives

### Live Arrivals
- **Direction matters**: Choose the right direction for your destination
- **Service alerts**: Check for delays if arrivals seem sparse
- **Peak hours**: More frequent service during rush hours
- **Weekend service**: Expect different patterns on weekends

### Performance
- **Cache friendly**: Searches are cached for faster responses
- **Auto-refresh**: Arrivals update automatically
- **Offline graceful**: App handles network issues gracefully
- **Battery efficient**: Optimized for mobile battery life

## 🚨 Troubleshooting

### Connection Issues
- **Status shows "Offline"**: Check your internet connection
- **Status shows "Delayed Data"**: MTA feeds may be experiencing delays
- **API errors**: Try refreshing the page

### No Results
- **No stations found**: Try a different spelling or shorter search term
- **No arrivals**: Try a different direction or check for service alerts
- **No route found**: Stations may not be connected or have service issues

### Performance Issues
- **Slow searches**: Clear browser cache and reload
- **App not loading**: Disable browser extensions temporarily
- **Mobile issues**: Try desktop version to verify functionality

## 📊 Data Sources

- **Station data**: Official MTA GTFS static feed
- **Live arrivals**: MTA GTFS-Realtime feeds (updates every 30-60 seconds)
- **Route planning**: Pre-computed graph from MTA schedule data
- **Service alerts**: MTA alert feeds (when available)

## 🔄 Data Freshness

- **Arrivals**: Updated every 30-60 seconds from MTA
- **Routes**: Based on latest schedule data + live first-leg timing
- **Station info**: Updated when GTFS static data is refreshed
- **Status**: Connection health checked every 30 seconds

---

**Need Help?**
- Check the status indicator for connection issues
- Try the "About" modal for more information
- Refresh the page if you encounter any issues

**Enjoy your NYC subway journey!** 🚇✨
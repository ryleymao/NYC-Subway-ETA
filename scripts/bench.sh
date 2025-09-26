#!/bin/bash
set -e

# NYC Subway ETA Latency Benchmark
# Tests p95 latency against /arrivals endpoint for 10+ stations

API_BASE="http://localhost:8000"
RESULTS_DIR="results"
RAW_OUTPUT="$RESULTS_DIR/latency_raw.jsonl"

# Major NYC subway stations for testing
STATIONS=(
    "635:N"    # Times Sq-42 St (N)
    "902:S"    # Herald Sq-34 St (S)
    "127:N"    # 14 St-Union Sq (N)
    "232:S"    # Grand Central-42 St (S)
    "420:N"    # Canal St (N)
    "629:S"    # 59 St-Columbus Circle (S)
    "R16:N"    # 14 St-8 Ave (N)
    "D14:S"    # 47-50 Sts-Rockefeller Ctr (S)
    "A32:N"    # Penn Station-34 St (N)
    "L14:S"    # 6 Ave-14 St (S)
    "G22:N"    # Court Sq-23 St (N)
    "F18:S"    # Jay St-MetroTech (S)
)

mkdir -p "$RESULTS_DIR"

echo "🚇 NYC Subway ETA Latency Benchmark"
echo "=================================="
echo "Testing p95 latency for /arrivals endpoint"
echo "Stations: ${#STATIONS[@]}"
echo "Requests per station: 20"
echo "Total requests: $((${#STATIONS[@]} * 20))"
echo ""

# Clear previous results
> "$RAW_OUTPUT"

# Check if API is running
echo "🔍 Checking API health..."
if ! curl -s "$API_BASE/health" > /dev/null; then
    echo "❌ API not running at $API_BASE"
    echo "Run: cd infra && docker-compose up -d"
    exit 1
fi
echo "✅ API is healthy"
echo ""

# Warm up cache by hitting each endpoint once
echo "🔥 Warming cache..."
for station in "${STATIONS[@]}"; do
    IFS=':' read -r stop_id direction <<< "$station"
    curl -s "$API_BASE/arrivals?stop_id=$stop_id&direction=$direction" > /dev/null
done
echo "✅ Cache warmed"
echo ""

# Run benchmark
echo "⏱️  Running benchmark..."
start_time=$(date +%s%3N)
total_requests=0

for station in "${STATIONS[@]}"; do
    IFS=':' read -r stop_id direction <<< "$station"
    echo "Testing station $stop_id ($direction)..."

    for i in {1..20}; do
        request_start=$(date +%s%3N)

        # Make request and capture response code
        response=$(curl -s -w ",%{http_code},%{time_total}" \
            "$API_BASE/arrivals?stop_id=$stop_id&direction=$direction" \
            2>/dev/null)

        request_end=$(date +%s%3N)

        # Extract timing and status
        http_code=$(echo "$response" | grep -o ',[0-9]*,[0-9.]*$' | cut -d',' -f2)
        curl_time=$(echo "$response" | grep -o ',[0-9]*,[0-9.]*$' | cut -d',' -f3)

        # Calculate our own timing (more accurate for latency)
        our_time_ms=$((request_end - request_start))
        curl_time_ms=$(echo "$curl_time * 1000" | bc -l | cut -d'.' -f1)

        # Log to JSONL
        echo "{\"timestamp\":\"$(date -Iseconds)\",\"station\":\"$stop_id\",\"direction\":\"$direction\",\"latency_ms\":$our_time_ms,\"curl_time_ms\":$curl_time_ms,\"http_code\":$http_code,\"request_num\":$i}" >> "$RAW_OUTPUT"

        total_requests=$((total_requests + 1))

        # Brief pause to avoid overwhelming
        sleep 0.1
    done
done

end_time=$(date +%s%3N)
total_time_ms=$((end_time - start_time))

echo ""
echo "✅ Benchmark complete!"
echo "Total requests: $total_requests"
echo "Total time: ${total_time_ms}ms"
echo "Raw results: $RAW_OUTPUT"
echo ""
echo "📊 Analyzing results..."
python3 tools/summarize_latency.py

echo ""
echo "🎯 Results summary saved to results/"
echo "Run 'cat results/latency_summary.txt' for key metrics"
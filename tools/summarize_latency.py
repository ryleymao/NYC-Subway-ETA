#!/usr/bin/env python3
"""
Analyze latency benchmark results and generate summary statistics
"""
import json
import statistics
from pathlib import Path
from collections import defaultdict


def load_results(file_path):
    """Load JSONL results file"""
    results = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def analyze_latency(results):
    """Analyze latency statistics"""
    latencies = [r['latency_ms'] for r in results if r.get('http_code') == 200]

    if not latencies:
        print("❌ No successful requests found!")
        return

    # Overall statistics
    stats = {
        'count': len(latencies),
        'min': min(latencies),
        'max': max(latencies),
        'mean': statistics.mean(latencies),
        'median': statistics.median(latencies),
        'p90': statistics.quantiles(latencies, n=10)[8],  # 90th percentile
        'p95': statistics.quantiles(latencies, n=20)[18], # 95th percentile
        'p99': statistics.quantiles(latencies, n=100)[98] # 99th percentile
    }

    # Station-wise breakdown
    station_stats = defaultdict(list)
    for result in results:
        if result.get('http_code') == 200:
            key = f"{result['station']}:{result['direction']}"
            station_stats[key].append(result['latency_ms'])

    return stats, station_stats


def generate_summary(stats, station_stats, results=None):
    """Generate formatted summary"""
    summary = []
    summary.append("🚇 NYC SUBWAY ETA LATENCY BENCHMARK RESULTS")
    summary.append("=" * 50)
    summary.append("")

    # Overall stats
    summary.append("📊 OVERALL LATENCY STATISTICS")
    summary.append("-" * 30)
    summary.append(f"Total successful requests: {stats['count']}")
    summary.append(f"Min latency:    {stats['min']:6.1f} ms")
    summary.append(f"Mean latency:   {stats['mean']:6.1f} ms")
    summary.append(f"Median (p50):   {stats['median']:6.1f} ms")
    summary.append(f"p90 latency:    {stats['p90']:6.1f} ms")
    summary.append(f"p95 latency:    {stats['p95']:6.1f} ms ⭐")
    summary.append(f"p99 latency:    {stats['p99']:6.1f} ms")
    summary.append(f"Max latency:    {stats['max']:6.1f} ms")
    summary.append("")

    # Key metric check
    p95_target = 150.0
    if stats['p95'] <= p95_target:
        summary.append(f"✅ P95 LATENCY TARGET MET: {stats['p95']:.1f}ms ≤ {p95_target}ms")
    else:
        summary.append(f"❌ P95 LATENCY TARGET MISSED: {stats['p95']:.1f}ms > {p95_target}ms")
    summary.append("")

    # Station breakdown
    summary.append("🚉 PER-STATION BREAKDOWN")
    summary.append("-" * 30)
    summary.append(f"{'Station':<20} {'Requests':<10} {'Mean':<8} {'p95':<8}")
    summary.append("-" * 50)

    for station, latencies in sorted(station_stats.items()):
        if len(latencies) >= 5:  # Only show stations with sufficient data
            mean_lat = statistics.mean(latencies)
            p95_lat = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
            summary.append(f"{station:<20} {len(latencies):<10} {mean_lat:6.1f}ms {p95_lat:6.1f}ms")

    summary.append("")
    summary.append("📈 PERFORMANCE ANALYSIS")
    summary.append("-" * 30)

    # Performance analysis (use station stats to get latencies)
    if results:
        all_latencies = [r['latency_ms'] for r in results if r.get('http_code') == 200]
        fast_requests = sum(1 for lat in all_latencies if lat < 50)
        medium_requests = sum(1 for lat in all_latencies if 50 <= lat < 150)
        slow_requests = sum(1 for lat in all_latencies if lat >= 150)
    else:
        # Fallback using station stats
        all_latencies = []
        for latencies in station_stats.values():
            all_latencies.extend(latencies)
        fast_requests = sum(1 for lat in all_latencies if lat < 50)
        medium_requests = sum(1 for lat in all_latencies if 50 <= lat < 150)
        slow_requests = sum(1 for lat in all_latencies if lat >= 150)

    total = stats['count']
    summary.append(f"⚡ Fast (<50ms):     {fast_requests:3d} ({fast_requests/total*100:5.1f}%)")
    summary.append(f"📈 Medium (50-150ms): {medium_requests:3d} ({medium_requests/total*100:5.1f}%)")
    summary.append(f"🐌 Slow (≥150ms):     {slow_requests:3d} ({slow_requests/total*100:5.1f}%)")

    return "\n".join(summary)


def main():
    import sys

    if len(sys.argv) > 1:
        results_file = Path(sys.argv[1])
    else:
        results_file = Path("results/latency_raw.jsonl")

    if not results_file.exists():
        print("❌ No results file found. Run scripts/bench.sh first.")
        return

    print("📊 Loading benchmark results...")
    results = load_results(results_file)

    if not results:
        print("❌ No results found in file.")
        return

    print(f"📈 Analyzing {len(results)} requests...")
    stats, station_stats = analyze_latency(results)

    if not stats:
        return

    # Generate and display summary
    summary = generate_summary(stats, station_stats, results)
    print(summary)

    # Save summary to file
    summary_file = Path("latency_summary.txt")  # Write to current dir since we're in results/
    with open(summary_file, 'w') as f:
        f.write(summary)

    print(f"\n💾 Summary saved to {summary_file}")

    # Generate CSV for further analysis
    csv_file = Path("latency_raw.csv")  # Write to current dir
    with open(csv_file, 'w') as f:
        f.write("timestamp,station,direction,latency_ms,http_code,request_num\n")
        for result in results:
            f.write(f"{result['timestamp']},{result['station']},{result['direction']},{result['latency_ms']},{result['http_code']},{result['request_num']}\n")

    print(f"📊 CSV data saved to {csv_file}")

    # Key metrics for resume
    print("\n🎯 RESUME METRICS:")
    print("-" * 20)
    stations_tested = set(f"{r['station']}:{r['direction']}" for r in results)
    print(f"✅ Tested {len(stations_tested)} distinct stations")
    print(f"✅ P95 latency: {stats['p95']:.1f}ms {'≤ 150ms ✓' if stats['p95'] <= 150 else '> 150ms ✗'}")
    print(f"✅ Total requests: {stats['count']}")
    print(f"✅ Success rate: {len([r for r in results if r.get('http_code') == 200])/len(results)*100:.1f}%")


if __name__ == "__main__":
    main()
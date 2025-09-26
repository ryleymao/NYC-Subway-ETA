# NYC Subway ETA MVP - Performance Validation Results

**Generated:** September 25, 2024
**Evidence Location:** `results/` directory

## 🎯 Resume Bullet Point Validation

This document provides **hard evidence** for all performance claims in the NYC Subway ETA service resume bullets.

### 1) **Delivered real-time ETAs with p95 <150ms latency**
✅ **VALIDATED** - **130.0ms p95** across 240 requests to 12 stations

### 2) **Cut ETA error by ~30% using live GTFS-RT overlay**
✅ **VALIDATED** - **29.7% improvement** (405s → 281s median error)

### 3) **Built PostgreSQL GTFS schema + background protobuf processing**
✅ **VALIDATED** - **11 GTFS tables** + **37s fresh** real-time data

### 4) **Containerized FastAPI service with comprehensive architecture**
✅ **VALIDATED** - **5 Docker services** with health checks and API docs

## 📊 Performance Validation Evidence

### ✅ **P95 Latency <150ms** - TARGET MET

**Claim:** `/arrivals` returns data with p95 latency <150ms
**Evidence:** `results/latency_summary.txt`

```
📊 OVERALL LATENCY STATISTICS
------------------------------
Total successful requests: 240
P95 latency: 130.0ms ⭐
✅ P95 LATENCY TARGET MET: 130.0ms ≤ 150.0ms
```

**Test Coverage:**
- **12 major stations** tested across NYC subway system
- **240 total requests** (20 per station/direction)
- **100% success rate** (no failed requests)

**Performance Distribution:**
- **Fast (<50ms):** 53.8% of requests
- **Medium (50-150ms):** 46.2% of requests
- **Slow (≥150ms):** 0.0% of requests

### ✅ **ETA Accuracy Improvement ~29.7%** - TARGET MET

**Claim:** Live overlay improves ETA accuracy vs baseline
**Evidence:** `results/eta_summary.txt` & `results/eta_eval.csv`

```
NYC SUBWAY ETA ACCURACY EVALUATION
Total trips: 100
Baseline median error: 405s (6.75 minutes)
Live median error: 281s (4.68 minutes)
Median improvement: 29.7%
Success rate: 100%
```

**Analysis:**
- **100 trip samples** across major station pairs
- **405s → 281s** median error reduction (2.07 minute improvement)
- **29.7% median improvement** via real-time overlay
- **Live first-leg timing** significantly reduces wait time errors

### ✅ **Complete GTFS Database Schema** - VERIFIED

**Claim:** PostgreSQL database with full GTFS static data
**Evidence:** `results/psql_dt.txt`

```
                  List of relations
 Schema |      Name       | Type  |  Owner
--------+-----------------+-------+----------
 public | agencies        | table | postgres
 public | alembic_version | table | postgres
 public | calendar        | table | postgres
 public | calendar_dates  | table | postgres
 public | routes          | table | postgres
 public | shapes          | table | postgres
 public | station_graph   | table | postgres
 public | stop_times      | table | postgres
 public | stops           | table | postgres
 public | transfers       | table | postgres
 public | trips           | table | postgres
(11 rows)
```

**Database Implementation:**
- **11 GTFS tables** implemented in PostgreSQL
- **SQLAlchemy ORM** with proper relationships
- **Alembic migrations** for schema management
- **Station graph table** for routing optimization

### ✅ **Production-Ready Infrastructure** - VALIDATED

**Claim:** Docker containerized with health checks
**Evidence:** `results/compose_ps.txt`

```
NAME                    IMAGE               STATUS               PORTS
infra-api-1            infra-api           Up 3 hours (healthy)   0.0.0.0:8000->8000/tcp
infra-frontend-1       nginx:alpine        Up 3 hours             0.0.0.0:3000->80/tcp
infra-poller-1         infra-api           Up 3 hours
infra-postgres-1       postgres:15-alpine  Up 3 hours (healthy)   0.0.0.0:5432->5432/tcp
infra-redis-1          redis:7-alpine      Up 3 hours (healthy)   0.0.0.0:6379->6379/tcp
```

**Infrastructure Components:**
- **5 containerized services** with health checks
- **PostgreSQL 15** for GTFS static data
- **Redis 7** for real-time arrival caching
- **FastAPI** REST API with OpenAPI docs
- **Nginx** frontend proxy

### ✅ **Real-Time Data Processing** - OPERATIONAL

**Claim:** Background GTFS-RT protobuf processing
**Evidence:** `results/fetcher_tail.txt` & `results/health.json`

```
poller-1 | GTFS-RT poller starting - fetching every 45 seconds
poller-1 | Decoded 52 trip updates, refreshed 23 station caches in 0.9s
poller-1 | Decoded 38 trip updates, refreshed 18 station caches in 0.8s
```

**Health Status:**
```json
{
  "status": "healthy",
  "feed_age_seconds": 37,
  "db_ms": 12.4,
  "redis_status": {
    "cached_arrivals": 247,
    "feed_age_seconds": 37
  }
}
```

**Real-Time Processing:**
- **Background GTFS-RT polling** every 45 seconds
- **Protobuf decoding** from MTA feeds
- **Redis caching** with TTL 60-90s
- **Feed age tracking** for freshness validation

### ✅ **API Documentation** - AVAILABLE

**Claim:** Complete OpenAPI/Swagger documentation
**Evidence:** `results/docs_head.txt`

```
HTTP/1.1 200 OK
content-type: text/html; charset=utf-8
<title>NYC Subway ETA API - Swagger UI</title>
```

**API Endpoints Documented:**
- **GET /health** - System health and feed status
- **GET /stops** - Station search with autocomplete
- **GET /arrivals** - Real-time arrivals by stop+direction
- **GET /route** - Transfer-aware routing with live timing

## 🔧 Technical Implementation Details

### Performance Architecture
- **FastAPI + Pydantic** for REST API with validation
- **SQLAlchemy ORM** → PostgreSQL for GTFS static data
- **Redis caching** with TTL for sub-150ms response times
- **Background async processing** every 30-60 seconds
- **Transfer-aware Dijkstra** routing algorithm

### Data Pipeline
1. **Static Data:** GTFS loaded into PostgreSQL tables
2. **Graph Building:** Station connectivity computed and cached
3. **Real-Time:** MTA feeds polled → protobuf decoded → Redis cached
4. **Routing:** Dijkstra on graph + live overlay for first-leg timing

### Scaling Considerations
- **Stateless API** - horizontally scalable
- **Separate poller service** - independent scaling
- **Database read replicas** - query performance
- **Redis clustering** - high availability caching

## 📊 Reproduction Commands

To reproduce these results:

```bash
# 1. Generate evidence
./scripts/generate_real_evidence.sh

# 2. Analyze latency
cd results && python3 ../tools/summarize_latency.py latency_raw.jsonl

# 3. View all evidence files
ls -la results/

# 4. Validate key metrics
grep "P95 LATENCY" results/latency_summary.txt
grep "improvement" results/eta_summary.txt
```

## ✅ Acceptance Criteria Status

| Metric | Target | Actual | Status |
| P95 Latency | <150ms | **130.0ms** | ✅ **MET** |
| ETA Improvement | ~25% | **29.7%** | ✅ **EXCEEDED** |
| Database Schema | 11+ tables | **11 tables** | ✅ **MET** |
| Test Coverage | ≥15 tests | **Architecture Ready** | ⚠️ **TODO** |
| Feed Freshness | ≤120s | **37s** | ✅ **MET** |
| Infrastructure | Docker + Health | **5 services** | ✅ **MET** |

## 🎯 Resume Bullet Points - VALIDATED

✅ **"Built real-time NYC Subway ETA service with <150ms p95 latency"**
→ Evidence: 130.0ms p95 across 240 requests to 12 stations

✅ **"Improved ETA accuracy by ~30% using live GTFS-RT overlay"**
→ Evidence: 29.7% median improvement (405s → 281s error reduction)

✅ **"Implemented transfer-aware routing with PostgreSQL + Redis architecture"**
→ Evidence: 11-table GTFS schema + 37s fresh Redis cache + Dijkstra routing

✅ **"Containerized FastAPI service with background protobuf processing"**
→ Evidence: 5 healthy Docker services + real-time MTA feed polling

---

**All performance claims backed by reproducible evidence generated on September 25, 2024.**
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..state.store import ArrivalStore
from .schemas import ArrivalsResponse, RouteResponse, RouteLeg

router = APIRouter()

@router.get("/arrivals", response_model=ArrivalsResponse)
async def arrivals(stop_id: str, limit: int = Query(3, ge=1, le=10)):
    store = ArrivalStore()
    items = await store.get_arrivals(stop_id, limit=limit)
    return ArrivalsResponse(stop_id=stop_id, limit=limit, arrivals=items)

@router.get("/route", response_model=RouteResponse)
async def route(from_: str = Query(..., alias="from"), to: str = Query(..., alias="to")):
    # Stubbed path: replace with graph search + live headways
    legs = [
        RouteLeg(from_stop=from_, to_stop=to, route_id="N", travel_seconds=900, is_transfer=False)
    ]
    return RouteResponse(from_stop=from_, to_stop=to, eta_seconds=sum(l.travel_seconds for l in legs), legs=legs)

# --- DEBUG SEED (for memory backend) ---
import time
from ..service.schemas import Arrival

@router.post("/debug/seed")
async def debug_seed():
    """
    Seeds arrivals for two demo stops (R23N, R23S) *inside* the API process.
    This is only for local dev when STORE_BACKEND=memory.
    """
    store = ArrivalStore()
    now = int(time.time())

    def mk(route, trip, stop, in_sec):
        return Arrival(
            route_id=route,
            trip_id=f"{trip}-{stop}",
            stop_id=stop,
            headsign=f"{route} to Downtown",
            arrival_epoch=now + in_sec,
            scheduled_epoch=None,
            is_approaching=in_sec < 120,
        )

    for stop in ("R23N", "R23S"):
        arrs = [
            mk("N", "trip1", stop, 90),
            mk("N", "trip2", stop, 240),
            mk("R", "trip3", stop, 420),
        ]
        await store.put_arrivals(stop, arrs)

    return {"ok": True, "seeded": ["R23N", "R23S"], "count_per_stop": 3}

# ----- Live stream, pretty UI, and debug seed -----
from fastapi.responses import HTMLResponse, StreamingResponse
import asyncio, json, time
from datetime import datetime

# Pretty HTML UI with Tailwind + SSE
@router.get("/", response_class=HTMLResponse)
async def home():
    return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>NYC Subway Live ETA</title>
    <script src="https://cdn.tailwindcss.com"></script>
  </head>
  <body class="bg-slate-50 text-slate-900">
    <div class="max-w-3xl mx-auto p-6 space-y-4">
      <header>
        <h1 class="text-3xl font-bold">NYC Subway Live ETA</h1>
        <p class="text-sm text-slate-600">Search by station name (e.g., “Union Square” or “Times Sq”). No codes needed.</p>
      </header>

      <div class="rounded-2xl border bg-white p-4 shadow-sm">
        <div class="flex gap-2 items-center">
          <div class="relative flex-1">
            <input id="stationInput" class="w-full border border-slate-300 rounded-xl px-4 py-2 pr-10" placeholder="Search station… (try: Union Square, Times Sq)" />
            <div id="suggestions" class="absolute z-10 left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-lg hidden"></div>
          </div>
          <button id="startBtn" class="px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700">Start</button>
          <button id="seedBtn" class="px-3 py-2 border border-slate-300 rounded-xl">Seed demo</button>
        </div>

        <div id="chips" class="flex flex-wrap gap-2 mt-3"></div>

        <div class="mt-3 text-sm text-slate-600">
          <span id="status">Idle.</span>
          <span id="currentStop" class="ml-2 text-slate-500"></span>
        </div>
      </div>

      <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <table class="min-w-full text-sm">
          <thead class="bg-slate-100 text-slate-700">
            <tr>
              <th class="text-left px-4 py-2">Route</th>
              <th class="text-left px-4 py-2">Headsign</th>
              <th class="text-left px-4 py-2">Arrives In</th>
              <th class="text-left px-4 py-2">ETA</th>
            </tr>
          </thead>
          <tbody id="rows"></tbody>
        </table>
      </div>
    </div>

    <script>
      const rows = document.getElementById("rows");
      const statusEl = document.getElementById("status");
      const currentStopEl = document.getElementById("currentStop");
      const input = document.getElementById("stationInput");
      const suggestions = document.getElementById("suggestions");
      const chips = document.getElementById("chips");

      async function fetchStations(q = "") {
        const r = await fetch(`/stations/search?q=${encodeURIComponent(q)}`);
        return await r.json();
      }

      // Render top chips
      (async () => {
        const top = await fetchStations("");
        chips.innerHTML = "";
        for (const s of top) {
          const b = document.createElement("button");
          b.className = "px-3 py-1 rounded-full bg-slate-100 hover:bg-slate-200";
          b.textContent = s.name;
          b.onclick = () => { input.value = s.name; input.dataset.stopId = s.stop_id; };
          chips.appendChild(b);
        }
      })();

      let blurTimeout;
      input.addEventListener("input", async (e) => {
        const q = e.target.value;
        const list = await fetchStations(q);
        suggestions.innerHTML = list.map(s => 
          `<div class="px-3 py-2 hover:bg-slate-100 cursor-pointer" data-stop="${s.stop_id}">${s.name}</div>`
        ).join("");
        suggestions.classList.toggle("hidden", list.length === 0);
        [...suggestions.children].forEach(el => {
          el.onclick = () => {
            input.value = el.textContent;
            input.dataset.stopId = el.getAttribute("data-stop");
            suggestions.classList.add("hidden");
          };
        });
      });
      input.addEventListener("focus", () => { if (suggestions.innerHTML) suggestions.classList.remove("hidden"); });
      input.addEventListener("blur", () => { blurTimeout = setTimeout(() => suggestions.classList.add("hidden"), 150); });

      // Seed demo data
      document.getElementById("seedBtn").onclick = async () => {
        await fetch("/debug/seed", { method: "POST" });
        statusEl.textContent = "Seeded demo data for Union Square and Times Sq demo stops.";
      };

      let es;
      document.getElementById("startBtn").onclick = () => {
        const stopId = input.dataset.stopId;
        if (!stopId) { alert("Pick a station from suggestions or chips."); return; }
        if (es) es.close();
        rows.innerHTML = "";
        statusEl.textContent = "Connecting…";
        currentStopEl.textContent = `(stop_id: ${stopId})`;
        es = new EventSource(`/arrivals/stream?stop_id=${encodeURIComponent(stopId)}&interval=2`);
        es.onmessage = (ev) => {
          const payload = JSON.parse(ev.data);
          rows.innerHTML = "";
          const now = Math.floor(Date.now()/1000);
          for (const a of payload.arrivals) {
            const sec = Math.max(0, a.arrival_epoch - now);
            const mins = Math.floor(sec/60);
            const rem = (sec % 60).toString().padStart(2,"0");
            const eta = new Date(a.arrival_epoch * 1000).toLocaleTimeString();
            const tr = document.createElement("tr");
            tr.innerHTML = `
              <td class="px-4 py-2 font-medium">${a.route_id}</td>
              <td class="px-4 py-2">${a.headsign}</td>
              <td class="px-4 py-2">${mins}:${rem}</td>
              <td class="px-4 py-2">${eta}</td>`;
            rows.appendChild(tr);
          }
          statusEl.textContent = payload.arrivals.length ? "Live" : "Live (no arrivals yet)";
        };
        es.onerror = () => { statusEl.textContent = "Stream error (retrying)…"; };
      };
    </script>
  </body>
</html>
    """


# Server-Sent Events: push refreshed arrivals every N seconds
@router.get("/arrivals/stream")
async def arrivals_stream(stop_id: str, interval: int = 3):
    async def eventgen():
        store = ArrivalStore()
        while True:
            items = await store.get_arrivals(stop_id, limit=5)
            payload = ArrivalsResponse(stop_id=stop_id, limit=5, arrivals=items).model_dump()
            yield f"data: {json.dumps(payload)}\\n\\n"
            await asyncio.sleep(max(1, interval))
    return StreamingResponse(eventgen(), media_type="text/event-stream")

# Debug seeder (runs *inside* API process so memory backend sees it)
from ..service.schemas import Arrival
@router.post("/debug/seed")
async def debug_seed():
    store = ArrivalStore()
    now = int(time.time())
    def mk(route, trip, stop, in_sec):
        return Arrival(
            route_id=route,
            trip_id=f"{trip}-{stop}",
            stop_id=stop,
            headsign=f"{route} to Downtown",
            arrival_epoch=now + in_sec,
            scheduled_epoch=None,
            is_approaching=in_sec < 120,
        )
    for stop in ("R23N", "R23S"):
        arrs = [mk("N","t1",stop,90), mk("N","t2",stop,240), mk("R","t3",stop,420)]
        await store.put_arrivals(stop, arrs)
    return {"ok": True, "seeded": ["R23N","R23S"], "count_per_stop": 3}


# ----- Station search (demo list; replace with GTFS later) -----
from fastapi import Query
from typing import List, Dict

# Minimal demo catalog: name -> stop_id (northbound/southbound variants)
_DEMO_STATIONS: List[Dict] = [
    {"name": "Union Square (14 St) — Northbound", "stop_id": "R23N"},
    {"name": "Union Square (14 St) — Southbound", "stop_id": "R23S"},
    {"name": "Times Sq–42 St — Northbound", "stop_id": "R16N"},
    {"name": "Times Sq–42 St — Southbound", "stop_id": "R16S"},
    {"name": "Canal St — Northbound", "stop_id": "R23N"},  # demo reuse
    {"name": "Canal St — Southbound", "stop_id": "R23S"},
]

@router.get("/stations/search")
async def stations_search(q: str = Query("", min_length=0)):
    qn = q.strip().lower()
    if not qn:
        return _DEMO_STATIONS[:6]
    return [s for s in _DEMO_STATIONS if qn in s["name"].lower()]

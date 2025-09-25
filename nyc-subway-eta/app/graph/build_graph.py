import os, csv, networkx as nx

def build_graph(gtfs_path: str) -> nx.Graph:
    G = nx.Graph()
    stops = {}
    with open(os.path.join(gtfs_path, "stops.txt"), newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            stops[row["stop_id"]] = row
            G.add_node(row["stop_id"], name=row.get("stop_name", ""))

    # Transfers (optional)
    transfers_path = os.path.join(gtfs_path, "transfers.txt")
    if os.path.exists(transfers_path):
        with open(transfers_path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                G.add_edge(row["from_stop_id"], row["to_stop_id"], transfer=True, weight=180)  # 3 min default

    return G

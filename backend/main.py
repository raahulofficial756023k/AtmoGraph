"""
main.py
FastAPI gateway for AtmoGraph.

Endpoints:
- GET  /graph            -> current supply chain graph (nodes + edges + risk)
- POST /ingest/news      -> ingest a news snippet, extract entities, bump risk
- GET  /predict/ripple   -> run the GNN over the current graph, return predicted delays
- WS   /ws/updates       -> push live graph/risk updates to the dashboard
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import torch

from graph_db import GraphDB
from nlp_pipeline import NLPIngestionEngine
from gnn_model import RippleEffectGNN, build_graph_from_neo4j_records

app = FastAPI(title="AtmoGraph API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

db = GraphDB()
nlp_engine = NLPIngestionEngine()
gnn_model = RippleEffectGNN(in_channels=8)
gnn_model.eval()

connected_clients: List[WebSocket] = []


class NewsInput(BaseModel):
    text: str


@app.on_event("startup")
def startup():
    db.init_schema()


@app.get("/graph")
def get_graph():
    records = db.get_subgraph()
    nodes = {}
    edges = []
    for r in records:
        nodes[r["source"]] = {"id": r["source"], "risk_score": r["source_risk"]}
        nodes[r["target"]] = {"id": r["target"], "risk_score": r["target_risk"]}
        edges.append({"source": r["source"], "target": r["target"], "type": r["rel_type"]})
    return {"nodes": list(nodes.values()), "edges": edges}


@app.post("/ingest/news")
async def ingest_news(payload: NewsInput):
    event = nlp_engine.extract_entities(payload.text)

    # In production: fuzzy-match entity names against a cached name->id map
    # pulled from Neo4j. Placeholder direct match here.
    entity_lookup = {n["name"].lower(): n["id"] for n in _flat_node_list()}
    matched_ids = nlp_engine.map_to_node_ids(event, entity_lookup)

    for node_id in matched_ids:
        db.update_risk(node_id, event.severity, reason=event.keyword)

    update = {
        "event": event.text,
        "keyword": event.keyword,
        "severity": event.severity,
        "affected_nodes": matched_ids,
    }
    await _broadcast(update)
    return update


@app.get("/predict/ripple")
def predict_ripple():
    records = db.get_subgraph()
    if not records:
        return {"predictions": []}

    node_ids = sorted({r["source"] for r in records} | {r["target"] for r in records})
    node_index = {nid: i for i, nid in enumerate(node_ids)}

    data = build_graph_from_neo4j_records(records, node_index)
    with torch.no_grad():
        preds = gnn_model(data)

    return {
        "predictions": [
            {"node_id": nid, "predicted_delay_days": round(float(preds[idx]), 2)}
            for nid, idx in node_index.items()
        ]
    }


@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keepalive / client pings
    except WebSocketDisconnect:
        connected_clients.remove(websocket)


async def _broadcast(message: dict):
    for client in list(connected_clients):
        try:
            await client.send_json(message)
        except Exception:
            connected_clients.remove(client)


def _flat_node_list():
    records = db.get_subgraph()
    seen = {}
    for r in records:
        seen[r["source"]] = {"id": r["source"], "name": r["source"]}
        seen[r["target"]] = {"id": r["target"], "name": r["target"]}
    return list(seen.values())

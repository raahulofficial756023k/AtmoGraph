<<<<<<< HEAD
# AtmoGraph: Supply Chain Ripple Effect Predictor

Starter scaffold matching the Week 1–2 architecture from the project brief.

## Backend

```bash
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Run Neo4j locally (Docker) first:
# docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j

python graph_db.py     # seeds a small mock graph
uvicorn main:app --reload --port 8000
```

## Frontend

```bash
cd frontend
npm install
npm start
```

## What's here
- `backend/graph_db.py` — Neo4j connection, schema, mock seed data
- `backend/nlp_pipeline.py` — spaCy-based entity/disruption extraction (swap in a HuggingFace NER model for production)
- `backend/gnn_model.py` — PyTorch Geometric GNN for ripple-effect delay regression
- `backend/main.py` — FastAPI gateway: `/graph`, `/ingest/news`, `/predict/ripple`, `/ws/updates`
- `frontend/src/SupplyChainGraph.jsx` — D3 force-directed graph, live risk coloring, WebSocket updates

## Next steps (per the Week 3–4 plan)
- Replace the toy GNN training loop with real historical delay data
- Add fuzzy entity-to-node matching (rapidfuzz) in `nlp_pipeline.py`
- Add a timeline slider (30/60/90 days) driven by repeated GNN inference
- Dockerize both services and wire up CI/CD
=======
# AtmoGraph
>>>>>>> 88bc38999e737eb99c5a27404a4a685c4af31507

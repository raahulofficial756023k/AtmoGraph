"""
graph_db.py
Neo4j connection layer for AtmoGraph.

Stores the global supply chain network: Suppliers, Manufacturers, Ports,
and ShippingRoutes as nodes, connected by SUPPLIES / SHIPS_VIA / RECEIVES_FROM
relationships. Each node carries a `risk_score` property that the NLP +
GNN pipeline updates when a disruption is detected.
"""

from neo4j import GraphDatabase
from typing import Optional
import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


class GraphDB:
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def init_schema(self):
        """Create uniqueness constraints for core node types."""
        with self.driver.session() as session:
            for label in ["Supplier", "Manufacturer", "Port", "Region"]:
                session.run(
                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) "
                    f"REQUIRE n.id IS UNIQUE"
                )

    def upsert_node(self, label: str, node_id: str, name: str, region: str,
                     risk_score: float = 0.0):
        query = f"""
        MERGE (n:{label} {{id: $node_id}})
        SET n.name = $name, n.region = $region, n.risk_score = $risk_score
        RETURN n
        """
        with self.driver.session() as session:
            session.run(query, node_id=node_id, name=name, region=region,
                        risk_score=risk_score)

    def link_nodes(self, from_id: str, to_id: str, rel_type: str,
                   weight: float = 1.0):
        query = f"""
        MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r.weight = $weight
        """
        with self.driver.session() as session:
            session.run(query, from_id=from_id, to_id=to_id, weight=weight)

    def update_risk(self, node_id: str, risk_score: float, reason: Optional[str] = None):
        query = """
        MATCH (n {id: $node_id})
        SET n.risk_score = $risk_score, n.last_disruption_reason = $reason
        RETURN n
        """
        with self.driver.session() as session:
            session.run(query, node_id=node_id, risk_score=risk_score, reason=reason)

    def get_subgraph(self, hops: int = 2):
        """Pull the full graph (or a bounded neighborhood) for the GNN and UI."""
        query = f"""
        MATCH (n)-[r]->(m)
        RETURN n.id AS source, m.id AS target, type(r) AS rel_type,
               n.risk_score AS source_risk, m.risk_score AS target_risk
        LIMIT 5000
        """
        with self.driver.session() as session:
            result = session.run(query)
            return [dict(record) for record in result]


if __name__ == "__main__":
    db = GraphDB()
    db.init_schema()
    # Seed a tiny mock network
    db.upsert_node("Port", "port_rotterdam", "Port of Rotterdam", "Europe")
    db.upsert_node("Manufacturer", "mfg_shenzhen", "Shenzhen Electronics Co.", "Asia")
    db.upsert_node("Region", "region_na", "North America Retail", "NorthAmerica")
    db.link_nodes("mfg_shenzhen", "port_rotterdam", "SHIPS_VIA")
    db.link_nodes("port_rotterdam", "region_na", "SUPPLIES")
    print("Seeded mock graph.")
    db.close()

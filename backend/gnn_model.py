"""
gnn_model.py
Graph Neural Network (PyTorch Geometric) that predicts the "ripple effect"
of a disruption: a downstream delay (in days) for each node, based on the
risk scores propagating from an upstream disrupted node across multiple hops.

This is framed as a node regression task: given node features (including
risk_score) and the graph structure, predict `predicted_delay_days` per node.
"""

import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, GATConv
from torch_geometric.data import Data


class RippleEffectGNN(torch.nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int = 64, out_channels: int = 1):
        super().__init__()
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GATConv(hidden_channels, hidden_channels, heads=2, concat=False)
        self.conv3 = GCNConv(hidden_channels, hidden_channels)
        self.readout = torch.nn.Linear(hidden_channels, out_channels)

    def forward(self, data: Data):
        x, edge_index = data.x, data.edge_index

        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)

        x = self.conv2(x, edge_index)
        x = F.relu(x)

        x = self.conv3(x, edge_index)
        x = F.relu(x)

        # Predicted delay in days per node (regression, non-negative)
        out = F.softplus(self.readout(x))
        return out.squeeze(-1)


def build_graph_from_neo4j_records(records, node_index, feature_dim=8):
    """
    Convert Neo4j subgraph query results into a PyG Data object.
    `node_index` maps node_id -> integer index.
    Node features here are a placeholder: [risk_score, degree_bucket, ...].
    Replace with real features (industry embedding, historical volume, etc.)
    """
    edge_list = []
    risk_by_idx = {}

    for r in records:
        src, tgt = node_index[r["source"]], node_index[r["target"]]
        edge_list.append([src, tgt])
        risk_by_idx[src] = r.get("source_risk", 0.0) or 0.0
        risk_by_idx[tgt] = r.get("target_risk", 0.0) or 0.0

    num_nodes = len(node_index)
    x = torch.zeros((num_nodes, feature_dim))
    for idx, risk in risk_by_idx.items():
        x[idx, 0] = risk  # first feature slot = risk_score

    edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
    return Data(x=x, edge_index=edge_index)


def train_step(model, data, target_delays, optimizer):
    model.train()
    optimizer.zero_grad()
    pred = model(data)
    loss = F.mse_loss(pred, target_delays)
    loss.backward()
    optimizer.step()
    return loss.item()


if __name__ == "__main__":
    # Minimal smoke test with a toy graph
    model = RippleEffectGNN(in_channels=8)
    x = torch.rand((5, 8))
    edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=torch.long)
    data = Data(x=x, edge_index=edge_index)
    preds = model(data)
    print("Predicted delays (days):", preds)

import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

const API_BASE = "http://localhost:8000";

export default function SupplyChainGraph() {
  const svgRef = useRef(null);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);

  // Initial graph load
  useEffect(() => {
    fetch(`${API_BASE}/graph`)
      .then((res) => res.json())
      .then((data) => {
        setNodes(data.nodes);
        setEdges(data.edges);
      })
      .catch((err) => console.error("Failed to load graph:", err));
  }, []);

  // Live updates via WebSocket
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/updates");
    ws.onmessage = (msg) => {
      const update = JSON.parse(msg.data);
      setNodes((prev) =>
        prev.map((n) =>
          update.affected_nodes.includes(n.id)
            ? { ...n, risk_score: update.severity }
            : n
        )
      );
    };
    return () => ws.close();
  }, []);

  // D3 force-directed render
  useEffect(() => {
    if (!nodes.length) return;

    const width = 800;
    const height = 600;
    const svg = d3.select(svgRef.current).attr("viewBox", [0, 0, width, height]);
    svg.selectAll("*").remove();

    const simulation = d3
      .forceSimulation(nodes)
      .force("link", d3.forceLink(edges).id((d) => d.id).distance(120))
      .force("charge", d3.forceManyBody().strength(-250))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg
      .append("g")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke-width", 1.5);

    const node = svg
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", 14)
      .attr("fill", (d) => riskColor(d.risk_score))
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .style("cursor", "pointer")
      .on("click", (_, d) => setSelectedNode(d))
      .call(drag(simulation));

    const label = svg
      .append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d) => d.id)
      .attr("font-size", 10)
      .attr("dx", 18)
      .attr("dy", 4);

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
      label.attr("x", (d) => d.x).attr("y", (d) => d.y);
    });

    return () => simulation.stop();
  }, [nodes, edges]);

  return (
    <div style={{ display: "flex", gap: "1rem", fontFamily: "sans-serif" }}>
      <svg ref={svgRef} width={800} height={600} style={{ border: "1px solid #ddd" }} />
      <div style={{ minWidth: 220 }}>
        <h3>Node Details</h3>
        {selectedNode ? (
          <div>
            <p><strong>ID:</strong> {selectedNode.id}</p>
            <p><strong>Risk Score:</strong> {selectedNode.risk_score?.toFixed(2) ?? "0.00"}</p>
          </div>
        ) : (
          <p>Click a node to see details.</p>
        )}
      </div>
    </div>
  );
}

function riskColor(risk = 0) {
  if (risk > 0.7) return "#e53935"; // high risk - red
  if (risk > 0.4) return "#fb8c00"; // medium - orange
  return "#43a047"; // low - green
}

function drag(simulation) {
  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }
  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }
  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }
  return d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended);
}

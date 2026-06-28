"""
builder.py
----------
Builds and renders the equipment-procedure-regulation knowledge graph.

Node types (colour coded in the UI):
  equipment   → red      (#e74c3c)
  regulation  → blue     (#2980b9)
  process     → green    (#27ae60)
  parameter   → orange   (#e67e22)
  location    → purple   (#8e44ad)

We use networkx for graph operations and pyvis for the HTML render so the
Streamlit component can embed it as an iframe.
"""

from __future__ import annotations
from pathlib import Path
import networkx as nx
from config import STORE_DIR

_NODE_COLORS = {
    "equipment":  "#e74c3c",
    "regulation": "#2980b9",
    "process":    "#27ae60",
    "parameter":  "#e67e22",
    "location":   "#8e44ad",
    "default":    "#95a5a6",
}
_NODE_SIZES = {
    "equipment":  30,
    "regulation": 25,
    "process":    22,
    "parameter":  18,
    "location":   20,
    "default":    15,
}

GRAPH_HTML_PATH = STORE_DIR / "knowledge_graph.html"


class KnowledgeGraph:
    def __init__(self) -> None:
        self.g: nx.DiGraph = nx.DiGraph()

    def add_entities(self, entities: dict, source: str = "") -> None:
        """Add extracted entities as nodes and inferred relationships as edges."""
        for tag in entities.get("equipment", []):
            self._add_node(tag, "equipment", source)
        for reg in entities.get("regulations", []):
            self._add_node(reg, "regulation", source)
        for proc in entities.get("processes", []):
            self._add_node(proc, "process", source)
        for param in entities.get("parameters", []):
            self._add_node(param, "parameter", source)
        for loc in entities.get("locations", []):
            self._add_node(loc, "location", source)
        for rel in entities.get("relationships", []):
            frm = rel.get("from", "")
            to  = rel.get("to", "")
            label = rel.get("relation", "RELATED_TO")
            if frm and to and self.g.has_node(frm) and self.g.has_node(to):
                self.g.add_edge(frm, to, label=label)

    def _add_node(self, name: str, kind: str, source: str) -> None:
        if not name:
            return
        if self.g.has_node(name):
            self.g.nodes[name].setdefault("sources", set()).add(source)
        else:
            self.g.add_node(
                name,
                kind=kind,
                color=_NODE_COLORS.get(kind, _NODE_COLORS["default"]),
                size=_NODE_SIZES.get(kind, _NODE_SIZES["default"]),
                sources={source},
            )

    def node_count(self) -> int:
        return self.g.number_of_nodes()

    def edge_count(self) -> int:
        return self.g.number_of_edges()

    def stats(self) -> dict:
        kinds: dict[str, int] = {}
        for _, data in self.g.nodes(data=True):
            k = data.get("kind", "default")
            kinds[k] = kinds.get(k, 0) + 1
        return {
            "nodes": self.g.number_of_nodes(),
            "edges": self.g.number_of_edges(),
            "by_type": kinds,
        }

    def render_html(self) -> Path:
        """Write an interactive pyvis graph to STORE_DIR and return its path."""
        from pyvis.network import Network

        net = Network(
            height="620px",
            width="100%",
            bgcolor="#1e1e2e",
            font_color="#cdd6f4",
            directed=True,
        )
        net.set_options("""
        {
          "physics": {"barnesHut": {"gravitationalConstant": -8000, "springLength": 150}},
          "edges": {"color": {"color": "#6c7086"}, "smooth": {"type": "curvedCW", "roundness": 0.2}},
          "interaction": {"tooltipDelay": 100, "hideEdgesOnDrag": true}
        }
        """)

        for node, data in self.g.nodes(data=True):
            srcs = ", ".join(sorted(data.get("sources", set())))
            net.add_node(
                node,
                label=node,
                color=data.get("color", _NODE_COLORS["default"]),
                size=data.get("size", 15),
                title=f"{data.get('kind','?').upper()}<br>Sources: {srcs}",
            )

        for src, dst, data in self.g.edges(data=True):
            net.add_edge(src, dst, title=data.get("label", ""), label=data.get("label", ""))

        net.save_graph(str(GRAPH_HTML_PATH))
        return GRAPH_HTML_PATH

    def get_neighbors(self, node: str) -> list[dict]:
        """Return neighbours with edge labels for the sidebar detail panel."""
        results = []
        for nbr in self.g.successors(node):
            results.append({
                "node": nbr,
                "direction": "→",
                "relation": self.g[node][nbr].get("label", ""),
                "kind": self.g.nodes[nbr].get("kind", ""),
            })
        for nbr in self.g.predecessors(node):
            results.append({
                "node": nbr,
                "direction": "←",
                "relation": self.g[nbr][node].get("label", ""),
                "kind": self.g.nodes[nbr].get("kind", ""),
            })
        return results

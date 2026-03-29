from __future__ import annotations

import json
from pathlib import Path

from app.core.config import GRAPH_HTML
from app.core.utils import pretty_ref
from app.engines.study_assistant import CROSS_REFERENCES

try:
    import networkx as nx  # type: ignore
except Exception:
    nx = None

try:
    from pyvis.network import Network  # type: ignore
except Exception:
    Network = None


class KnowledgeGraphEngine:
    def export_html(self) -> str:
        if nx is not None and Network is not None:
            graph = nx.Graph()
            for source, targets in CROSS_REFERENCES.items():
                source_label = pretty_ref(*source)
                graph.add_node(source_label, title=source_label)
                for target in targets:
                    target_label = pretty_ref(*target)
                    graph.add_node(target_label, title=target_label)
                    graph.add_edge(source_label, target_label)

            network = Network(height="700px", width="100%", bgcolor="#111111", font_color="white")
            network.from_nx(graph)
            network.write_html(str(GRAPH_HTML), notebook=False)
            return str(GRAPH_HTML)

        nodes: list[dict[str, str]] = []
        edges: list[dict[str, str]] = []
        seen: set[str] = set()
        for source, targets in CROSS_REFERENCES.items():
            source_label = pretty_ref(*source)
            if source_label not in seen:
                nodes.append({"id": source_label, "label": source_label})
                seen.add(source_label)
            for target in targets:
                target_label = pretty_ref(*target)
                if target_label not in seen:
                    nodes.append({"id": target_label, "label": target_label})
                    seen.add(target_label)
                edges.append({"from": source_label, "to": target_label})

        html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Bible Knowledge Graph</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body {{ background:#111; color:#fff; font-family:Arial,sans-serif; margin:0; }}
    #mynetwork {{ width:100vw; height:100vh; border:0; }}
    .note {{ position:fixed; top:8px; left:8px; background:#222; padding:8px 12px; border-radius:8px; z-index:10; }}
  </style>
</head>
<body>
  <div class="note">Fallback graph export active (install networkx + pyvis for richer layouts).</div>
  <div id="mynetwork"></div>
  <script>
    const nodes = new vis.DataSet({json.dumps(nodes)});
    const edges = new vis.DataSet({json.dumps(edges)});
    const container = document.getElementById('mynetwork');
    const data = {{ nodes, edges }};
    const options = {{
      nodes: {{ shape:'dot', size:18, font:{{color:'#fff'}} }},
      edges: {{ color:'#aaa' }},
      physics: {{ stabilization:true }},
      interaction: {{ hover:true }}
    }};
    new vis.Network(container, data, options);
  </script>
</body>
</html>
"""
        Path(GRAPH_HTML).write_text(html, encoding="utf-8")
        return str(GRAPH_HTML)

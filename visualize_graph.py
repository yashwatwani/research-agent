import pickle
import os
import json
import webbrowser
import networkx as nx

GRAPH_PATH = "data/graph/knowledge_graph.pkl"
HTML_PATH = "data/graph/knowledge_graph.html"


# export_to_json — loads graph from disk, returns nodes and edges as dict
def export_to_json():
    if not os.path.exists(GRAPH_PATH):
        print("No graph found. Run a test first.")
        return None

    with open(GRAPH_PATH, "rb") as f:
        graph = pickle.load(f)

    data = {
        "nodes": [{"id": node} for node in graph.nodes()],
        "links": [
            {
                "source": u,
                "target": v,
                "relation": d.get("relation", ""),
                "source_title": d.get("source_title", "")
            }
            for u, v, d in graph.edges(data=True)
        ]
    }

    print(f"Graph loaded: {len(data['nodes'])} nodes, {len(data['links'])} edges")
    return data


# generate_html — builds a self contained interactive HTML visualizer
# from the current graph state and opens it in your browser
def generate_html(data: dict):
    graph_json = json.dumps(data)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>ResearchAgent Knowledge Graph</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, sans-serif; background: #f9f9f7; color: #1a1a1a; }}

    #header {{ padding: 20px 24px 12px; border-bottom: 0.5px solid #e0e0d8; background: white; }}
    #header h1 {{ font-size: 16px; font-weight: 500; }}
    #header p {{ font-size: 13px; color: #888; margin-top: 4px; }}

    #stats {{ display: flex; gap: 12px; padding: 12px 24px; background: white; border-bottom: 0.5px solid #e0e0d8; }}
    .stat {{ background: #f4f3ef; border-radius: 8px; padding: 8px 16px; }}
    .stat-label {{ font-size: 11px; color: #888; }}
    .stat-value {{ font-size: 20px; font-weight: 500; }}

    #info-bar {{ padding: 10px 24px; font-size: 13px; color: #534AB7; background: #EEEDFE; min-height: 36px; }}

    #graph {{ width: 100%; height: calc(100vh - 160px); }}

    .node circle {{ cursor: pointer; transition: all 0.2s; }}
    .node text {{ pointer-events: none; font-size: 10px; font-weight: 500; }}
    .edge-label {{ font-size: 9px; fill: #534AB7; pointer-events: none; }}

    #hint {{ position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
             font-size: 12px; color: #888; background: white;
             padding: 6px 14px; border-radius: 20px; border: 0.5px solid #e0e0d8; }}
  </style>
</head>
<body>

<div id="header">
  <h1>ResearchAgent — Knowledge Graph</h1>
  <p>Auto-generated from extracted entities and relationships. Updates every time new sources are stored.</p>
</div>

<div id="stats">
  <div class="stat">
    <div class="stat-label">nodes</div>
    <div class="stat-value" id="node-count">0</div>
  </div>
  <div class="stat">
    <div class="stat-label">edges</div>
    <div class="stat-value" id="edge-count">0</div>
  </div>
  <div class="stat" style="flex:1">
    <div class="stat-label">sources</div>
    <div class="stat-value" id="source-count">0</div>
  </div>
</div>

<div id="info-bar">Click any node to see its connections</div>
<svg id="graph"></svg>
<div id="hint">drag · scroll to zoom · click to highlight</div>

<script>
const graphData = {graph_json};

document.getElementById("node-count").textContent = graphData.nodes.length;
document.getElementById("edge-count").textContent = graphData.links.length;
const sources = new Set(graphData.links.map(l => l.source_title).filter(Boolean));
document.getElementById("source-count").textContent = sources.size;

const W = window.innerWidth;
const H = window.innerHeight - 160;
const svg = d3.select("#graph").attr("width", W).attr("height", H);
const g = svg.append("g");

svg.call(d3.zoom().scaleExtent([0.2, 4]).on("zoom", e => g.attr("transform", e.transform)));

svg.append("defs").append("marker")
  .attr("id", "arrow").attr("viewBox", "0 -5 10 10")
  .attr("refX", 24).attr("refY", 0)
  .attr("markerWidth", 6).attr("markerHeight", 6)
  .attr("orient", "auto")
  .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", "#1D9E75");

const sim = d3.forceSimulation(graphData.nodes)
  .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(140))
  .force("charge", d3.forceManyBody().strength(-500))
  .force("center", d3.forceCenter(W / 2, H / 2))
  .force("collision", d3.forceCollide(44));

const link = g.append("g").selectAll("line")
  .data(graphData.links).join("line")
  .attr("stroke", "#1D9E75")
  .attr("stroke-width", 1.5)
  .attr("stroke-opacity", 0.6)
  .attr("marker-end", "url(#arrow)");

const edgeLabel = g.append("g").selectAll("text")
  .data(graphData.links).join("text")
  .attr("class", "edge-label")
  .attr("text-anchor", "middle")
  .attr("dy", -4)
  .text(d => d.relation);

const node = g.append("g").selectAll("g")
  .data(graphData.nodes).join("g")
  .attr("class", "node")
  .call(d3.drag()
    .on("start", (e, d) => {{ if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
    .on("drag", (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
    .on("end", (e, d) => {{ if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }}))
  .on("click", (e, d) => {{
    const connected = new Set([d.id]);
    const rels = [];
    graphData.links.forEach(l => {{
      const src = l.source.id || l.source;
      const tgt = l.target.id || l.target;
      if (src === d.id || tgt === d.id) {{
        connected.add(src);
        connected.add(tgt);
        rels.push(`${{src}} → ${{l.relation}} → ${{tgt}}`);
      }}
    }});
    node.select("circle")
      .attr("fill", n => n.id === d.id ? "#7F77DD" : connected.has(n.id) ? "#AFA9EC" : "#EEEDFE")
      .attr("stroke", n => n.id === d.id ? "#3C3489" : connected.has(n.id) ? "#534AB7" : "#AFA9EC");
    node.select("text")
      .attr("fill", n => n.id === d.id ? "white" : connected.has(n.id) ? "#3C3489" : "#888");
    link.attr("stroke-opacity", l => {{
      const src = l.source.id || l.source;
      const tgt = l.target.id || l.target;
      return (src === d.id || tgt === d.id) ? 1 : 0.1;
    }});
    document.getElementById("info-bar").textContent =
      d.id + " · " + rels.length + " connection" + (rels.length !== 1 ? "s" : "") + " · " + rels.join(" | ");
  }});

node.append("circle")
  .attr("r", 22)
  .attr("fill", "#EEEDFE")
  .attr("stroke", "#AFA9EC")
  .attr("stroke-width", 1);

node.append("text")
  .attr("text-anchor", "middle")
  .attr("dy", "0.35em")
  .attr("fill", "#3C3489")
  .text(d => d.id.length > 11 ? d.id.slice(0, 10) + "…" : d.id);

sim.on("tick", () => {{
  link
    .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  edgeLabel
    .attr("x", d => (d.source.x + d.target.x) / 2)
    .attr("y", d => (d.source.y + d.target.y) / 2);
  node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
}});
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(HTML_PATH), exist_ok=True)
    with open(HTML_PATH, "w") as f:
        f.write(html)

    print(f"Graph saved to {HTML_PATH}")
    webbrowser.open(f"file://{os.path.abspath(HTML_PATH)}")
    print("Opened in browser.")


if __name__ == "__main__":
    data = export_to_json()
    if data:
        generate_html(data)
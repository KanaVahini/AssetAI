import { useState, useEffect, useRef, useCallback } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { forceCollide } from "d3-force";
import { fetchGraphData } from "../services/graphService";

const LABEL_COLORS = {
  Plant: "#f79767",
  Equipment: "#57c7e3",
  Document: "#8dcc93",
  Person: "#ecb5c9",
  Regulation: "#d9c8ae",
};

// Nodes with more connections should be visually "heavier" (bigger + more
// central), same as the "Bharat Process Indu" hub in the reference image.
const BASE_RADIUS = 10;
const RADIUS_PER_LINK = 1.1;
const MAX_RADIUS = 34;

function wrapText(ctx, text, maxWidth) {
  const words = String(text).split(" ");
  const lines = [];
  let currentLine = words[0] || "";
  for (let i = 1; i < words.length; i++) {
    const testLine = currentLine + " " + words[i];
    if (ctx.measureText(testLine).width < maxWidth) {
      currentLine = testLine;
    } else {
      lines.push(currentLine);
      currentLine = words[i];
    }
  }
  lines.push(currentLine);
  return lines;
}

export default function KnowledgeGraph() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const containerRef = useRef(null);
  const fgRef = useRef(null);

  useEffect(() => {
    fetchGraphData()
      .then((data) => {
        // Count degree per node so hub-like nodes render bigger/heavier,
        // exactly like the big orange "Bharat Process Indu" node in the
        // reference screenshot.
        const degree = {};
        data.edges.forEach((e) => {
          degree[e.source] = (degree[e.source] || 0) + 1;
          degree[e.target] = (degree[e.target] || 0) + 1;
        });

        let hubId = null;
        let hubDegree = -1;
        Object.entries(degree).forEach(([id, d]) => {
          if (d > hubDegree) {
            hubDegree = d;
            hubId = id;
          }
        });

        const nodes = data.nodes.map((n) => {
          const d = degree[n.id] || 0;
          return {
            id: n.id,
            name:
              n.properties?.name ||
              n.properties?.tag ||
              n.properties?.filename ||
              n.properties?.code ||
              n.label,
            label: n.label,
            degree: d,
            radius: Math.min(MAX_RADIUS, BASE_RADIUS + d * RADIUS_PER_LINK),
            isHub: n.id === hubId,
          };
        });

        setGraphData({
          nodes,
          links: data.edges.map((e) => ({
            source: e.source,
            target: e.target,
            type: e.type,
          })),
        });
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to load graph data");
        setLoading(false);
      });
  }, []);

  // Tune the physics once data is loaded so the layout settles into a clean
  // radial arrangement (hub in the middle, rings of related nodes around
  // it) instead of the default clumped/overlapping layout.
  const handleEngineStop = useCallback(() => {
    fgRef.current?.zoomToFit(400, 60);
  }, []);

  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || graphData.nodes.length === 0) return;

    // Push nodes apart based on how "big" they are so large hub nodes get
    // more breathing room, and add collision detection so circles never
    // overlap or sit on top of their own labels.
    fg.d3Force("charge").strength((node) => -120 - node.degree * 12);
    fg.d3Force("link")
      .distance((link) => {
        const s = typeof link.source === "object" ? link.source : { degree: 0 };
        const t = typeof link.target === "object" ? link.target : { degree: 0 };
        // Hub-adjacent links stay shorter so rings hug the center like the
        // reference image; leaf-to-leaf links get more room.
        return 60 + Math.max(s.degree || 0, t.degree || 0) * 1.5;
      })
      .strength(0.35);
    fg.d3Force(
      "collide",
      forceCollide((node) => node.radius + 14)
    );
    // Weaken the pull to center so the graph spreads into rings rather than
    // bunching in the middle.
    fg.d3Force("center")?.strength(0.02);

    // Pin the hub node in place at the center, like the fixed orange node
    // in the reference image.
    const hub = graphData.nodes.find((n) => n.isHub);
    if (hub) {
      hub.fx = 0;
      hub.fy = 0;
    }

    fg.d3ReheatSimulation();
  }, [graphData]);

  if (loading) return <div className="p-4">Loading knowledge graph...</div>;
  if (error) return <div className="p-4 text-red-500">{error}</div>;
  if (graphData.nodes.length === 0)
    return <div className="p-4">No graph data found.</div>;

  return (
    <div
      ref={containerRef}
      className="w-full h-screen"
      style={{ background: "#1e2027" }}
    >
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        backgroundColor="#1e2027"
        linkColor={() => "rgba(255,255,255,0.35)"}
        linkWidth={1}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        linkDirectionalArrowColor={() => "rgba(255,255,255,0.6)"}
        linkLabel={(link) => link.type}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.35}
        cooldownTicks={200}
        onEngineStop={handleEngineStop}
        nodeRelSize={1}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const radius = node.radius || BASE_RADIUS;
          const color = LABEL_COLORS[node.label] || "#69b3a2";

          // node circle
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
          ctx.fillStyle = node.isHub ? "#f79767" : color;
          ctx.fill();

          if (node.isHub) {
            ctx.lineWidth = 2 / globalScale;
            ctx.strokeStyle = "#ffffff";
            ctx.stroke();
          }

          // wrapped label inside the circle, white text like the reference
          const fontSize = Math.max(3.4, 10 / globalScale);
          ctx.font = `${fontSize}px Sans-Serif`;
          ctx.fillStyle = "#ffffff";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          const maxWidth = radius * 1.7;
          const lines = wrapText(ctx, node.name, maxWidth).slice(0, 3);
          const lineHeight = fontSize * 1.1;
          const startY = node.y - ((lines.length - 1) * lineHeight) / 2;
          lines.forEach((line, i) => {
            ctx.fillText(line, node.x, startY + i * lineHeight);
          });
        }}
        nodeCanvasObjectMode={() => "replace"}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius || BASE_RADIUS, 0, 2 * Math.PI, false);
          ctx.fill();
        }}
      />
    </div>
  );
}
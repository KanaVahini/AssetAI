import { useState, useEffect, useRef, useCallback } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { forceCollide, forceX, forceY } from "d3-force";
import { fetchGraphData } from "../services/graphService";

// Node colors — UNCHANGED from the working version. Only the background
// is different in this file.
const LABEL_COLORS = {
  Plant: "#f79767",
  Equipment: "#57c7e3",
  Document: "#c990c0",
  Person: "#d9c8ae",
  Regulation: "#f16667",
  Location: "#8dcc93",
};
const DEFAULT_NODE_COLOR = "#a5abb6";

// ── Only the background changed: the "plant-at-night" dark gradient ──
// Inlined directly (not relying on external CSS vars/classes) so this
// renders correctly even if that stylesheet isn't loaded in your app yet.
const BACKGROUND_CSS = `
  radial-gradient(1100px 780px at 12% 8%, rgba(35, 92, 89, 0.55) 0%, rgba(35, 92, 89, 0) 55%),
  radial-gradient(900px 700px at 85% 82%, rgba(199, 123, 44, 0.14) 0%, rgba(199, 123, 44, 0) 60%),
  linear-gradient(165deg, #0D2224 0%, #0A1A26 42%, #070E14 100%)
`;
const BACKGROUND_SOLID = "#070E14"; // fallback / canvas fill color

const BASE_RADIUS = 6;
const RADIUS_PER_LINK = 0.55;
const MAX_RADIUS = 22;

const SECTOR_RADIUS = 320;
const SECTOR_STRENGTH = 0.12;

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

        const categories = [...new Set(data.nodes.map((n) => n.label))];
        const angleStep = (2 * Math.PI) / Math.max(1, categories.length);
        const angleByCategory = {};
        categories.forEach((cat, i) => {
          angleByCategory[cat] = i * angleStep;
        });

        const nodes = data.nodes.map((n) => {
          const d = degree[n.id] || 0;
          const name =
            n.properties?.name ||
            n.properties?.tag ||
            n.properties?.filename ||
            n.properties?.code ||
            n.label;
          const radius = Math.min(MAX_RADIUS, BASE_RADIUS + d * RADIUS_PER_LINK);
          return {
            id: n.id,
            name,
            label: n.label,
            degree: d,
            radius,
            isHub: n.id === hubId,
            sectorAngle: angleByCategory[n.label] ?? 0,
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

  const handleEngineStop = useCallback(() => {
    fgRef.current?.zoomToFit(400, 60);
  }, []);

  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || graphData.nodes.length === 0) return;

    fg.d3Force("charge").strength((node) => -90 - node.degree * 10);
    fg.d3Force("link")
      .distance((link) => {
        const s = typeof link.source === "object" ? link.source : { degree: 0 };
        const t = typeof link.target === "object" ? link.target : { degree: 0 };
        return 50 + Math.max(s.degree || 0, t.degree || 0) * 1.2;
      })
      .strength(0.3);

    fg.d3Force(
      "collide",
      forceCollide((node) => node.radius + 6).strength(0.9)
    );

    fg.d3Force("center")?.strength(0.02);

    fg.d3Force(
      "sectorX",
      forceX((node) => {
        if (node.isHub) return 0;
        const r = SECTOR_RADIUS + node.degree * 4;
        return Math.cos(node.sectorAngle) * r;
      }).strength((node) => (node.isHub ? 0 : SECTOR_STRENGTH))
    );
    fg.d3Force(
      "sectorY",
      forceY((node) => {
        if (node.isHub) return 0;
        const r = SECTOR_RADIUS + node.degree * 4;
        return Math.sin(node.sectorAngle) * r;
      }).strength((node) => (node.isHub ? 0 : SECTOR_STRENGTH))
    );

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
      style={{ background: `${BACKGROUND_CSS} ${BACKGROUND_SOLID}` }}
    >
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        backgroundColor={BACKGROUND_SOLID}
        linkColor={() => "rgba(143, 174, 172, 0.35)"}
        linkWidth={1}
        linkDirectionalArrowLength={5}
        linkDirectionalArrowRelPos={1}
        linkDirectionalArrowColor={() => "#E0A24E"}
        linkLabel={(link) => link.type}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.35}
        cooldownTicks={200}
        onEngineStop={handleEngineStop}
        nodeRelSize={1}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const radius = node.radius || BASE_RADIUS;
          const color = LABEL_COLORS[node.label] || DEFAULT_NODE_COLOR;

          ctx.beginPath();
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
          ctx.fillStyle = node.isHub ? "#f79767" : color;
          ctx.fill();

          if (node.isHub) {
            ctx.lineWidth = 2 / globalScale;
            ctx.strokeStyle = "#c75f2e";
            ctx.stroke();
          }

          const maxWidth = radius * 1.7;
          const maxHeight = radius * 1.6;
          let fontSize = Math.max(3, 10 / globalScale);
          const minFontSize = 1.6 / globalScale;

          let lines = [];
          while (fontSize >= minFontSize) {
            ctx.font = `${fontSize}px Sans-Serif`;
            lines = wrapText(ctx, node.name, maxWidth);
            const lineHeight = fontSize * 1.1;
            const blockHeight = lines.length * lineHeight;
            const widestLine = Math.max(
              ...lines.map((l) => ctx.measureText(l).width)
            );
            if (blockHeight <= maxHeight && widestLine <= maxWidth) break;
            fontSize -= 0.4 / globalScale;
          }

          ctx.font = `${fontSize}px Sans-Serif`;
          ctx.fillStyle = "#ffffff";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
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
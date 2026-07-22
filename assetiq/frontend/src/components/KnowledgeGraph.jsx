import { useState, useEffect, useRef, useCallback } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { forceCollide, forceX, forceY } from "d3-force";
import { fetchGraphData } from "../services/graphService";

const LABEL_COLORS = {
  Plant: "#f79767",
  Equipment: "#57c7e3",
  Document: "#c990c0",
  Person: "#d9c8ae",
  Regulation: "#f16667",
  Location: "#8dcc93",
};
const DEFAULT_NODE_COLOR = "#a5abb6";

const BACKGROUND_CSS = `
  radial-gradient(1100px 780px at 12% 8%, rgba(35, 92, 89, 0.55) 0%, rgba(35, 92, 89, 0) 55%),
  radial-gradient(900px 700px at 85% 82%, rgba(199, 123, 44, 0.14) 0%, rgba(199, 123, 44, 0) 60%),
  linear-gradient(165deg, #0D2224 0%, #0A1A26 42%, #070E14 100%)
`;
const BACKGROUND_SOLID = "#070E14";

const BASE_RADIUS = 6;
const RADIUS_PER_LINK = 0.55;
const MAX_RADIUS = 22;

// Sector layout — nodes settle onto rings by category, hub in the middle.
const SECTOR_STRENGTH = 0.7; // strong enough to actually separate categories

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

const containerStyle = {
  width: "100%",
  height: "100vh",
  minHeight: "400px",
  position: "relative",
  background: `${BACKGROUND_CSS} ${BACKGROUND_SOLID}`,
};

const overlayStyle = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: "#EDF4F2",
  fontFamily: "monospace",
  fontSize: 14,
  zIndex: 2,
};

export default function KnowledgeGraph() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const containerRef = useRef(null);
  const fgRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // This effect now attaches on the very first paint, because the
  // container div below is ALWAYS rendered (loading/error/empty states
  // are drawn as an overlay on top of it, not as separate early
  // returns). Previously the div carrying containerRef only existed
  // after `loading` became false, so on mount containerRef.current was
  // null, this effect bailed out immediately, and — since its
  // dependency array is empty — it never ran again. The ResizeObserver
  // was never actually attached, and ForceGraph2D was silently falling
  // back to its own internal auto-sizing with no explicit fallback.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) {
      console.warn("[KnowledgeGraph] containerRef was null on mount — sizing will fail");
      return;
    }
    const measure = () => {
      const rect = el.getBoundingClientRect();
      console.log("[KnowledgeGraph] measured container:", rect.width, rect.height);
      setDimensions({ width: rect.width, height: rect.height });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    console.log("[KnowledgeGraph] fetching graph data…");
    fetchGraphData()
      .then((data) => {
        console.log("[KnowledgeGraph] raw response:", data);

        // Defend against API shape mismatches — some backends return
        // `links` instead of `edges`. If neither exists we fail loudly
        // instead of throwing deep inside a .forEach on undefined.
        const rawNodes = data?.nodes ?? [];
        const rawEdges = data?.edges ?? data?.links ?? [];

        if (!Array.isArray(rawNodes) || rawNodes.length === 0) {
          console.warn("[KnowledgeGraph] response had no usable nodes array", data);
        }

        const degree = {};
        rawEdges.forEach((e) => {
          const s = e.source ?? e.from;
          const t = e.target ?? e.to;
          degree[s] = (degree[s] || 0) + 1;
          degree[t] = (degree[t] || 0) + 1;
        });

        let hubId = null;
        let hubDegree = -1;
        Object.entries(degree).forEach(([id, d]) => {
          if (d > hubDegree) {
            hubDegree = d;
            hubId = id;
          }
        });

        const categories = [...new Set(rawNodes.map((n) => n.label))];
        const angleStep = (2 * Math.PI) / Math.max(1, categories.length);
        const angleByCategory = {};
        categories.forEach((cat, i) => {
          angleByCategory[cat] = i * angleStep;
        });

        // Count nodes per category so dense categories fan across a wider
        // arc instead of every node in a category stacking on one spoke.
        const countByCategory = {};
        rawNodes.forEach((n) => {
          countByCategory[n.label] = (countByCategory[n.label] || 0) + 1;
        });
        const indexInCategory = {};

        const nodes = rawNodes.map((n) => {
          const d = degree[n.id] || 0;
          const name =
            n.properties?.name ||
            n.properties?.tag ||
            n.properties?.filename ||
            n.properties?.code ||
            n.label;
          const radius = Math.min(MAX_RADIUS, BASE_RADIUS + d * RADIUS_PER_LINK);

          const catCount = countByCategory[n.label] || 1;
          const idx = indexInCategory[n.label] || 0;
          indexInCategory[n.label] = idx + 1;

          const fan = Math.min(0.9, catCount * 0.05);
          const jitter = catCount > 1 ? (idx / (catCount - 1) - 0.5) * fan : 0;

          return {
            id: n.id,
            name,
            label: n.label,
            degree: d,
            radius,
            isHub: n.id === hubId,
            sectorAngle: (angleByCategory[n.label] ?? 0) + jitter,
          };
        });

        const links = rawEdges.map((e) => ({
          source: e.source ?? e.from,
          target: e.target ?? e.to,
          type: e.type,
        }));

        console.log("[KnowledgeGraph] parsed nodes/links:", nodes.length, links.length);

        setGraphData({ nodes, links });
        setLoading(false);
      })
      .catch((err) => {
        console.error("[KnowledgeGraph] fetchGraphData failed:", err);
        setError("Failed to load graph data: " + (err?.message || String(err)));
        setLoading(false);
      });
  }, []);

  // Fit the view only once the simulation actually reports it has settled.
  const handleEngineStop = useCallback(() => {
    fgRef.current?.zoomToFit(400, 60);
  }, []);

  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || graphData.nodes.length === 0) return;

    const n = graphData.nodes.length;
    const sectorRadius = Math.max(220, Math.sqrt(n) * 55);

    fg.d3Force("charge").strength((node) => -60 - node.degree * 6);
    fg.d3Force("link").distance(30).strength(0.4);
    fg.d3Force("collide", forceCollide((node) => node.radius + 10).strength(0.9));
    fg.d3Force("center", null);

    fg.d3Force(
      "sectorX",
      forceX((node) => {
        if (node.isHub) return 0;
        const r = sectorRadius + node.degree * 3;
        return Math.cos(node.sectorAngle) * r;
      }).strength(SECTOR_STRENGTH)
    );
    fg.d3Force(
      "sectorY",
      forceY((node) => {
        if (node.isHub) return 0;
        const r = sectorRadius + node.degree * 3;
        return Math.sin(node.sectorAngle) * r;
      }).strength(SECTOR_STRENGTH)
    );

    const hub = graphData.nodes.find((node) => node.isHub);
    if (hub) {
      hub.fx = 0;
      hub.fy = 0;
    }

    // Guarded: on a zero-size container the internal simulation engine
    // hasn't finished initializing yet, so these methods may not exist
    // for a tick. Don't let that crash the whole component — log it
    // instead so the real (layout) cause is visible without an
    // unrelated uncaught exception burying it.
    try {
      if (typeof fg.d3AlphaDecay === "function") fg.d3AlphaDecay(0.024);
      if (typeof fg.d3VelocityDecay === "function") fg.d3VelocityDecay(0.42);
      if (typeof fg.d3ReheatSimulation === "function") fg.d3ReheatSimulation();
    } catch (e) {
      console.warn("[KnowledgeGraph] d3 tuning skipped — engine not ready:", e);
    }
  }, [graphData]);

  const showLoading = loading;
  const showError = !loading && error;
  const showEmpty = !loading && !error && graphData.nodes.length === 0;
  const showGraph = !loading && !error && graphData.nodes.length > 0;

  return (
    <div ref={containerRef} style={containerStyle}>
      {showLoading && <div style={overlayStyle}>Loading knowledge graph…</div>}
      {showError && <div style={{ ...overlayStyle, color: "#f16667" }}>{error}</div>}
      {showEmpty && <div style={overlayStyle}>No graph data found.</div>}

      {showGraph && (
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          width={dimensions.width || undefined}
          height={dimensions.height || undefined}
          backgroundColor={BACKGROUND_SOLID}
          linkColor={() => "rgba(143, 174, 172, 0.25)"}
          linkWidth={1}
          linkCurvature={0.15}
          linkDirectionalArrowLength={0}
          linkLabel={(link) => link.type}
          d3AlphaDecay={0.024}
          d3VelocityDecay={0.42}
          cooldownTicks={200}
          cooldownTime={6000}
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

            if (globalScale < 0.55) return;

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
              const widestLine = Math.max(...lines.map((l) => ctx.measureText(l).width));
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
      )}
    </div>
  );
}
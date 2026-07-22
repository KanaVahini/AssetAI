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
  const [hoverNode, setHoverNode] = useState(null);

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

  // Highlight connections for any hovered node (no degree restriction).
  const highlightActive = Boolean(hoverNode);

  const isLinkOnHoverNode = (link) => {
    if (!highlightActive) return false;
    const sourceId = typeof link.source === "object" ? link.source.id : link.source;
    const targetId = typeof link.target === "object" ? link.target.id : link.target;
    return sourceId === hoverNode.id || targetId === hoverNode.id;
  };

  // Neighbor nodes of the hovered node — drives both the enlarged
  // rendering on the canvas and the name list shown beside the graph.
  const connectedNodes = highlightActive
    ? graphData.links
        .filter(isLinkOnHoverNode)
        .map((link) => {
          const sourceId = typeof link.source === "object" ? link.source.id : link.source;
          const otherRef = sourceId === hoverNode.id ? link.target : link.source;
          const otherId = typeof otherRef === "object" ? otherRef.id : otherRef;
          return typeof otherRef === "object"
            ? otherRef
            : graphData.nodes.find((n) => n.id === otherId);
        })
        .filter(Boolean)
    : [];

  const connectedNodeIds = new Set(connectedNodes.map((n) => n.id));

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
          onNodeHover={(node) => setHoverNode(node)}
          linkCanvasObjectMode={(link) => (isLinkOnHoverNode(link) ? "replace" : undefined)}
          linkCanvasObject={(link, ctx) => {
            const start = link.source;
            const end = link.target;
            if (typeof start !== "object" || typeof end !== "object") return;

            // Orient the gradient outward from the hovered node so the
            // color grading reads as "flowing" from the node being
            // inspected toward each of its connections.
            const fromHover = start.id === hoverNode.id;
            const from = fromHover ? start : end;
            const to = fromHover ? end : start;

            const gradient = ctx.createLinearGradient(from.x, from.y, to.x, to.y);
            gradient.addColorStop(0, "#E0A24E");
            gradient.addColorStop(1, "#4FBFA8");

            ctx.strokeStyle = gradient;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(start.x, start.y);
            ctx.lineTo(end.x, end.y);
            ctx.stroke();
          }}
          d3AlphaDecay={0.024}
          d3VelocityDecay={0.42}
          cooldownTicks={200}
          cooldownTime={6000}
          onEngineStop={handleEngineStop}
          nodeRelSize={1}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const isHoverOrConnected =
              highlightActive && (node.id === hoverNode.id || connectedNodeIds.has(node.id));
            const radius = (node.radius || BASE_RADIUS) * (isHoverOrConnected ? 1.7 : 1);
            const color = LABEL_COLORS[node.label] || DEFAULT_NODE_COLOR;

            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
            ctx.fillStyle = node.isHub ? "#f79767" : color;
            ctx.fill();

            if (isHoverOrConnected) {
              ctx.lineWidth = 2 / globalScale;
              ctx.strokeStyle = "#EDF4F2";
              ctx.stroke();
            }

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

      {/* Legend — explains the hover behavior directly on the page */}
      {showGraph && (
        <div
          style={{
            position: "absolute",
            top: 16,
            left: 16,
            zIndex: 3,
            maxWidth: 320,
            padding: "10px 14px",
            borderRadius: 6,
            background: "rgba(16, 34, 46, 0.82)",
            border: "1px solid rgba(178, 212, 208, 0.26)",
            color: "#8FAEAC",
            fontFamily: "monospace",
            fontSize: 11,
            lineHeight: 1.5,
            pointerEvents: "none",
          }}
        >
          Hover any node to see its links highlighted with a color
          gradient, its connected nodes enlarged, and a list of those
          connections here on the right.
        </div>
      )}

      {/* Connections panel — shown beside the graph while a qualifying
          node (fewer than 5 connections) is hovered */}
      {showGraph && highlightActive && (
        <div
          style={{
            position: "absolute",
            top: 16,
            right: 16,
            bottom: 16,
            width: 240,
            zIndex: 3,
            padding: "14px 16px",
            borderRadius: 6,
            background: "rgba(16, 34, 46, 0.9)",
            border: "1px solid rgba(178, 212, 208, 0.26)",
            color: "#EDF4F2",
            fontFamily: "monospace",
            overflowY: "auto",
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
            {hoverNode.name}
          </div>
          <div style={{ fontSize: 10, color: "#8FAEAC", marginBottom: 10 }}>
            {connectedNodes.length} connection{connectedNodes.length === 1 ? "" : "s"}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, boxSizing: "border-box" }}>
            {connectedNodes.map((n) => (
              <div
                key={n.id}
                style={{
                  fontSize: 12,
                  padding: "4px 8px",
                  borderRadius: 4,
                  background: "rgba(224, 162, 78, 0.12)",
                  color: "#EDF4F2",
                  boxSizing: "border-box",
                  width: "100%",
                  whiteSpace: "normal",
                  overflowWrap: "break-word",
                  wordBreak: "break-word",
                }}
              >
                {n.name}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
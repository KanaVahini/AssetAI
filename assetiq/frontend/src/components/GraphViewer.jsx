import KnowledgeGraph from './KnowledgeGraph'

/**
 * GraphViewer — thin wrapper around KnowledgeGraph.
 *
 * This file was previously a placeholder:
 *   export default function GraphViewer() {
 *     return <div>GraphViewer placeholder</div>
 *   }
 *
 * If your router's /graph route imports GraphViewer instead of
 * KnowledgeGraph directly, that placeholder is why nothing rendered —
 * it was never a bug in the graph code itself, just an empty stand-in
 * component sitting in front of it. Routing here now mounts the real
 * graph regardless of which filename the route references.
 */
export default function GraphViewer() {
  return <KnowledgeGraph />
}
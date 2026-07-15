import Gauge from './Gauge'

export default function Loader() {
  return (
    <div className="thinking-row">
      <Gauge value={50} sweeping size={44} tone="amber" label="" />
      <span className="thinking-label">Copilot is reading the documents…</span>
    </div>
  )
}

import Gauge from './Gauge'

export default function Loader({ label = 'Copilot is reading the documents…' }) {
  return (
    <div className="thinking-row">
      <Gauge value={50} sweeping size={44} tone="amber" label="" />
      <span className="thinking-label">{label}</span>
    </div>
  )
}

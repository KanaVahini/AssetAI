export default function SourceCard({ filename }) {
  const getIcon = (name) => {
    if (name.endsWith('.pdf')) return '▤'
    if (name.endsWith('.csv')) return '▦'
    if (name.endsWith('.jpeg') || name.endsWith('.jpg') || name.endsWith('.png')) return '▥'
    return '▧'
  }

  return (
    <div className="source-tag" title={filename}>
      <span className="source-tag__icon">{getIcon(filename)}</span>
      {filename}
    </div>
  )
}

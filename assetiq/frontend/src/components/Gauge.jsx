import { useEffect, useState } from 'react'

/**
 * Gauge — the signature visual element of AssetIQ.
 * A pressure-gauge dial, styled after the instruments that
 * appear throughout the plant's own equipment (PG tags, bearing
 * temperature readouts). Used in the hero, as the "thinking"
 * loader (sweeping needle), and as a status indicator.
 *
 * value: 0-100
 * sweeping: if true, needle animates back and forth (loading state)
 * size: pixel size of the square viewBox
 */
export default function Gauge({
  value = 72,
  label = 'SYSTEM',
  sweeping = false,
  size = 180,
  tone = 'amber' // amber | green | red
}) {
  const [sweepValue, setSweepValue] = useState(20)

  useEffect(() => {
    if (!sweeping) return
    let dir = 1
    let v = 20
    const id = setInterval(() => {
      v += dir * 4
      if (v >= 92) dir = -1
      if (v <= 12) dir = 1
      setSweepValue(v)
    }, 60)
    return () => clearInterval(id)
  }, [sweeping])

  const displayValue = sweeping ? sweepValue : value

  const toneColor = {
    amber: 'var(--brass-solid)',
    green: 'var(--verdigris)',
    red: 'var(--rust)'
  }[tone]

  // Gauge sweeps 220 degrees, from -110deg to +110deg
  const angle = -110 + (displayValue / 100) * 220
  const ticks = Array.from({ length: 12 })

  return (
    <div style={{ width: size, height: size, position: 'relative' }}>
      <svg viewBox="0 0 200 200" width={size} height={size}>
        {/* Outer bezel */}
        <circle cx="100" cy="100" r="94" fill="var(--panel-solid)" stroke="var(--border-strong)" strokeWidth="2" />
        <circle cx="100" cy="100" r="82" fill="none" stroke="var(--border)" strokeWidth="1" />

        {/* Tick marks */}
        {ticks.map((_, i) => {
          const tickAngle = -110 + (i / (ticks.length - 1)) * 220
          const rad = (tickAngle * Math.PI) / 180
          const x1 = 100 + 70 * Math.sin(rad)
          const y1 = 100 - 70 * Math.cos(rad)
          const x2 = 100 + 80 * Math.sin(rad)
          const y2 = 100 - 80 * Math.cos(rad)
          const isMajor = i % 3 === 0
          return (
            <line
              key={i}
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke={isMajor ? 'var(--text-muted)' : 'var(--border-strong)'}
              strokeWidth={isMajor ? 2 : 1}
            />
          )
        })}

        {/* Danger zone arc (top right of dial) */}
        <path
          d="M 155 45 A 82 82 0 0 1 180 100"
          fill="none"
          stroke="var(--rust)"
          strokeWidth="4"
          opacity="0.5"
        />

        {/* Needle */}
        <g style={{ transition: sweeping ? 'none' : 'transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)' }}>
          <line
            x1="100" y1="100"
            x2={100 + 62 * Math.sin((angle * Math.PI) / 180)}
            y2={100 - 62 * Math.cos((angle * Math.PI) / 180)}
            stroke={toneColor}
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="100" cy="100" r="7" fill={toneColor} />
          <circle cx="100" cy="100" r="3" fill="var(--panel-solid)" />
        </g>

        {/* Readout value — omitted at small sizes where it wouldn't be legible */}
        {size >= 80 && (
          <>
            <text
              x="100" y="132"
              textAnchor="middle"
              fill="var(--text-primary)"
              fontFamily="var(--font-mono)"
              fontSize="20"
              fontWeight="600"
            >
              {Math.round(displayValue)}
            </text>
            <text
              x="100" y="150"
              textAnchor="middle"
              fill="var(--text-muted)"
              fontFamily="var(--font-mono)"
              fontSize="9"
              letterSpacing="2"
            >
              {label}
            </text>
          </>
        )}
      </svg>
    </div>
  )
}

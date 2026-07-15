import { useEffect, useRef } from 'react'

/**
 * KnowledgeField — the signature element of AssetIQ.
 *
 * Stages, visually, the exact problem the brief describes:
 * seven disconnected document systems (P&IDs, work orders, SOPs,
 * inspection reports, email archives, OEM manuals, compliance logs)
 * scattered in isolated clusters — then pulled together, live, into
 * one connected knowledge graph. It never fully settles; the mesh
 * keeps a slow ambient pulse, because the graph is meant to be
 * continuously updated, not a static diagram.
 *
 * Pure canvas, no dependencies. Respects prefers-reduced-motion by
 * rendering a single settled frame with no animation loop.
 */

const HUB_LABELS = [
  'P&IDs',
  'WORK ORDERS',
  'SOPs',
  'INSPECTION REPORTS',
  'EMAIL ARCHIVES',
  'OEM MANUALS',
  'COMPLIANCE LOGS'
]

const RECORDS_PER_HUB = 6
const ASSEMBLY_DURATION = 2600 // ms

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

export default function KnowledgeField() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let width = 0
    let height = 0
    let dpr = Math.min(window.devicePixelRatio || 1, 2)

    const resize = () => {
      const rect = canvas.parentElement.getBoundingClientRect()
      width = rect.width
      height = rect.height
      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = width + 'px'
      canvas.style.height = height + 'px'
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const rand = (a, b) => a + Math.random() * (b - a)

    // Build hubs: scattered "before" position (isolated, near edges)
    // and a settled "after" position (loose ring, unified).
    const hubs = HUB_LABELS.map((label, i) => {
      const angle = (i / HUB_LABELS.length) * Math.PI * 2 - Math.PI / 2
      const settleRadius = Math.min(width, height) * 0.30
      return {
        label,
        scatterX: rand(0.08, 0.92) * width,
        scatterY: rand(0.12, 0.88) * height,
        settleX: 0, // computed after resize below (needs width/height)
        settleY: 0,
        angle,
        settleRadius,
        wanderSeed: rand(0, 1000),
        records: Array.from({ length: RECORDS_PER_HUB }).map(() => ({
          offX: rand(-46, 46),
          offY: rand(-46, 46),
          jitterSeed: rand(0, 1000)
        }))
      }
    })

    const computeSettlePositions = () => {
      const cx = width / 2
      const cy = height / 2
      hubs.forEach(h => {
        h.settleX = cx + Math.cos(h.angle) * h.settleRadius
        h.settleY = cy + Math.sin(h.angle) * h.settleRadius * 0.72
      })
    }
    computeSettlePositions()

    const start = performance.now()
    let raf = null

    const drawFrame = (now) => {
      const elapsed = now - start
      const rawT = reducedMotion ? 1 : Math.min(elapsed / ASSEMBLY_DURATION, 1)
      const t = easeInOutCubic(rawT)
      const cohesion = rawT // 0 -> 1, used to fade in cross-hub mesh

      ctx.clearRect(0, 0, width, height)

      const hubPositions = hubs.map(h => {
        const bx = h.scatterX + (h.settleX - h.scatterX) * t
        const by = h.scatterY + (h.settleY - h.scatterY) * t
        // gentle perpetual wander once mostly settled
        const wander = reducedMotion ? 0 : Math.min(cohesion, 1)
        const wx = Math.sin((elapsed / 2600) + h.wanderSeed) * 10 * wander
        const wy = Math.cos((elapsed / 3100) + h.wanderSeed) * 10 * wander
        return { x: bx + wx, y: by + wy, label: h.label }
      })

      // Cross-hub mesh — fades in once cohesion builds, gently pulses after
      const pulse = 0.35 + 0.15 * Math.sin(elapsed / 1400)
      for (let i = 0; i < hubPositions.length; i++) {
        for (let j = i + 1; j < hubPositions.length; j++) {
          const a = hubPositions[i]
          const b = hubPositions[j]
          const meshOpacity = Math.max(0, cohesion - 0.45) * 1.8 * pulse
          if (meshOpacity <= 0.01) continue
          ctx.strokeStyle = `rgba(224, 162, 78, ${meshOpacity * 0.3})`
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(a.x, a.y)
          ctx.lineTo(b.x, b.y)
          ctx.stroke()
        }
      }

      // Records: small dots orbiting their hub, with a line to it
      hubs.forEach((h, hi) => {
        const hub = hubPositions[hi]
        h.records.forEach(r => {
          const jt = reducedMotion ? 0 : elapsed / 1800
          const jx = Math.sin(jt + r.jitterSeed) * 6
          const jy = Math.cos(jt * 0.8 + r.jitterSeed) * 6
          const rx = hub.x + r.offX * (0.5 + 0.5 * t) + jx
          const ry = hub.y + r.offY * (0.5 + 0.5 * t) + jy

          ctx.strokeStyle = 'rgba(143, 174, 172, 0.16)'
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(hub.x, hub.y)
          ctx.lineTo(rx, ry)
          ctx.stroke()

          ctx.fillStyle = 'rgba(143, 174, 172, 0.55)'
          ctx.beginPath()
          ctx.arc(rx, ry, 1.6, 0, Math.PI * 2)
          ctx.fill()
        })
      })

      // Hub nodes + labels
      hubPositions.forEach(hub => {
        ctx.beginPath()
        ctx.arc(hub.x, hub.y, 4.5, 0, Math.PI * 2)
        ctx.fillStyle = '#E0A24E'
        ctx.shadowColor = 'rgba(224, 162, 78, 0.8)'
        ctx.shadowBlur = 10
        ctx.fill()
        ctx.shadowBlur = 0

        ctx.font = '500 10px "IBM Plex Mono", monospace'
        ctx.fillStyle = 'rgba(237, 244, 242, 0.55)'
        ctx.textAlign = hub.x < width / 2 ? 'right' : 'left'
        const offsetX = hub.x < width / 2 ? -10 : 10
        ctx.fillText(hub.label, hub.x + offsetX, hub.y + 3)
      })

      if (!reducedMotion || rawT < 1) {
        raf = requestAnimationFrame(drawFrame)
      }
    }

    raf = requestAnimationFrame(drawFrame)

    return () => {
      window.removeEventListener('resize', resize)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

  return <canvas ref={canvasRef} className="knowledge-field" aria-hidden="true" />
}

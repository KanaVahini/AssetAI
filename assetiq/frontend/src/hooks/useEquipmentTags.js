import { useState, useEffect } from 'react'
import { getEquipmentTags } from '../services/api'

/**
 * Fetches the real equipment tags currently indexed in the knowledge graph.
 * Returns an empty array (never fake/example data) if the backend call
 * fails or the corpus has no tagged equipment yet — callers should hide
 * whatever UI depends on this rather than fall back to placeholder tags.
 */
export default function useEquipmentTags(limit = 5) {
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    getEquipmentTags()
      .then(result => {
        if (cancelled) return
        setTags((result.tags || []).slice(0, limit))
      })
      .catch(() => {
        if (!cancelled) setTags([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [limit])

  return { tags, loading }
}
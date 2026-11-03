import { useEffect, useState } from 'react'

export interface Identity {
  name: string
  role: string
}

const STORAGE_KEY = 'suryasutra-identity'

function readStoredIdentity(): Identity | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Identity
    return parsed.name && parsed.role ? parsed : null
  } catch {
    return null
  }
}

/** Per-viewer identification, not authentication — there's no server-side account or
 * password (CLAUDE.md's auth/multi-tenant work is explicitly pilot-stage, not
 * prototype). This exists so feedback submissions carry a real, human-entered name
 * and role instead of a hardcoded placeholder. */
export function useIdentity(): [Identity | null, (identity: Identity) => void, () => void] {
  const [identity, setIdentityState] = useState<Identity | null>(readStoredIdentity)

  useEffect(() => {
    try {
      if (identity) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(identity))
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
    } catch {
      // per-viewer convenience only; fine if storage is unavailable
    }
  }, [identity])

  const setIdentity = (next: Identity) => setIdentityState(next)
  const clearIdentity = () => setIdentityState(null)

  return [identity, setIdentity, clearIdentity]
}

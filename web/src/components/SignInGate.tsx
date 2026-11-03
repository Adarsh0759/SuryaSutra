import { LogIn, SunMedium } from 'lucide-react'
import { useState } from 'react'
import type { Identity } from '../useIdentity'

interface SignInGateProps {
  onSignIn: (identity: Identity) => void
}

const ROLES = ['technician', 'site_engineer', 'manager']

/** Identification, not authentication — no password, no server-side account (see
 * useIdentity.ts). Gates /app so feedback has a real name/role attached to it. */
export function SignInGate({ onSignIn }: SignInGateProps) {
  const [name, setName] = useState('')
  const [role, setRole] = useState(ROLES[0])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onSignIn({ name: name.trim(), role })
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-bg p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-border bg-surface-1 p-6"
      >
        <h1 className="flex items-center gap-2 text-xl font-bold text-text-1">
          <SunMedium className="text-accent" size={22} strokeWidth={2} />
          SuryaSutra
        </h1>
        <p className="mt-1 text-sm text-text-2">
          Sign in with your name and role — this identifies your feedback, it isn't a
          password-protected account.
        </p>

        <label className="mt-5 block text-sm text-text-2">
          Name
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Ravi Kumar"
            autoFocus
            className="mt-1 w-full rounded-sm border border-border bg-surface-2 px-2 py-1.5 text-text-1"
          />
        </label>

        <label className="mt-3 block text-sm text-text-2">
          Role
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="mt-1 w-full rounded-sm border border-border bg-surface-2 px-2 py-1.5 text-text-1"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r.replace('_', ' ')}
              </option>
            ))}
          </select>
        </label>

        <button
          type="submit"
          disabled={!name.trim()}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-medium text-accent-text transition-transform hover:brightness-105 active:scale-[0.97] disabled:opacity-40"
        >
          <LogIn size={16} strokeWidth={1.75} />
          Sign in
        </button>
      </form>
    </div>
  )
}

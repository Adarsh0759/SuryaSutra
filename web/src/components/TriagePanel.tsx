import { CheckCircle2, XCircle } from 'lucide-react'
import { motion } from 'motion/react'
import type { TriageResult } from '../api/types'

interface TriagePanelProps {
  title: string
  result: TriageResult | undefined
  isPending: boolean
  isError: boolean
}

/** Compact single-method result panel, shared by compare mode. Flags missing safety
 * evidence prominently — that's the whole point of compare mode (CLAUDE.md §11). */
export function TriagePanel({ title, result, isPending, isError }: TriagePanelProps) {
  const missingSafety =
    result?.status === 'INSUFFICIENT' || (result?.status === 'ANSWERED' && result.safety.length === 0)

  return (
    <div className="flex flex-1 flex-col gap-2 rounded-md border border-border bg-surface-1 p-3">
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-sm font-semibold text-text-1">{title}</h3>
        {result && (
          <span
            className={`flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium ${
              missingSafety ? 'bg-danger/15 text-danger' : 'bg-success/15 text-success'
            }`}
          >
            {missingSafety ? (
              <XCircle size={13} strokeWidth={2} />
            ) : (
              <CheckCircle2 size={13} strokeWidth={2} />
            )}
            {result.status}
          </span>
        )}
      </div>

      {isPending && <p className="text-xs text-text-3">Running...</p>}
      {isError && <p className="text-xs text-danger">Request failed.</p>}

      {missingSafety && (
        <motion.p
          initial={{ x: 0 }}
          animate={{ x: [0, -4, 4, -4, 4, 0] }}
          transition={{ duration: 0.3 }}
          className="rounded-md border border-danger bg-surface-2 p-2 text-xs font-semibold text-danger"
        >
          Missing — no safety evidence in this answer
          {result?.status === 'INSUFFICIENT' ? ` (${result.reason})` : ''}
        </motion.p>
      )}

      {result?.status === 'ANSWERED' && (
        <>
          {result.safety.length > 0 && (
            <div className="rounded-md border border-border bg-surface-2 p-2 text-xs text-text-1">
              {result.safety.map((item, i) => (
                <p key={i}>{item.text}</p>
              ))}
            </div>
          )}
          <ol className="list-inside list-decimal text-xs text-text-2">
            {result.steps.map((step) => (
              <li key={step.n}>{step.action}</li>
            ))}
          </ol>
          <p className="font-mono text-xs text-text-3">
            {result.usage.input_tokens + result.usage.output_tokens} tokens · ₹
            {result.usage.cost_inr.toFixed(4)}
          </p>
        </>
      )}
    </div>
  )
}

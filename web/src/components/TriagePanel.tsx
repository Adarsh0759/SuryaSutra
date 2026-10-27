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
    <div className="flex flex-1 flex-col gap-2 rounded border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
          {title}
        </h3>
        {result && (
          <span
            className={`rounded px-2 py-0.5 text-xs font-medium ${
              missingSafety
                ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
                : 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
            }`}
          >
            {result.status}
          </span>
        )}
      </div>

      {isPending && <p className="text-xs text-slate-400 dark:text-slate-500">Running...</p>}
      {isError && <p className="text-xs text-red-600 dark:text-red-400">Request failed.</p>}

      {missingSafety && (
        <p className="rounded border border-red-400 bg-red-50 p-2 text-xs font-semibold text-red-800 dark:border-red-600 dark:bg-red-950/40 dark:text-red-300">
          ⚠ No safety evidence in this answer
          {result?.status === 'INSUFFICIENT' ? ` (${result.reason})` : ''}
        </p>
      )}

      {result?.status === 'ANSWERED' && (
        <>
          {result.safety.length > 0 && (
            <div className="rounded border border-red-300 bg-red-50 p-2 text-xs text-red-900 dark:border-red-700 dark:bg-red-950/30 dark:text-red-200">
              {result.safety.map((item, i) => (
                <p key={i}>{item.text}</p>
              ))}
            </div>
          )}
          <ol className="list-inside list-decimal text-xs text-slate-700 dark:text-slate-300">
            {result.steps.map((step) => (
              <li key={step.n}>{step.action}</li>
            ))}
          </ol>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {result.usage.input_tokens + result.usage.output_tokens} tokens · ₹
            {result.usage.cost_inr.toFixed(4)}
          </p>
        </>
      )}
    </div>
  )
}

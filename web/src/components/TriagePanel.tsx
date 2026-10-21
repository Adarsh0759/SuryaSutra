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
    <div className="flex flex-1 flex-col gap-2 rounded border border-gray-200 p-3">
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-sm font-semibold text-gray-900">{title}</h3>
        {result && (
          <span
            className={`rounded px-2 py-0.5 text-xs font-medium ${
              missingSafety ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
            }`}
          >
            {result.status}
          </span>
        )}
      </div>

      {isPending && <p className="text-xs text-gray-400">Running...</p>}
      {isError && <p className="text-xs text-red-600">Request failed.</p>}

      {missingSafety && (
        <p className="rounded border border-red-400 bg-red-50 p-2 text-xs font-semibold text-red-800">
          ⚠ No safety evidence in this answer
          {result?.status === 'INSUFFICIENT' ? ` (${result.reason})` : ''}
        </p>
      )}

      {result?.status === 'ANSWERED' && (
        <>
          {result.safety.length > 0 && (
            <div className="rounded border border-red-300 bg-red-50 p-2 text-xs text-red-900">
              {result.safety.map((item, i) => (
                <p key={i}>{item.text}</p>
              ))}
            </div>
          )}
          <ol className="list-inside list-decimal text-xs text-gray-700">
            {result.steps.map((step) => (
              <li key={step.n}>{step.action}</li>
            ))}
          </ol>
          <p className="text-xs text-gray-500">
            {result.usage.input_tokens + result.usage.output_tokens} tokens · ₹
            {result.usage.cost_inr.toFixed(4)}
          </p>
        </>
      )}
    </div>
  )
}

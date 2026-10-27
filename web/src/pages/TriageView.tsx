import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { runTriage } from '../api/client'
import { SELECTOR_METHODS, type SelectorMethod } from '../api/types'
import { CitationChips } from '../components/CitationChips'
import { SourcePanel } from '../components/SourcePanel'

interface TriageViewProps {
  alarmId: number
}

export function TriageView({ alarmId }: TriageViewProps) {
  const [method, setMethod] = useState<SelectorMethod>('requirement_complete')
  const [budget, setBudget] = useState(1000)
  const [openCitation, setOpenCitation] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => runTriage(alarmId, method, budget),
  })

  const result = mutation.data

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
        Triage alarm #{alarmId}
      </h2>

      <div className="flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-amber-50 p-3 dark:border-slate-700 dark:bg-slate-800">
        <label className="flex flex-col text-sm text-slate-600 dark:text-slate-300">
          Method
          <select
            className="mt-1 rounded border border-slate-300 bg-white px-2 py-1 text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            value={method}
            onChange={(e) => setMethod(e.target.value as SelectorMethod)}
          >
            {SELECTOR_METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-sm text-slate-600 dark:text-slate-300">
          Budget (tokens)
          <input
            type="number"
            min={1}
            className="mt-1 w-28 rounded border border-slate-300 bg-white px-2 py-1 text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
          />
        </label>
        <button
          type="button"
          className="rounded bg-amber-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50 dark:bg-amber-500 dark:hover:bg-amber-600"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? 'Running...' : 'Run triage'}
        </button>
      </div>

      {mutation.isError && (
        <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-700 dark:bg-red-950/40 dark:text-red-300">
          {mutation.error instanceof Error ? mutation.error.message : 'Request failed'}
        </p>
      )}

      {result?.status === 'INSUFFICIENT' && (
        <div className="rounded border border-amber-400 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-600 dark:bg-amber-950/30 dark:text-amber-200">
          <p className="font-semibold">Insufficient evidence ({result.reason})</p>
          {result.missing_requirements.length > 0 && (
            <ul className="mt-1 list-disc pl-5">
              {result.missing_requirements.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          <p className="mt-2">{result.suggested_next}</p>
        </div>
      )}

      {result?.status === 'ANSWERED' && (
        <>
          <div className="rounded border-2 border-red-400 bg-red-50 p-3 dark:border-red-600 dark:bg-red-950/30">
            <p className="font-semibold text-red-800 dark:text-red-300">Safety</p>
            <ul className="mt-1 space-y-1 text-sm text-red-900 dark:text-red-200">
              {result.safety.map((item, i) => (
                <li key={i}>
                  {item.text}
                  <CitationChips ids={item.citations} onOpen={setOpenCitation} />
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
            <p className="font-semibold text-slate-800 dark:text-slate-100">Likely causes</p>
            <ul className="mt-1 space-y-1 text-sm text-slate-700 dark:text-slate-300">
              {result.likely_causes.map((c, i) => (
                <li key={i}>
                  {c.cause}{' '}
                  <span className="text-slate-400 dark:text-slate-500">({c.confidence})</span>
                  <CitationChips ids={c.citations} onOpen={setOpenCitation} />
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
            <p className="font-semibold text-slate-800 dark:text-slate-100">Steps</p>
            <ol className="mt-1 space-y-2 text-sm text-slate-700 dark:text-slate-300">
              {result.steps.map((step) => (
                <li key={step.n}>
                  <span className="font-medium text-slate-900 dark:text-slate-100">{step.n}.</span>{' '}
                  {step.action}
                  <div className="text-slate-500 dark:text-slate-400">
                    Expected: {step.expected_result}
                  </div>
                  <CitationChips ids={step.citations} onOpen={setOpenCitation} />
                </li>
              ))}
            </ol>
          </div>

          {result.escalate_if.length > 0 && (
            <div className="rounded border border-orange-300 bg-orange-50 p-3 text-sm text-orange-800 dark:border-orange-700 dark:bg-orange-950/30 dark:text-orange-200">
              <p className="font-semibold">Escalate if</p>
              <ul className="mt-1 list-disc pl-5">
                {result.escalate_if.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}

          {result.uncertainties.length > 0 && (
            <div className="rounded border border-slate-200 bg-amber-50 p-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              <p className="font-semibold text-slate-800 dark:text-slate-100">Uncertainties</p>
              <ul className="mt-1 list-disc pl-5">
                {result.uncertainties.map((u, i) => (
                  <li key={i}>{u}</li>
                ))}
              </ul>
            </div>
          )}

          {/* CLAUDE.md §11 also asks for latency here — the backend doesn't return
              it in the usage object yet (CLAUDE.md §10's contract never included
              it), so it's omitted rather than faked. */}
          <div className="flex flex-wrap gap-4 rounded border border-slate-200 bg-amber-50 p-3 text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
            <span>Input tokens: {result.usage.input_tokens}</span>
            <span>Output tokens: {result.usage.output_tokens}</span>
            <span>Cost: ₹{result.usage.cost_inr.toFixed(4)}</span>
            <span>Budget: {result.usage.budget}</span>
            <span>Method: {result.usage.method}</span>
          </div>

          {openCitation && result.sources[openCitation] && (
            <SourcePanel
              citationId={openCitation}
              source={result.sources[openCitation]}
              onClose={() => setOpenCitation(null)}
            />
          )}
        </>
      )}
    </div>
  )
}

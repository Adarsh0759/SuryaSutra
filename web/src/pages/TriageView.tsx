import { useMutation } from '@tanstack/react-query'
import { AlertCircle, HelpCircle, TriangleAlert } from 'lucide-react'
import { motion } from 'motion/react'
import { useState } from 'react'
import { runTriage } from '../api/client'
import { SELECTOR_METHODS, type SelectorMethod } from '../api/types'
import { CitationChips } from '../components/CitationChips'
import { SafetyBox } from '../components/SafetyBox'
import { SourcePanel } from '../components/SourcePanel'
import { stagger } from '../motion/tokens'

interface TriageViewProps {
  alarmId: number
}

function TriageSkeleton() {
  return (
    <div className="flex flex-col gap-3" aria-live="polite" aria-label="Running triage">
      {[88, 64, 96, 72].map((w, i) => (
        <div
          key={i}
          className="h-16 animate-pulse rounded-md border border-border bg-surface-2"
          style={{ width: `${w}%` }}
        />
      ))}
    </div>
  )
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
      <h2 className="text-lg font-semibold text-text-1">Triage alarm #{alarmId}</h2>

      <div className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-surface-1 p-3">
        <label className="flex flex-col text-sm text-text-2">
          Method
          <select
            className="mt-1 rounded-sm border border-border bg-surface-2 px-2 py-1 text-text-1"
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
        <label className="flex flex-col text-sm text-text-2">
          Budget (tokens)
          <input
            type="number"
            min={1}
            className="mt-1 w-28 rounded-sm border border-border bg-surface-2 px-2 py-1 text-text-1"
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
          />
        </label>
        <button
          type="button"
          className="rounded-full bg-accent px-4 py-1.5 text-sm font-medium text-accent-text transition-transform hover:brightness-105 active:scale-[0.97] disabled:opacity-40"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? 'Running...' : 'Run triage'}
        </button>
      </div>

      {mutation.isPending && <TriageSkeleton />}

      {mutation.isError && (
        <p className="flex items-center gap-2 rounded-md border border-danger bg-surface-2 p-3 text-sm text-danger">
          <AlertCircle size={16} strokeWidth={1.75} />
          {mutation.error instanceof Error ? mutation.error.message : 'Request failed'}
        </p>
      )}

      {result?.status === 'INSUFFICIENT' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.22 }}
          className="rounded-md border border-warning bg-surface-2 p-3 text-sm text-text-1"
        >
          <p className="flex items-center gap-2 font-semibold text-warning">
            <TriangleAlert size={16} strokeWidth={1.75} />
            Not enough evidence for a safe answer ({result.reason})
          </p>
          {result.missing_requirements.length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-text-2">
              {result.missing_requirements.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-text-2">{result.suggested_next}</p>
        </motion.div>
      )}

      {result?.status === 'ANSWERED' && (
        <>
          <SafetyBox items={result.safety} onOpenCitation={setOpenCitation} />

          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, delay: stagger.list }}
            className="rounded-md border border-border bg-surface-1 p-3"
          >
            <p className="font-semibold text-text-1">Likely causes</p>
            <ul className="mt-1 space-y-1 text-sm text-text-2">
              {result.likely_causes.map((c, i) => (
                <li key={i}>
                  {c.cause} <span className="text-text-3">({c.confidence})</span>
                  <CitationChips ids={c.citations} onOpen={setOpenCitation} />
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, delay: stagger.list * 2 }}
            className="rounded-md border border-border bg-surface-1 p-3"
          >
            <p className="font-semibold text-text-1">Steps</p>
            <ol className="mt-1 space-y-2 text-sm text-text-2">
              {result.steps.map((step) => (
                <li key={step.n}>
                  <span className="font-medium text-text-1">{step.n}.</span> {step.action}
                  <div className="text-text-3">Expected: {step.expected_result}</div>
                  <CitationChips ids={step.citations} onOpen={setOpenCitation} />
                </li>
              ))}
            </ol>
          </motion.div>

          {result.escalate_if.length > 0 && (
            <div className="rounded-md border border-border bg-surface-2 p-3 text-sm text-text-1">
              <p className="flex items-center gap-2 font-semibold">
                <AlertCircle size={16} strokeWidth={1.75} className="text-warning" />
                Escalate if
              </p>
              <ul className="mt-1 list-disc pl-5 text-text-2">
                {result.escalate_if.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}

          {result.uncertainties.length > 0 && (
            <div className="rounded-md border border-border bg-surface-1 p-3 text-sm text-text-2">
              <p className="flex items-center gap-2 font-semibold text-text-1">
                <HelpCircle size={16} strokeWidth={1.75} />
                Uncertainties
              </p>
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
          <div className="flex flex-wrap gap-4 rounded-md border border-border bg-surface-2 p-3 font-mono text-xs text-text-3">
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

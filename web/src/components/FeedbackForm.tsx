import { useMutation } from '@tanstack/react-query'
import { Check } from 'lucide-react'
import { useState } from 'react'
import { submitFeedback } from '../api/client'
import { FEEDBACK_OUTCOMES, type FeedbackOutcome } from '../api/types'
import { useIdentity } from '../useIdentity'

interface FeedbackFormProps {
  runId: number
}

const OUTCOME_LABELS: Record<FeedbackOutcome, string> = {
  fixed: 'Fixed',
  not_fixed: 'Not fixed',
  wrong_step: 'A step was wrong',
  unsafe: 'Unsafe',
}

/** Wires up POST /feedback — previously had no frontend at all (CLAUDE.md §4.2's
 * technician feedback loop was built backend-only, pilot-stage UI deferred; this is
 * the minimal real UI for it, not the full pilot version). */
export function FeedbackForm({ runId }: FeedbackFormProps) {
  const [identity] = useIdentity()
  const [note, setNote] = useState('')
  const [submittedOutcome, setSubmittedOutcome] = useState<FeedbackOutcome | null>(null)

  const mutation = useMutation({
    mutationFn: (outcome: FeedbackOutcome) =>
      submitFeedback(runId, identity?.role ?? 'unknown', outcome, note || undefined),
    onSuccess: (_data, outcome) => setSubmittedOutcome(outcome),
  })

  if (submittedOutcome) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-success bg-surface-2 p-3 text-sm text-success">
        <Check size={16} strokeWidth={1.75} />
        Marked "{OUTCOME_LABELS[submittedOutcome]}". Thanks — this is stored against run
        #{runId}.
      </div>
    )
  }

  return (
    <div className="rounded-md border border-border bg-surface-1 p-3">
      <p className="text-sm font-medium text-text-1">Did this resolve the alarm?</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {FEEDBACK_OUTCOMES.map((outcome) => (
          <button
            key={outcome}
            type="button"
            onClick={() => mutation.mutate(outcome)}
            disabled={mutation.isPending}
            className="rounded-full border border-border px-3 py-1.5 text-xs font-medium text-text-1 transition-colors hover:border-interactive disabled:opacity-40"
          >
            {OUTCOME_LABELS[outcome]}
          </button>
        ))}
      </div>
      <input
        type="text"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Optional note"
        className="mt-2 w-full rounded-sm border border-border bg-surface-2 px-2 py-1 text-sm text-text-1"
      />
      {mutation.isError && (
        <p className="mt-2 text-xs text-danger">Could not submit feedback. Try again.</p>
      )}
    </div>
  )
}

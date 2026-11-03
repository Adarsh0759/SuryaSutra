import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { deleteFeedback, listFeedback, updateFeedback } from '../api/client'
import { FEEDBACK_OUTCOMES, type Feedback, type FeedbackOutcome } from '../api/types'

const OUTCOME_LABELS: Record<FeedbackOutcome, string> = {
  fixed: 'Fixed',
  not_fixed: 'Not fixed',
  wrong_step: 'A step was wrong',
  unsafe: 'Unsafe',
}

function EditRow({ entry, onDone }: { entry: Feedback; onDone: () => void }) {
  const [outcome, setOutcome] = useState<FeedbackOutcome>(entry.outcome)
  const [note, setNote] = useState(entry.note ?? '')
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => updateFeedback(entry.id, { outcome, note }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feedback'] })
      onDone()
    },
  })

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-md border border-interactive bg-surface-2 p-2">
      <select
        value={outcome}
        onChange={(e) => setOutcome(e.target.value as FeedbackOutcome)}
        className="rounded-sm border border-border bg-surface-1 px-2 py-1 text-sm text-text-1"
      >
        {FEEDBACK_OUTCOMES.map((o) => (
          <option key={o} value={o}>
            {OUTCOME_LABELS[o]}
          </option>
        ))}
      </select>
      <input
        type="text"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        className="min-w-48 flex-1 rounded-sm border border-border bg-surface-1 px-2 py-1 text-sm text-text-1"
      />
      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="rounded-full bg-accent px-3 py-1 text-xs font-medium text-accent-text disabled:opacity-40"
      >
        Save
      </button>
      <button type="button" onClick={onDone} className="text-text-3 hover:text-text-1">
        <X size={16} strokeWidth={1.75} />
      </button>
    </div>
  )
}

/** Makes Update and Delete on `feedback` visible and usable, not just curl-able —
 * POST (FeedbackForm.tsx) and GET were the only ones with a UI before this. */
export function FeedbackList() {
  const [editingId, setEditingId] = useState<number | null>(null)
  const queryClient = useQueryClient()

  const { data: entries, isLoading, isError } = useQuery({
    queryKey: ['feedback'],
    queryFn: listFeedback,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteFeedback,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['feedback'] }),
  })

  if (isLoading) return <p className="p-4 text-sm text-text-2">Loading feedback...</p>
  if (isError) return <p className="p-4 text-sm text-danger">Could not load feedback.</p>

  if (!entries || entries.length === 0) {
    return (
      <p className="rounded-md border border-border bg-surface-1 p-4 text-sm text-text-2">
        No feedback submitted yet. Mark an outcome after running a triage to see it here.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-text-1">Feedback</h2>
      <div className="flex flex-col gap-2">
        {entries.map((entry) =>
          editingId === entry.id ? (
            <EditRow key={entry.id} entry={entry} onDone={() => setEditingId(null)} />
          ) : (
            <div
              key={entry.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border bg-surface-1 p-2 text-sm"
            >
              <div>
                <span className="font-medium text-text-1">{OUTCOME_LABELS[entry.outcome]}</span>
                <span className="ml-2 text-text-3">
                  run #{entry.run_id} · {entry.user_role}
                </span>
                {entry.note && <p className="text-text-2">{entry.note}</p>}
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setEditingId(entry.id)}
                  className="text-text-3 hover:text-interactive"
                  aria-label={`Edit feedback ${entry.id}`}
                >
                  <Pencil size={15} strokeWidth={1.75} />
                </button>
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(entry.id)}
                  className="text-text-3 hover:text-danger"
                  aria-label={`Delete feedback ${entry.id}`}
                >
                  <Trash2 size={15} strokeWidth={1.75} />
                </button>
              </div>
            </div>
          ),
        )}
      </div>
    </div>
  )
}

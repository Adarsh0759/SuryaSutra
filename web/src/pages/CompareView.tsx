import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { runTriage } from '../api/client'
import { SELECTOR_METHODS, type SelectorMethod } from '../api/types'
import { TriagePanel } from '../components/TriagePanel'

interface CompareViewProps {
  alarmId: number
}

export function CompareView({ alarmId }: CompareViewProps) {
  const [methodA, setMethodA] = useState<SelectorMethod>('topk')
  const [methodB, setMethodB] = useState<SelectorMethod>('requirement_complete')
  const [budget, setBudget] = useState(500)

  const mutationA = useMutation({ mutationFn: () => runTriage(alarmId, methodA, budget) })
  const mutationB = useMutation({ mutationFn: () => runTriage(alarmId, methodB, budget) })

  const runBoth = () => {
    mutationA.mutate()
    mutationB.mutate()
  }

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
        Compare methods — alarm #{alarmId}
      </h2>

      <div className="flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-amber-50 p-3 dark:border-slate-700 dark:bg-slate-800">
        <label className="flex flex-col text-sm text-slate-600 dark:text-slate-300">
          Method A
          <select
            className="mt-1 rounded border border-slate-300 bg-white px-2 py-1 text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            value={methodA}
            onChange={(e) => setMethodA(e.target.value as SelectorMethod)}
          >
            {SELECTOR_METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-sm text-slate-600 dark:text-slate-300">
          Method B
          <select
            className="mt-1 rounded border border-slate-300 bg-white px-2 py-1 text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            value={methodB}
            onChange={(e) => setMethodB(e.target.value as SelectorMethod)}
          >
            {SELECTOR_METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-sm text-slate-600 dark:text-slate-300">
          Budget (tokens, shared)
          <input
            type="number"
            min={1}
            className="mt-1 w-32 rounded border border-slate-300 bg-white px-2 py-1 text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
          />
        </label>
        <button
          type="button"
          className="rounded bg-amber-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50 dark:bg-amber-500 dark:hover:bg-amber-600"
          onClick={runBoth}
          disabled={mutationA.isPending || mutationB.isPending}
        >
          Run compare
        </button>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <TriagePanel
          title={methodA}
          result={mutationA.data}
          isPending={mutationA.isPending}
          isError={mutationA.isError}
        />
        <TriagePanel
          title={methodB}
          result={mutationB.data}
          isPending={mutationB.isPending}
          isError={mutationB.isError}
        />
      </div>
    </div>
  )
}

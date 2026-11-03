import { useQuery } from '@tanstack/react-query'
import { CircleX } from 'lucide-react'
import { useMemo, useState } from 'react'
import { getAlarms } from '../api/client'
import { SyntheticBadge } from '../components/SyntheticBadge'

interface AlarmQueueProps {
  selectedAlarmId: number | null
  onSelectAlarm: (alarmId: number) => void
}

export function AlarmQueue({ selectedAlarmId, onSelectAlarm }: AlarmQueueProps) {
  const [siteFilter, setSiteFilter] = useState<string>('all')
  const [hideUnanswerable, setHideUnanswerable] = useState(false)

  const { data: alarms, isLoading, isError, error } = useQuery({
    queryKey: ['alarms'],
    queryFn: getAlarms,
  })

  const sites = useMemo(
    () => Array.from(new Set((alarms ?? []).map((a) => a.site_id))).sort(),
    [alarms],
  )

  const filteredAlarms = useMemo(
    () =>
      (alarms ?? []).filter(
        (a) =>
          (siteFilter === 'all' || a.site_id === siteFilter) &&
          (!hideUnanswerable || a.answerable !== false),
      ),
    [alarms, siteFilter, hideUnanswerable],
  )

  if (isLoading) {
    return <p className="p-4 text-sm text-text-2">Loading alarms...</p>
  }

  if (isError) {
    return (
      <p className="p-4 text-sm text-danger">
        Could not load alarms: {error instanceof Error ? error.message : 'unknown error'}
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-text-1">Alarm queue</h2>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-text-2">
            <input
              type="checkbox"
              checked={hideUnanswerable}
              onChange={(e) => setHideUnanswerable(e.target.checked)}
            />
            Hide test cases
          </label>
          <label className="flex items-center gap-2 text-sm text-text-2">
            Site:
            <select
              className="rounded-sm border border-border bg-surface-2 px-2 py-1 text-sm text-text-1"
              value={siteFilter}
              onChange={(e) => setSiteFilter(e.target.value)}
            >
              <option value="all">All</option>
              {sites.map((site) => (
                <option key={site} value={site}>
                  {site}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <p className="text-xs text-text-3">
        Click any alarm below to see an AI-generated, cited triage plan for it. Rows
        marked <span className="text-danger">"Will abstain"</span> are intentionally
        unanswerable test cases — the system correctly refuses to guess on these, by
        design.
      </p>

      <div className="overflow-x-auto rounded-md border border-border bg-surface-1">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="bg-surface-2">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-text-3">Time</th>
              <th className="px-3 py-2 text-left font-medium text-text-3">Site</th>
              <th className="px-3 py-2 text-left font-medium text-text-3">Inverter</th>
              <th className="px-3 py-2 text-left font-medium text-text-3">Code</th>
              <th className="px-3 py-2 text-left font-medium text-text-3">Message</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredAlarms.map((alarm) => (
              <tr
                key={alarm.id}
                onClick={() => onSelectAlarm(alarm.id)}
                className={`cursor-pointer transition-colors hover:bg-surface-2 ${
                  selectedAlarmId === alarm.id ? 'bg-surface-2' : ''
                } ${alarm.answerable === false ? 'opacity-60' : ''}`}
              >
                <td className="px-3 py-2 whitespace-nowrap text-text-3">
                  {new Date(alarm.raised_at).toLocaleString()}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-text-1">{alarm.site_id}</td>
                <td className="px-3 py-2 whitespace-nowrap text-text-1">{alarm.inverter_id}</td>
                <td className="px-3 py-2 font-mono whitespace-nowrap text-text-1">{alarm.code}</td>
                <td className="px-3 py-2 text-text-2">
                  {alarm.message}
                  {alarm.is_synthetic && <SyntheticBadge />}
                  {alarm.answerable === false && (
                    <span className="ml-2 inline-flex items-center gap-1 rounded-sm border border-danger px-1.5 py-0.5 text-xs font-medium text-danger">
                      <CircleX size={12} strokeWidth={2} />
                      Will abstain
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { getAlarms } from '../api/client'

interface AlarmQueueProps {
  selectedAlarmId: number | null
  onSelectAlarm: (alarmId: number) => void
}

export function AlarmQueue({ selectedAlarmId, onSelectAlarm }: AlarmQueueProps) {
  const [siteFilter, setSiteFilter] = useState<string>('all')

  const { data: alarms, isLoading, isError, error } = useQuery({
    queryKey: ['alarms'],
    queryFn: getAlarms,
  })

  const sites = useMemo(
    () => Array.from(new Set((alarms ?? []).map((a) => a.site_id))).sort(),
    [alarms],
  )

  const filteredAlarms = useMemo(
    () => (alarms ?? []).filter((a) => siteFilter === 'all' || a.site_id === siteFilter),
    [alarms, siteFilter],
  )

  if (isLoading) {
    return <p className="p-4 text-sm text-slate-500 dark:text-slate-400">Loading alarms...</p>
  }

  if (isError) {
    return (
      <p className="p-4 text-sm text-red-600 dark:text-red-400">
        Could not load alarms: {error instanceof Error ? error.message : 'unknown error'}
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Alarm queue</h2>
        <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          Site:
          <select
            className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
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

      <p className="text-xs text-slate-500 dark:text-slate-400">
        Click any alarm below to see an AI-generated, cited triage plan for it.
      </p>

      <div className="overflow-x-auto rounded border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
        <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
          <thead className="bg-amber-50 dark:bg-slate-900">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400">Time</th>
              <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400">Site</th>
              <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400">Inverter</th>
              <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400">Code</th>
              <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400">Message</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
            {filteredAlarms.map((alarm) => (
              <tr
                key={alarm.id}
                onClick={() => onSelectAlarm(alarm.id)}
                className={`cursor-pointer hover:bg-amber-50 dark:hover:bg-amber-900/20 ${
                  selectedAlarmId === alarm.id ? 'bg-amber-100 dark:bg-amber-900/40' : ''
                }`}
              >
                <td className="whitespace-nowrap px-3 py-2 text-slate-500 dark:text-slate-400">
                  {new Date(alarm.raised_at).toLocaleString()}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-slate-800 dark:text-slate-200">
                  {alarm.site_id}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-slate-800 dark:text-slate-200">
                  {alarm.inverter_id}
                </td>
                <td className="whitespace-nowrap px-3 py-2 font-mono text-slate-800 dark:text-slate-200">
                  {alarm.code}
                </td>
                <td className="px-3 py-2 text-slate-700 dark:text-slate-300">
                  {alarm.message}
                  {alarm.is_synthetic && (
                    <span className="ml-2 rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/50 dark:text-blue-300">
                      SYNTHETIC
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

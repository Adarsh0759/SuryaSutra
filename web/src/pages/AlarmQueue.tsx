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
    return <p className="p-4 text-sm text-gray-500">Loading alarms...</p>
  }

  if (isError) {
    return (
      <p className="p-4 text-sm text-red-600">
        Could not load alarms: {error instanceof Error ? error.message : 'unknown error'}
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-gray-900">Alarm queue</h2>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          Site:
          <select
            className="rounded border border-gray-300 px-2 py-1 text-sm"
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

      <div className="overflow-x-auto rounded border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Time</th>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Site</th>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Inverter</th>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Code</th>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Message</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredAlarms.map((alarm) => (
              <tr
                key={alarm.id}
                onClick={() => onSelectAlarm(alarm.id)}
                className={`cursor-pointer hover:bg-amber-50 ${
                  selectedAlarmId === alarm.id ? 'bg-amber-100' : ''
                }`}
              >
                <td className="whitespace-nowrap px-3 py-2 text-gray-500">
                  {new Date(alarm.raised_at).toLocaleString()}
                </td>
                <td className="whitespace-nowrap px-3 py-2">{alarm.site_id}</td>
                <td className="whitespace-nowrap px-3 py-2">{alarm.inverter_id}</td>
                <td className="whitespace-nowrap px-3 py-2 font-mono">{alarm.code}</td>
                <td className="px-3 py-2 text-gray-700">
                  {alarm.message}
                  {alarm.is_synthetic && (
                    <span className="ml-2 rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">
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

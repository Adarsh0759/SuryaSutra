import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getUsageStats } from '../api/client'

/** Cost dashboard (CLAUDE.md §11 screen 4): cost per alarm by method/budget,
 * mandatory-coverage rate, abstention counts — from real logged runs only (D-11).
 * No chart renders fake numbers: an empty dataset shows an honest empty state. */
export function Dashboard() {
  const { data: rows, isLoading, isError, error } = useQuery({
    queryKey: ['usageStats'],
    queryFn: () => getUsageStats('method,budget'),
  })

  if (isLoading) {
    return <p className="p-4 text-sm text-text-2">Loading usage stats...</p>
  }

  if (isError) {
    return (
      <p className="p-4 text-sm text-danger">
        Could not load usage stats: {error instanceof Error ? error.message : 'unknown error'}
      </p>
    )
  }

  if (!rows || rows.length === 0) {
    return (
      <p className="rounded-md border border-border bg-surface-1 p-4 text-sm text-text-2">
        No triage runs recorded yet. Run a triage or compare from the alarm queue to populate
        this dashboard — it only ever shows real logged runs, never placeholder data.
      </p>
    )
  }

  const chartData = rows
    .filter((r) => r.mean_cost_inr !== null)
    .map((r) => ({
      label: `${r.method} @ ${r.budget}`,
      mean_cost_inr: r.mean_cost_inr,
    }))

  // Recharts doesn't read our CSS variables directly, so these are the resolved
  // token values (docs/DESIGN_BRIEF.md §2.2) for the dark theme.
  const axisColor = '#6b7486' // --text-3
  const gridColor = '#1f2737' // --border
  const barColor = '#d4ff24' // --accent (lime)

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-text-1">Dashboard</h2>

      {chartData.length > 0 && (
        <div className="h-64 rounded-md border border-border bg-surface-1 p-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: axisColor }} stroke={axisColor} />
              <YAxis
                tick={{ fontSize: 11, fill: axisColor }}
                stroke={axisColor}
                label={{ value: '₹', angle: 0, position: 'insideLeft', fill: axisColor }}
              />
              <Tooltip
                formatter={(value) => (typeof value === 'number' ? value.toFixed(4) : value)}
                contentStyle={{
                  background: '#121826',
                  border: '1px solid #1f2737',
                  color: '#f2f4f8',
                }}
              />
              <Legend />
              <Bar dataKey="mean_cost_inr" name="Mean cost (₹)" fill={barColor} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="overflow-x-auto rounded-md border border-border bg-surface-1">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="bg-surface-2">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-text-3">Method</th>
              <th className="px-3 py-2 text-left font-medium text-text-3">Budget</th>
              <th className="px-3 py-2 text-right font-medium text-text-3">Runs</th>
              <th className="px-3 py-2 text-right font-medium text-text-3">Answered</th>
              <th className="px-3 py-2 text-right font-medium text-text-3">Insufficient</th>
              <th className="px-3 py-2 text-right font-medium text-text-3">Full coverage</th>
              <th className="px-3 py-2 text-right font-medium text-text-3">Mean cost (₹)</th>
              <th className="px-3 py-2 text-right font-medium text-text-3">Mean tokens (in/out)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((r, i) => (
              <tr key={i} className="text-text-1">
                <td className="px-3 py-2 font-mono">{r.method}</td>
                <td className="px-3 py-2">{r.budget}</td>
                <td className="px-3 py-2 text-right">{r.run_count}</td>
                <td className="px-3 py-2 text-right">{r.answered_count}</td>
                <td className="px-3 py-2 text-right">{r.insufficient_count}</td>
                <td className="px-3 py-2 text-right">
                  {r.full_mandatory_coverage_rate !== null
                    ? `${(r.full_mandatory_coverage_rate * 100).toFixed(0)}%`
                    : 'n/a'}
                </td>
                <td className="px-3 py-2 text-right">
                  {r.mean_cost_inr !== null ? r.mean_cost_inr.toFixed(4) : 'n/a'}
                </td>
                <td className="px-3 py-2 text-right">
                  {r.mean_input_tokens !== null && r.mean_output_tokens !== null
                    ? `${r.mean_input_tokens.toFixed(0)} / ${r.mean_output_tokens.toFixed(0)}`
                    : 'n/a'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

import type { Alarm, SelectorMethod, TriageResult, UsageStatsRow } from './types'

// Relative /api prefix, proxied to the FastAPI backend by Vite in dev
// (see vite.config.ts) so there's nothing to reconfigure for Docker Compose later.
const BASE_URL = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const body = await response.text()
    throw new Error(`${response.status} ${response.statusText}: ${body}`)
  }
  return response.json() as Promise<T>
}

export function getAlarms(): Promise<Alarm[]> {
  return request<Alarm[]>('/alarms')
}

export function runTriage(
  alarmId: number,
  method: SelectorMethod,
  budget: number,
): Promise<TriageResult> {
  return request<TriageResult>('/triage', {
    method: 'POST',
    body: JSON.stringify({ alarm_id: alarmId, method, budget }),
  })
}

export function getUsageStats(groupBy: string = 'method,budget'): Promise<UsageStatsRow[]> {
  return request<UsageStatsRow[]>(`/stats/usage?group_by=${encodeURIComponent(groupBy)}`)
}

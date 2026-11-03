import type {
  Alarm,
  Feedback,
  FeedbackOutcome,
  SelectorMethod,
  TriageResult,
  UsageStatsRow,
} from './types'

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

export function submitFeedback(
  runId: number,
  userRole: string,
  outcome: FeedbackOutcome,
  note?: string,
): Promise<Feedback> {
  return request<Feedback>('/feedback', {
    method: 'POST',
    body: JSON.stringify({ run_id: runId, user_role: userRole, outcome, note }),
  })
}

export function listFeedback(): Promise<Feedback[]> {
  return request<Feedback[]>('/feedback')
}

export function updateFeedback(
  feedbackId: number,
  changes: { outcome?: FeedbackOutcome; note?: string },
): Promise<Feedback> {
  return request<Feedback>(`/feedback/${feedbackId}`, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}

export function deleteFeedback(feedbackId: number): Promise<{ deleted: number }> {
  return request<{ deleted: number }>(`/feedback/${feedbackId}`, { method: 'DELETE' })
}

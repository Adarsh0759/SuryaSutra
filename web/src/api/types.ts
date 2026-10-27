// Mirrors the backend contracts exactly (CLAUDE.md §10,
// src/suryasutra/generation/schema.py, src/suryasutra/api/schemas.py).
// Keep these in sync by hand for now — no shared schema generation yet.

export interface Alarm {
  id: number
  site_id: string
  inverter_id: string
  brand: string
  model: string
  code: string
  category: string
  message: string
  raised_at: string
  is_synthetic: boolean
  answerable: boolean | null
}

export interface CitedItem {
  text: string
  citations: string[]
}

export interface Cause {
  cause: string
  confidence: 'high' | 'medium' | 'low'
  citations: string[]
}

export interface Step {
  n: number
  action: string
  expected_result: string
  citations: string[]
}

export interface Usage {
  input_tokens: number
  output_tokens: number
  cost_inr: number
  budget: number
  method: string
}

export interface Source {
  page_start: number
  page_end: number
  text: string
}

export interface AnsweredContract {
  status: 'ANSWERED'
  alarm: { code: string; summary: string }
  safety: CitedItem[]
  likely_causes: Cause[]
  steps: Step[]
  escalate_if: string[]
  uncertainties: string[]
  sources: Record<string, Source>
  usage: Usage
}

export interface InsufficientContract {
  status: 'INSUFFICIENT'
  reason: 'no_evidence' | 'over_budget' | 'citation_validation_failed'
  missing_requirements: string[]
  suggested_next: string
}

export type TriageResult = AnsweredContract | InsufficientContract

export const SELECTOR_METHODS = [
  'requirement_complete',
  'topk',
  'knapsack',
  'mmr',
  'safety_slot',
] as const

export type SelectorMethod = (typeof SELECTOR_METHODS)[number]

// GET /stats/usage — one row per method/budget group (CLAUDE.md §11 screen 4).
// Means are null when a group has no ANSWERED runs with usage yet (nothing to
// average), not zero — a dashboard with no runs should say so, not show fake 0s.
export interface UsageStatsRow {
  method?: string
  budget?: number
  run_count: number
  answered_count: number
  insufficient_count: number
  full_mandatory_coverage_rate: number | null
  mean_cost_inr: number | null
  mean_input_tokens: number | null
  mean_output_tokens: number | null
}

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

import { motion } from 'motion/react'
import { GlassTiltCard } from './GlassTiltCard'

// Pulled directly from eval/results/summary.md (run 20261025T122406Z, N=32 synthetic
// alarms, 5 selectors x 3 budgets) — not estimated, not rounded up. D-11: no number
// appears here that isn't in that file. Selection-level only; see the caveat below.
const TILES = [
  {
    value: '0%',
    label: 'Mandatory evidence silently dropped, any budget',
    detail: 'requirement_complete · vs. 31–100% for the four baselines',
  },
  {
    value: '100%',
    label: 'Abstention precision & recall',
    detail: 'Correctly flags all 8 deliberately-unanswerable alarms',
  },
  {
    value: '75%',
    label: 'Full mandatory coverage rate',
    detail: 'The remaining 25% is the unanswerable alarms, correctly abstained',
  },
]

export function Results() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-24">
      <h2 className="text-3xl font-semibold text-text-1">Results</h2>
      <p className="mt-3 max-w-xl text-sm text-text-2">
        Selection-level only — generation-level numbers need a larger hand-labelled
        eval set than exists yet. Synthetic alarm data (32 alarms). Real, reproducible:{' '}
        <code className="rounded-sm bg-surface-2 px-1 py-0.5 font-mono text-xs">
          python -m eval.run_eval
        </code>
        .
      </p>

      <div className="mt-8 grid gap-5 sm:grid-cols-3">
        {TILES.map((tile, i) => (
          <motion.div
            key={tile.label}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.4, delay: i * 0.08 }}
          >
            <GlassTiltCard>
              <p className="font-mono text-4xl font-semibold text-accent tabular-nums">
                {tile.value}
              </p>
              <p className="mt-2 text-sm font-medium text-text-1">{tile.label}</p>
              <p className="mt-1 text-xs text-text-3">{tile.detail}</p>
            </GlassTiltCard>
          </motion.div>
        ))}
      </div>

      <p className="mt-6 text-xs text-text-3">
        Source: <code className="font-mono">eval/results/summary.md</code>, run
        20261025T122406Z. Cause accuracy, citation precision and real-plant outcomes:{' '}
        <strong className="text-text-2">not yet measured.</strong>
      </p>
    </section>
  )
}

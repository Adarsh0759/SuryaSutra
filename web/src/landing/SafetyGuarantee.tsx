import { Lock, X } from 'lucide-react'
import { motion } from 'motion/react'

// Illustrative, not a replay of a real run trace (that needs GET /runs/{id} to return
// a candidate-by-candidate decision log, which doesn't exist yet — docs/TRD.md §3.2).
// Proportions and the "doesn't fit" case are representative of how
// RequirementCompleteSelector actually behaves (docs/NLP_CONCEPTS.md §5b), not invented.
const SEGMENTS = [
  { label: 'DC isolation (mandatory)', width: 28, kind: 'mandatory' as const },
  { label: 'Cause diagnosis (mandatory)', width: 22, kind: 'mandatory' as const },
  { label: 'Corrective steps (optional)', width: 30, kind: 'optional' as const },
]

export function SafetyGuarantee() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-24">
      <h2 className="text-3xl font-semibold text-text-1">The safety guarantee</h2>
      <p className="mt-3 max-w-xl text-text-2">
        Mandatory evidence fills the budget first and locks in. Optional evidence fills
        what's left. Anything that doesn't fit is dropped — never a mandatory item.
      </p>

      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true, margin: '-120px' }}
        transition={{ duration: 0.3 }}
        className="mt-10 rounded-lg border border-border bg-surface-1/70 p-6 backdrop-blur-md"
      >
        <div className="flex h-10 w-full overflow-hidden rounded-md border border-border bg-surface-2">
          {SEGMENTS.map((seg, i) => (
            <motion.div
              key={seg.label}
              initial={{ width: '0%' }}
              whileInView={{ width: `${seg.width}%` }}
              viewport={{ once: true, margin: '-120px' }}
              transition={{ type: 'spring', stiffness: 420, damping: 32, delay: i * 0.12 }}
              className={`relative flex items-center justify-center border-r border-bg/40 text-xs font-medium ${
                seg.kind === 'mandatory' ? 'bg-accent text-accent-text' : 'bg-interactive text-white'
              }`}
            >
              {seg.kind === 'mandatory' && (
                <motion.span
                  initial={{ scale: 0 }}
                  whileInView={{ scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.4 + i * 0.12 }}
                >
                  <Lock size={12} strokeWidth={2} />
                </motion.span>
              )}
            </motion.div>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-text-2">
          {SEGMENTS.map((seg) => (
            <span key={seg.label} className="flex items-center gap-1.5">
              <span
                className={`h-2 w-2 rounded-full ${seg.kind === 'mandatory' ? 'bg-accent' : 'bg-interactive'}`}
              />
              {seg.label}
            </span>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, x: -8 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: '-120px' }}
          transition={{ delay: 0.7, duration: 0.3 }}
          className="mt-4 flex items-center gap-2 text-xs text-text-3"
        >
          <X size={14} strokeWidth={1.75} className="text-danger" />
          Doesn't fit → dropped, never a mandatory item
        </motion.div>

        <p className="mt-6 text-xs text-text-3">
          812 / 1,000 tokens — illustrative example, not a live run.
        </p>
      </motion.div>
    </section>
  )
}

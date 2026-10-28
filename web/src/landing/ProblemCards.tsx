import { BookOpen, ShieldOff, Siren } from 'lucide-react'
import { motion } from 'motion/react'
import { GlassTiltCard } from './GlassTiltCard'

const CARDS = [
  {
    icon: Siren,
    title: 'Alarms, constantly',
    body: 'A solar plant throws fault codes all day. Each one means a technician searching a 100+ page vendor PDF by hand.',
  },
  {
    icon: BookOpen,
    title: 'Knowledge locked in PDFs',
    body: "What to check first, in what order, with what precautions — it's in the manual, or in someone's memory. Rarely both, rarely fast.",
  },
  {
    icon: ShieldOff,
    title: "Safety can't be skipped",
    body: 'Generic AI answers are uncited and can quietly drop a safety step. At fleet scale, that’s not an acceptable risk.',
  },
]

export function ProblemCards() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-24">
      <motion.h2
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-80px' }}
        transition={{ duration: 0.4 }}
        className="text-3xl font-semibold text-text-1"
      >
        The problem
      </motion.h2>
      <div className="mt-8 grid gap-5 sm:grid-cols-3">
        {CARDS.map(({ icon: Icon, title, body }, i) => (
          <motion.div
            key={title}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.4, delay: i * 0.08 }}
          >
            <GlassTiltCard>
              <Icon size={24} className="text-accent" strokeWidth={1.75} />
              <h3 className="mt-4 text-lg font-semibold text-text-1">{title}</h3>
              <p className="mt-2 text-sm text-text-2">{body}</p>
            </GlassTiltCard>
          </motion.div>
        ))}
      </div>
    </section>
  )
}

import { ArrowRight, FileCheck2, ShieldAlert, Siren } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { Link } from 'react-router-dom'

const FLOAT_CARDS = [
  { icon: Siren, label: 'Fault 370 raised', depth: 0, x: '-6%', y: '4%' },
  { icon: ShieldAlert, label: 'Safety evidence locked', depth: 40, x: '58%', y: '-2%' },
  { icon: FileCheck2, label: 'Cited · p.103', depth: 80, x: '30%', y: '46%' },
]

export function Hero() {
  const reduceMotion = useReducedMotion()

  return (
    <section className="relative overflow-hidden px-4 pt-20 pb-28 sm:pt-28">
      <div
        aria-hidden
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            'linear-gradient(var(--text-1) 1px, transparent 1px), linear-gradient(90deg, var(--text-1) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      <div className="relative mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2">
        <div>
          <motion.h1
            initial={reduceMotion ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="font-serif text-5xl leading-[1.05] text-text-1 sm:text-6xl"
          >
            From alarm to <span className="text-accent italic">safe action</span>, with the
            source on every step.
          </motion.h1>
          <motion.p
            initial={reduceMotion ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.08 }}
            className="mt-5 max-w-md text-lg text-text-2"
          >
            SuryaSutra retrieves cited, step-by-step triage plans from your plant's own
            manuals — and refuses to guess when the evidence isn't there.
          </motion.p>
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.16 }}
            className="mt-8 flex flex-wrap items-center gap-4"
          >
            <Link
              to="/app"
              className="group flex items-center gap-2 rounded-full bg-accent px-6 py-3 font-medium text-accent-text transition-transform hover:brightness-105 active:scale-[0.97]"
            >
              Try the demo
              <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
            </Link>
            <a
              href="#how-it-works"
              className="text-sm font-medium text-text-2 underline decoration-border underline-offset-4 hover:text-text-1"
            >
              How it works
            </a>
          </motion.div>
        </div>

        {/* Layered glass cards at staggered depth/offset — the "spatial" hero visual.
            A hand-drawn SVG illustration (per DESIGN_BRIEF.md) is a later pass; this
            is a real, working substitute using the same glass+depth language used
            throughout the rest of the page. */}
        <div
          className="relative hidden h-96 lg:block"
          style={{ perspective: 1200 }}
          aria-hidden
        >
          {FLOAT_CARDS.map(({ icon: Icon, label, depth, x, y }, i) => (
            <motion.div
              key={label}
              initial={reduceMotion ? false : { opacity: 0, y: 24 }}
              animate={{
                opacity: 1,
                y: reduceMotion ? 0 : [0, -10, 0],
              }}
              transition={{
                opacity: { duration: 0.5, delay: 0.2 + i * 0.1 },
                y: reduceMotion
                  ? { duration: 0 }
                  : { duration: 4 + i, repeat: Infinity, ease: 'easeInOut', delay: i * 0.4 },
              }}
              style={{
                position: 'absolute',
                left: x,
                top: y,
                transform: `translateZ(${depth}px)`,
                transformStyle: 'preserve-3d',
              }}
              className="flex items-center gap-2 rounded-lg border border-border bg-surface-1/70 px-4 py-3 text-sm text-text-1 shadow-[var(--shadow-overlay)] backdrop-blur-md"
            >
              <Icon size={16} className="text-accent" strokeWidth={1.75} />
              {label}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

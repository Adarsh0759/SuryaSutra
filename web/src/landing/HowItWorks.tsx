import { motion, useScroll, useSpring } from 'motion/react'
import { useRef } from 'react'

// The real pipeline (docs/NLP_CONCEPTS.md §2) — not a marketing simplification.
const STEPS = [
  { title: 'Ingest & chunk', body: 'The manual is parsed and split into ~300-token chunks, each small enough to cite, big enough to make sense alone.' },
  { title: 'Tag requirements', body: 'Each chunk is tagged with which safety/cause/procedure requirements it actually covers, from config/requirements.yaml.' },
  { title: 'Alarm fires → retrieve', body: 'BM25 (exact terms) and dense embeddings (meaning) both search the manual; results are fused by rank, not raw score.' },
  { title: 'Budgeted selection', body: 'Every mandatory requirement must be covered by a selected chunk before anything else — the hard constraint this project is about.' },
  { title: 'Abstain if infeasible', body: "If mandatory evidence doesn't exist or won't fit the budget, the system refuses to answer and says exactly what's missing." },
  { title: 'Generate the cited answer', body: 'An LLM turns the selected, already-vetted evidence into a structured, cited safety plan — it never decides what counts as evidence.' },
  { title: 'Validate every citation', body: 'Every safety item and step must cite a chunk that was actually selected. An uncited claim fails validation and gets retried, or abstains.' },
]

export function HowItWorks() {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 0.8', 'end 0.4'] })
  const lineScale = useSpring(scrollYProgress, { stiffness: 120, damping: 24 })

  return (
    <section id="how-it-works" ref={ref} className="mx-auto max-w-3xl px-4 py-24">
      <h2 className="text-3xl font-semibold text-text-1">How it works</h2>
      <div className="relative mt-10 pl-8">
        <div className="absolute top-0 bottom-0 left-2.5 w-px bg-border" />
        <motion.div
          style={{ scaleY: lineScale }}
          className="absolute top-0 bottom-0 left-2.5 w-px origin-top bg-accent"
        />
        <ol className="flex flex-col gap-10">
          {STEPS.map((step, i) => (
            <motion.li
              key={step.title}
              initial={{ opacity: 0, x: -12 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: '-100px' }}
              transition={{ duration: 0.35 }}
              className="relative"
            >
              <span className="absolute top-0.5 -left-[34px] flex h-5 w-5 items-center justify-center rounded-full border border-accent bg-bg font-mono text-[10px] text-accent">
                {i + 1}
              </span>
              <h3 className="font-semibold text-text-1">{step.title}</h3>
              <p className="mt-1 text-sm text-text-2">{step.body}</p>
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  )
}

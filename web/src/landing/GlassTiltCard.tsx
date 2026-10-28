import { motion, useMotionTemplate, useMotionValue, useReducedMotion, useSpring } from 'motion/react'
import type { ReactNode } from 'react'

interface GlassTiltCardProps {
  children: ReactNode
  className?: string
}

/** Frosted-glass panel that tilts in 3D toward the cursor (docs/DESIGN_BRIEF.md's
 * "spatial" direction: glassmorphism + perspective tilt). Reduced-motion users get the
 * glass styling without the tilt — DESIGN_BRIEF.md §7.2 rule 4. */
export function GlassTiltCard({ children, className = '' }: GlassTiltCardProps) {
  const reduceMotion = useReducedMotion()
  const rotateX = useSpring(0, { stiffness: 220, damping: 20 })
  const rotateY = useSpring(0, { stiffness: 220, damping: 20 })
  const glowX = useMotionValue(50)
  const glowY = useMotionValue(50)
  const glow = useMotionTemplate`radial-gradient(240px circle at ${glowX}% ${glowY}%, color-mix(in srgb, var(--lime) 12%, transparent), transparent 70%)`

  const handleMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (reduceMotion) return
    const rect = e.currentTarget.getBoundingClientRect()
    const px = (e.clientX - rect.left) / rect.width
    const py = (e.clientY - rect.top) / rect.height
    rotateY.set((px - 0.5) * 12)
    rotateX.set((0.5 - py) * 12)
    glowX.set(px * 100)
    glowY.set(py * 100)
  }

  const handleLeave = () => {
    rotateX.set(0)
    rotateY.set(0)
  }

  return (
    <div style={{ perspective: 1000 }} className={className}>
      <motion.div
        onMouseMove={handleMove}
        onMouseLeave={handleLeave}
        style={{ rotateX, rotateY, transformStyle: 'preserve-3d' }}
        className="relative h-full overflow-hidden rounded-lg border border-border bg-surface-1/60 p-6 shadow-[var(--shadow-overlay)] backdrop-blur-md"
      >
        <motion.div
          aria-hidden
          style={{ backgroundImage: glow }}
          className="pointer-events-none absolute inset-0"
        />
        <div className="relative">{children}</div>
      </motion.div>
    </div>
  )
}

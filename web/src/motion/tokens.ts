// Motion tokens (docs/DESIGN_BRIEF.md §7.1).

export const dur = {
  instant: 0.08,
  fast: 0.15,
  base: 0.22,
  slow: 0.36,
} as const

export const ease = {
  standard: [0.2, 0, 0, 1] as const,
  exit: [0.4, 0, 1, 1] as const,
  emphasized: [0.3, 0, 0, 1] as const,
}

export const spring = {
  snappy: { type: 'spring', stiffness: 420, damping: 32 } as const,
  soft: { type: 'spring', stiffness: 220, damping: 26 } as const,
}

export const stagger = {
  list: 0.04,
}

interface CitationChipsProps {
  ids: string[]
  onOpen: (id: string) => void
}

export function CitationChips({ ids, onOpen }: CitationChipsProps) {
  if (ids.length === 0) return null
  return (
    <span className="ml-1 inline-flex gap-1">
      {ids.map((id) => (
        <button
          key={id}
          type="button"
          onClick={() => onOpen(id)}
          className="rounded-sm border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-xs text-text-2 transition-colors hover:border-interactive hover:text-interactive"
        >
          [{id}]
        </button>
      ))}
    </span>
  )
}

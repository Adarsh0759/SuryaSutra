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
          className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-xs text-amber-800 hover:bg-amber-200 dark:bg-amber-900/50 dark:text-amber-300 dark:hover:bg-amber-900/70"
        >
          {id}
        </button>
      ))}
    </span>
  )
}

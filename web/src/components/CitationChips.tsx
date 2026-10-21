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
          className="rounded bg-gray-200 px-1.5 py-0.5 font-mono text-xs text-gray-700 hover:bg-gray-300"
        >
          {id}
        </button>
      ))}
    </span>
  )
}

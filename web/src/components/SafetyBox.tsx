import { AlertTriangle } from 'lucide-react'
import { CitationChips } from './CitationChips'

interface SafetyBoxProps {
  items: { text: string; citations: string[] }[]
  onOpenCitation: (id: string) => void
}

/** Always rendered first, never collapsible (docs/DESIGN_BRIEF.md §5, §7.2 rule 2). */
export function SafetyBox({ items, onOpenCitation }: SafetyBoxProps) {
  return (
    <div className="rounded-md border-l-2 border-danger bg-surface-2 p-4">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold tracking-wide text-danger uppercase">
        <AlertTriangle size={16} strokeWidth={1.75} />
        Safety first
      </div>
      <ul className="space-y-1.5 text-sm text-text-1">
        {items.map((item, i) => (
          <li key={i}>
            {item.text}
            <CitationChips ids={item.citations} onOpen={onOpenCitation} />
          </li>
        ))}
      </ul>
    </div>
  )
}

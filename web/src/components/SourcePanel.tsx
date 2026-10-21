import type { Source } from '../api/types'

interface SourcePanelProps {
  citationId: string
  source: Source
  onClose: () => void
}

export function SourcePanel({ citationId, source, onClose }: SourcePanelProps) {
  const pageLabel =
    source.page_start === source.page_end
      ? `page ${source.page_start}`
      : `pages ${source.page_start}-${source.page_end}`

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[80vh] w-full max-w-lg overflow-y-auto rounded bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-semibold text-gray-900">
            Source [{citationId}] — {pageLabel}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <p className="mt-2 whitespace-pre-wrap text-sm text-gray-700">{source.text}</p>
      </div>
    </div>
  )
}

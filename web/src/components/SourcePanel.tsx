import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { motion } from 'motion/react'
import type { Source } from '../api/types'
import { spring } from '../motion/tokens'

interface SourcePanelProps {
  citationId: string
  source: Source
  onClose: () => void
}

/** Desktop: right-side panel. Mobile: same component, full-width via responsive
 * classes (a true bottom sheet is a later iteration — see docs/APP_FLOW.md §3.5). */
export function SourcePanel({ citationId, source, onClose }: SourcePanelProps) {
  const pageLabel =
    source.page_start === source.page_end
      ? `page ${source.page_start}`
      : `pages ${source.page_start}-${source.page_end}`

  return (
    <Dialog.Root open onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal forceMount>
        <Dialog.Overlay asChild forceMount>
          <motion.div
            className="fixed inset-0 z-50 bg-midnight/50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          />
        </Dialog.Overlay>
        <Dialog.Content asChild forceMount aria-describedby={undefined}>
          <motion.div
            className="fixed top-0 right-0 z-50 h-full w-full max-w-md overflow-y-auto border-l border-border bg-surface-1 p-5 shadow-(--shadow-overlay)"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={spring.soft}
          >
            <div className="flex items-center justify-between gap-2">
              <Dialog.Title className="font-mono text-sm text-text-1">
                [{citationId}] · {pageLabel}
              </Dialog.Title>
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="text-text-3 transition-colors hover:text-text-1"
                  aria-label="Close"
                >
                  <X size={18} strokeWidth={1.75} />
                </button>
              </Dialog.Close>
            </div>
            <p className="mt-3 text-sm whitespace-pre-wrap text-text-2">{source.text}</p>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

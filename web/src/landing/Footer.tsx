import { Code2 } from 'lucide-react'

export function Footer() {
  return (
    <footer className="border-t border-border px-4 py-10">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 text-sm text-text-3">
        <p>SuryaSutra — a research prototype, not a finished product.</p>
        <a
          href="https://github.com/Adarsh0759/SuryaSutra"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 text-text-2 hover:text-text-1"
        >
          <Code2 size={16} strokeWidth={1.75} />
          Source on GitHub
        </a>
      </div>
    </footer>
  )
}

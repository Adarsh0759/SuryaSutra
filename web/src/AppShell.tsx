import * as Tabs from '@radix-ui/react-tabs'
import { Moon, Sun, SunMedium } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AlarmQueue } from './pages/AlarmQueue'
import { CompareView } from './pages/CompareView'
import { Dashboard } from './pages/Dashboard'
import { TriageView } from './pages/TriageView'
import { useTheme } from './useTheme'

type Tab = 'queue' | 'dashboard'

export function AppShell() {
  const [tab, setTab] = useState<Tab>('queue')
  const [selectedAlarmId, setSelectedAlarmId] = useState<number | null>(null)
  const [compareMode, setCompareMode] = useState(false)
  const [theme, toggleTheme] = useTheme()

  return (
    <div className="min-h-svh bg-bg">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 p-4">
        <header className="flex items-start justify-between gap-4 border-b border-border pb-4">
          <Link to="/" className="group">
            <h1 className="flex items-center gap-2 text-2xl font-bold text-text-1">
              <SunMedium className="text-accent" size={26} strokeWidth={2} />
              SuryaSutra
            </h1>
            <p className="text-sm text-text-2 transition-colors group-hover:text-interactive">
              From alarm to safe action, with the source on every step.
            </p>
          </Link>
          <button
            type="button"
            onClick={toggleTheme}
            className="flex shrink-0 items-center gap-1.5 rounded-full border border-border bg-surface-2 px-3 py-1.5 text-sm font-medium text-text-1 transition-colors hover:border-interactive"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <>
                <Sun size={16} strokeWidth={1.75} /> Field mode
              </>
            ) : (
              <>
                <Moon size={16} strokeWidth={1.75} /> Dark
              </>
            )}
          </button>
        </header>

        <Tabs.Root value={tab} onValueChange={(v) => setTab(v as Tab)}>
          <Tabs.List className="flex gap-2 border-b border-border">
            {(['queue', 'dashboard'] as const).map((t) => (
              <Tabs.Trigger
                key={t}
                value={t}
                className="px-3 py-2 text-sm font-medium text-text-2 transition-colors hover:text-text-1 data-[state=active]:border-b-2 data-[state=active]:border-accent data-[state=active]:text-text-1"
              >
                {t === 'queue' ? 'Alarm queue' : 'Dashboard'}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
        </Tabs.Root>

        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22 }}
          >
            {tab === 'queue' ? (
              <div className="flex flex-col gap-4">
                <AlarmQueue selectedAlarmId={selectedAlarmId} onSelectAlarm={setSelectedAlarmId} />

                {selectedAlarmId !== null && (
                  <>
                    <label className="flex w-fit items-center gap-2 text-sm text-text-2">
                      <input
                        type="checkbox"
                        checked={compareMode}
                        onChange={(e) => setCompareMode(e.target.checked)}
                      />
                      Compare mode
                    </label>
                    {compareMode ? (
                      <CompareView alarmId={selectedAlarmId} />
                    ) : (
                      <TriageView alarmId={selectedAlarmId} />
                    )}
                  </>
                )}
              </div>
            ) : (
              <Dashboard />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { AlarmQueue } from './pages/AlarmQueue'
import { CompareView } from './pages/CompareView'
import { Dashboard } from './pages/Dashboard'
import { TriageView } from './pages/TriageView'
import { useTheme } from './useTheme'

type Tab = 'queue' | 'dashboard'

function App() {
  const [tab, setTab] = useState<Tab>('queue')
  const [selectedAlarmId, setSelectedAlarmId] = useState<number | null>(null)
  const [compareMode, setCompareMode] = useState(false)
  const [theme, toggleTheme] = useTheme()

  return (
    <div className="min-h-svh bg-amber-50 dark:bg-slate-900">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 p-4">
        <header className="flex items-start justify-between gap-4 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 p-4 shadow-sm dark:from-amber-600 dark:to-orange-700">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
              <span aria-hidden>☀️</span> SuryaSutra
            </h1>
            <p className="text-sm text-amber-50">
              From alarm to safe action, with the source on every step.
            </p>
          </div>
          <button
            type="button"
            onClick={toggleTheme}
            className="shrink-0 rounded-full border border-white/40 bg-white/20 px-3 py-1.5 text-sm font-medium text-white backdrop-blur hover:bg-white/30"
            aria-label="Toggle dark mode"
          >
            {theme === 'light' ? '🌙 Dark' : '☀️ Light'}
          </button>
        </header>

        <nav className="flex gap-2 border-b border-amber-200 dark:border-slate-700">
          {(['queue', 'dashboard'] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`px-3 py-2 text-sm font-medium ${
                tab === t
                  ? 'border-b-2 border-amber-600 text-amber-700 dark:border-amber-400 dark:text-amber-400'
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              {t === 'queue' ? 'Alarm queue' : 'Dashboard'}
            </button>
          ))}
        </nav>

        {tab === 'queue' ? (
          <>
            <AlarmQueue selectedAlarmId={selectedAlarmId} onSelectAlarm={setSelectedAlarmId} />

            {selectedAlarmId !== null && (
              <>
                <label className="flex w-fit items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
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
          </>
        ) : (
          <Dashboard />
        )}
      </div>
    </div>
  )
}

export default App

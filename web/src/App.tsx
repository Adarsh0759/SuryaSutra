import { useState } from 'react'
import { AlarmQueue } from './pages/AlarmQueue'
import { CompareView } from './pages/CompareView'
import { Dashboard } from './pages/Dashboard'
import { TriageView } from './pages/TriageView'

type Tab = 'queue' | 'dashboard'

function App() {
  const [tab, setTab] = useState<Tab>('queue')
  const [selectedAlarmId, setSelectedAlarmId] = useState<number | null>(null)
  const [compareMode, setCompareMode] = useState(false)

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-4">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">SuryaSutra</h1>
        <p className="text-sm text-gray-500">
          From alarm to safe action, with the source on every step.
        </p>
      </header>

      <nav className="flex gap-2 border-b border-gray-200">
        {(['queue', 'dashboard'] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm font-medium ${
              tab === t
                ? 'border-b-2 border-amber-600 text-amber-700'
                : 'text-gray-500 hover:text-gray-700'
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
              <label className="flex w-fit items-center gap-2 text-sm text-gray-600">
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
  )
}

export default App

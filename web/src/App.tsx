import { useState } from 'react'
import { AlarmQueue } from './pages/AlarmQueue'
import { CompareView } from './pages/CompareView'
import { TriageView } from './pages/TriageView'

function App() {
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
    </div>
  )
}

export default App

import { Route, Routes } from 'react-router-dom'
import { AppShell } from './AppShell'
import { LandingPage } from './landing/LandingPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/app" element={<AppShell />} />
    </Routes>
  )
}

export default App

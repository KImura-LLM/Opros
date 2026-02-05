import { Routes, Route } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { useLocation } from 'react-router-dom'

// Страницы
import HomePage from '@/pages/HomePage'
import SurveyPage from '@/pages/SurveyPage'
import CompletePage from '@/pages/CompletePage'
import ErrorPage from '@/pages/ErrorPage'

function App() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-slate-50">
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<HomePage />} />
          <Route path="/survey" element={<SurveyPage />} />
          <Route path="/complete" element={<CompletePage />} />
          <Route path="/error" element={<ErrorPage />} />
        </Routes>
      </AnimatePresence>
    </div>
  )
}

export default App

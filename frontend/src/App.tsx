import { Routes, Route } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { useLocation } from 'react-router-dom'

// Страницы
import HomePage from '@/pages/HomePage'
import SurveyPage from '@/pages/SurveyPage'
import CompletePage from '@/pages/CompletePage'
import ErrorPage from '@/pages/ErrorPage'
import EditorPage from '@/pages/EditorPage'
import AnalysisEditorPage from '@/pages/AnalysisEditorPage'

function App() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-slate-50">
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<HomePage />} />
          <Route path="/s/:code" element={<HomePage />} />
          <Route path="/survey" element={<SurveyPage />} />
          <Route path="/complete" element={<CompletePage />} />
          <Route path="/error" element={<ErrorPage />} />
          
          {/* Редактор опросника (для админ-панели) */}
          <Route path="/editor/:surveyId" element={<EditorPage />} />
          
          {/* Редактор системного анализа (для админ-панели) */}
          <Route path="/analysis-editor/:surveyId" element={<AnalysisEditorPage />} />
        </Routes>
      </AnimatePresence>
    </div>
  )
}

export default App

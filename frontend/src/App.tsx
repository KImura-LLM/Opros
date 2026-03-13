import { Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useLocation } from 'react-router-dom'

// Страницы
import HomePage from '@/pages/HomePage'
import SurveyPage from '@/pages/SurveyPage'
import CompletePage from '@/pages/CompletePage'
import ErrorPage from '@/pages/ErrorPage'

const EditorPage = lazy(() => import('@/pages/EditorPage'))
const AnalysisEditorPage = lazy(() => import('@/pages/AnalysisEditorPage'))

function App() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-slate-50">
      {/* motion.div с key обеспечивает корректную работу AnimatePresence:
          Routes не поддерживает forwardRef, поэтому оборачиваем в motion.div */}
      <AnimatePresence mode="wait">
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          <Suspense
            fallback={
              <div className="flex min-h-[40vh] items-center justify-center text-slate-500">
                Загрузка...
              </div>
            }
          >
            <Routes location={location}>
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
          </Suspense>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

export default App

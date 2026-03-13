import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import './index.css'

try {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </BrowserRouter>
    </React.StrictMode>,
  )
} catch (e) {
  console.error('App render failed:', e)
  const root = document.getElementById('root')!
  root.textContent = ''
  const errorDiv = document.createElement('div')
  errorDiv.style.cssText = 'color:red; padding: 20px;'
  errorDiv.textContent = 'Ошибка загрузки приложения. Пожалуйста, обновите страницу.'
  root.appendChild(errorDiv)
}

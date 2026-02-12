import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

console.log('App starting...')

try {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </React.StrictMode>,
  )
  console.log('App rendered')
} catch (e) {
  console.error('App render failed:', e)
  document.getElementById('root')!.innerHTML = '<div style="color:red; padding: 20px;">' + String(e) + '</div>'
}

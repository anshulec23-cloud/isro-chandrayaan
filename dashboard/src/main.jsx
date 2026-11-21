import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Pre-seed demo job
if (!localStorage.getItem('lumen_job_id')) {
  localStorage.setItem('lumen_job_id', 'SEED-JOB-TMC-TMC');
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider } from './context/AuthContext'
import { StatusBarProvider } from './context/StatusBarContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <StatusBarProvider>
          <App />
        </StatusBarProvider>
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>,
)

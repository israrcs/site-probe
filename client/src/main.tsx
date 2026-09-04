import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          minHeight: '100vh', background: '#0f172a', color: '#e2e8f0',
          padding: '2rem', fontFamily: 'system-ui, sans-serif',
        }}>
          <h1 style={{ color: '#f87171', fontSize: '1.25rem' }}>
            ⚠ Render error
          </h1>
          <pre style={{
            background: '#1e293b', padding: '1rem', borderRadius: '0.5rem',
            overflow: 'auto', fontSize: '0.8rem', whiteSpace: 'pre-wrap',
            marginTop: '1rem', border: '1px solid #334155',
          }}>
            {this.state.error.message}
            {this.state.error.stack}
          </pre>
          <p style={{ marginTop: '1rem', color: '#94a3b8', fontSize: '0.8rem' }}>
            Check the browser console for details. This usually means a
            component threw during render.
          </p>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
)

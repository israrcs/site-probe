import { Link, Outlet, useLocation } from 'react-router-dom'
import { useTheme } from './ThemeProvider'
import ThemeToggle from './ThemeToggle'

export default function Layout() {
  const { pathname } = useLocation()
  const { theme, toggleTheme } = useTheme()
  const isActive = (p: string) =>
    p === '/' ? pathname === '/' : pathname.startsWith(p)
  return (
    <div className="min-h-screen bg-slate-950">
      <div className="h-0.5 bg-gradient-to-r from-sky-500 via-emerald-500 to-transparent" />
      <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500 to-emerald-500 text-sm font-black text-slate-950 shadow-lg shadow-sky-500/20">
              SP
            </span>
            <span className="text-lg font-bold tracking-tight text-white">
              Site<span className="bg-gradient-to-r from-sky-400 to-emerald-400 bg-clip-text text-transparent">Probe</span>
            </span>
          </Link>
          <nav className="flex items-center gap-1 text-sm">
            <Link
              to="/"
              className={`rounded-lg px-3 py-1.5 transition-colors ${
                isActive('/')
                  ? 'bg-gradient-to-r from-sky-600/30 to-emerald-600/20 text-white ring-1 ring-sky-500/30'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-white'
              }`}
            >
              New scan
            </Link>
            <Link
              to="/runs"
              className={`rounded-lg px-3 py-1.5 transition-colors ${
                isActive('/runs')
                  ? 'bg-gradient-to-r from-sky-600/30 to-emerald-600/20 text-white ring-1 ring-sky-500/30'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-white'
              }`}
            >
              History
            </Link>
          </nav>
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}

import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import NewRunPage from './pages/NewRunPage'
import RunDetailPage from './pages/RunDetailPage'
import RunsListPage from './pages/RunsListPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<NewRunPage />} />
        <Route path="/runs" element={<RunsListPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="*" element={<NewRunPage />} />
      </Route>
    </Routes>
  )
}

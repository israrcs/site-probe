import axios from 'axios'
import type { Run, RunOptions, RunSummary } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({ baseURL: API_BASE })

export const artifactUrl = (runId: string, rel: string) =>
  `${API_BASE}/artifacts/${runId}/${rel}`

export const startRun = (opts: RunOptions) =>
  api.post<{ id: string; status: string }>('/runs', opts).then((r) => r.data)

export const listRuns = () =>
  api.get<RunSummary[]>('/runs').then((r) => r.data)

export const getRun = (id: string) =>
  api.get<Run>(`/runs/${id}`).then((r) => r.data)

export const cancelRun = (id: string) =>
  api.delete(`/runs/${id}`).then((r) => r.data)

export const issuesUrl = (id: string) => `${api.defaults.baseURL}/runs/${id}/issues`
export const reportJsonUrl = (id: string) => `${api.defaults.baseURL}/runs/${id}/report.json`
export const reportHtmlUrl = (id: string) => `${api.defaults.baseURL}/runs/${id}/report.html`
export const reportZipUrl = (id: string) => `${api.defaults.baseURL}/runs/${id}/site-report.zip`

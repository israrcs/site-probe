export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'

export type Category =
  | 'functional'
  | 'console'
  | 'network'
  | 'a11y'
  | 'seo'
  | 'security'
  | 'performance'

export type Viewport = 'desktop' | 'tablet' | 'mobile'

export type RunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

export interface Issue {
  id: string
  run_id: string
  page_url: string
  category: Category
  severity: Severity
  title: string
  description: string
  suggestion: string
  selector?: string | null
  html_snippet?: string | null
  bounding_box?: BoundingBox | null
  screenshot?: Record<string, string>
  viewport?: string | null
  metadata?: Record<string, unknown>
}

export interface PageResult {
  url: string
  status?: number | null
  title?: string | null
  screenshots: Record<string, string>
  console_errors: number
  failed_requests: number
  metrics: Record<string, unknown>
}

export interface Scores {
  overall: number
  grade: string
  categories: Record<string, number>
}

export interface RunOptions {
  url: string
  max_pages: number
  viewports: Viewport[]
  engines: Category[]
  follow_robots: boolean
  delay_ms: number
  timeout_ms: number
  user_agent?: string | null
}

export interface Run {
  id: string
  options: RunOptions
  status: RunStatus
  phase: string
  pages_done: number
  pages_total: number
  current_url?: string | null
  issues: Issue[]
  pages: PageResult[]
  scores: Scores
  error?: string | null
  is_demo?: boolean
  created_at: number
  started_at?: number | null
  finished_at?: number | null
}

export interface RunSummary {
  id: string
  url: string
  status: RunStatus
  phase: string
  pages_done: number
  pages_total: number
  issue_counts: Record<Severity, number>
  total_issues: number
  overall_score?: number | null
  grade?: string | null
  created_at: number
  started_at?: number | null
  finished_at?: number | null
  duration_s?: number | null
  error?: string | null
  is_demo?: boolean
}

export interface ProgressEvent {
  run_id: string
  status: RunStatus
  phase: string
  pages_done: number
  pages_total: number
  current_url?: string | null
  issue_count: number
}

export const ALL_CATEGORIES: Category[] = [
  'functional',
  'console',
  'network',
  'a11y',
  'seo',
  'security',
  'performance',
]

export const ALL_VIEWPORTS: Viewport[] = ['desktop', 'tablet', 'mobile']

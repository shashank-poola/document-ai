import type { JobStatusResponse, PipelineOutput } from '../types'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export async function uploadDocument(file: File): Promise<JobStatusResponse> {
  const form = new FormData()
  form.append('file', file)

  const response = await fetch(`${API_BASE}/api/v1/documents/upload`, {
    method: 'POST',
    body: form,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail ?? `Upload failed (${response.status})`)
  }

  return response.json()
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await fetch(`${API_BASE}/api/v1/documents/${jobId}/status`)
  if (!response.ok) {
    throw new Error(`Status check failed (${response.status})`)
  }
  return response.json()
}

export async function getJobResult(jobId: string): Promise<PipelineOutput> {
  const response = await fetch(`${API_BASE}/api/v1/documents/${jobId}/result`)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail ?? `Result fetch failed (${response.status})`)
  }
  return response.json()
}

export const TERMINAL_STATUSES = new Set(['completed', 'needs_review', 'failed'])

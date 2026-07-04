import { useCallback, useEffect, useRef, useState } from 'react'
import { getJobResult, getJobStatus, TERMINAL_STATUSES, uploadDocument } from './api/client'
import { JobList } from './components/JobList'
import { ResultViewer } from './components/ResultViewer'
import { UploadZone } from './components/UploadZone'
import type { TrackedJob } from './types'
import './App.css'

const POLL_MS = 2000
const UPLOAD_CONCURRENCY = 4

async function mapPool<T, R>(items: T[], limit: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const results: R[] = []
  let index = 0

  async function worker() {
    while (index < items.length) {
      const current = index++
      results[current] = await fn(items[current])
    }
  }

  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker))
  return results
}

function App() {
  const [jobs, setJobs] = useState<TrackedJob[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const jobsRef = useRef(jobs)
  jobsRef.current = jobs

  const updateJob = useCallback((id: string, patch: Partial<TrackedJob>) => {
    setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, ...patch } : j)))
  }, [])

  const handleUpload = useCallback(
    async (files: File[]) => {
      setUploading(true)

      const placeholders: TrackedJob[] = files.map((file) => ({
        id: crypto.randomUUID(),
        file,
        status: 'pending',
        pageCount: 0,
        submitted: false,
      }))

      setJobs((prev) => [...placeholders, ...prev])

      await mapPool(placeholders, UPLOAD_CONCURRENCY, async (placeholder) => {
        try {
          const response = await uploadDocument(placeholder.file)
          updateJob(placeholder.id, {
            id: response.job_id,
            status: response.status,
            pageCount: response.page_count,
            submitted: true,
          })
          setSelectedId((current) =>
            current === placeholder.id ? response.job_id : current ?? response.job_id,
          )
        } catch (err) {
          updateJob(placeholder.id, {
            status: 'failed',
            error: err instanceof Error ? err.message : 'Upload failed',
          })
        }
      })

      setUploading(false)
    },
    [updateJob],
  )

  useEffect(() => {
    const interval = setInterval(async () => {
      const active = jobsRef.current.filter(
        (j) => j.submitted && !TERMINAL_STATUSES.has(j.status),
      )
      if (!active.length) return

      await Promise.all(
        active.map(async (job) => {
          try {
            const status = await getJobStatus(job.id)
            updateJob(job.id, {
              status: status.status,
              pageCount: status.page_count,
              error: status.error_message ?? undefined,
            })

            if (status.status === 'completed' || status.status === 'needs_review') {
              const result = await getJobResult(job.id)
              updateJob(job.id, { result })
            }
          } catch {
            /* retry on next poll */
          }
        }),
      )
    }, POLL_MS)

    return () => clearInterval(interval)
  }, [updateJob])

  const selected = jobs.find((j) => j.id === selectedId) ?? null

  return (
    <div className="page">
      <header className="hero">
        <p className="eyebrow">Document Intelligence</p>
        <h1>Extract structure<br />from any document.</h1>
        <p className="hero-sub">
          Upload invoices, receipts, and purchase orders. Get structured JSON and Markdown — powered by
          PaddleOCR and async workers.
        </p>
      </header>

      <UploadZone onFilesSelected={handleUpload} disabled={uploading} />

      <JobList jobs={jobs} selectedId={selectedId} onSelect={setSelectedId} />

      <ResultViewer job={selected} />

      <footer className="footer">
        <p>API · Redis queue · PaddleOCR · Phase 1–2</p>
      </footer>
    </div>
  )
}

export default App

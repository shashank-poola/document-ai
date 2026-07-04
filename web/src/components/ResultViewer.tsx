import { useState } from 'react'
import type { TrackedJob } from '../types'

interface ResultViewerProps {
  job: TrackedJob | null
}

export function ResultViewer({ job }: ResultViewerProps) {
  const [tab, setTab] = useState<'markdown' | 'json'>('markdown')

  if (!job) {
    return (
      <section className="result-panel empty">
        <p>Select a completed document to view extracted output.</p>
      </section>
    )
  }

  if (job.status === 'failed') {
    return (
      <section className="result-panel error">
        <h3>Processing failed</h3>
        <p>{job.error ?? 'An unknown error occurred.'}</p>
      </section>
    )
  }

  if (!job.result) {
    return (
      <section className="result-panel loading">
        <div className="spinner" />
        <p>Processing <strong>{job.file.name}</strong>…</p>
        <p className="muted">Status: {job.status.replace(/_/g, ' ')}</p>
      </section>
    )
  }

  const segment = job.result.segments[0]
  const jsonPayload = {
    job_id: job.result.job_id,
    filename: job.result.original_filename,
    page_count: job.result.page_count,
    segments: job.result.segments.map((s) => ({
      segment_id: s.segment.segment_id,
      document_type: s.segment.document_type,
      fields: s.extraction.fields,
      confidence: s.validation.overall_confidence,
      needs_review: s.validation.needs_review,
    })),
  }

  return (
    <section className="result-panel">
      <div className="result-header">
        <div>
          <h3>{job.file.name}</h3>
          <p className="muted">
            {segment?.segment.document_type.replace(/_/g, ' ')} ·{' '}
            {job.result.page_count} page{job.result.page_count !== 1 ? 's' : ''} ·{' '}
            {Math.round((segment?.validation.overall_confidence ?? 0) * 100)}% confidence
          </p>
        </div>
        <div className="tabs">
          <button
            type="button"
            className={tab === 'markdown' ? 'active' : ''}
            onClick={() => setTab('markdown')}
          >
            Markdown
          </button>
          <button
            type="button"
            className={tab === 'json' ? 'active' : ''}
            onClick={() => setTab('json')}
          >
            JSON
          </button>
        </div>
      </div>

      <div className="result-body">
        {tab === 'markdown' ? (
          <pre className="markdown-view">{segment?.markdown ?? 'No output generated.'}</pre>
        ) : (
          <pre className="json-view">{JSON.stringify(jsonPayload, null, 2)}</pre>
        )}
      </div>
    </section>
  )
}

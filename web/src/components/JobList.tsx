import type { TrackedJob } from '../types'

interface JobListProps {
  jobs: TrackedJob[]
  selectedId: string | null
  onSelect: (id: string) => void
}

const STATUS_LABEL: Record<string, string> = {
  pending: 'Pending',
  queued: 'Queued',
  preprocessing: 'Preparing',
  ocr: 'Reading',
  boundary_detection: 'Analyzing',
  classification: 'Classifying',
  extraction: 'Extracting',
  validation: 'Validating',
  output: 'Generating',
  completed: 'Done',
  needs_review: 'Review',
  failed: 'Failed',
}

export function JobList({ jobs, selectedId, onSelect }: JobListProps) {
  if (!jobs.length) return null

  const done = jobs.filter((j) => j.status === 'completed' || j.status === 'needs_review').length
  const failed = jobs.filter((j) => j.status === 'failed').length
  const inProgress = jobs.length - done - failed

  return (
    <section className="jobs-section">
      <div className="jobs-header">
        <h2>Processing queue</h2>
        <div className="jobs-stats">
          <span>{jobs.length} total</span>
          <span className="dot" />
          <span>{inProgress} in progress</span>
          <span className="dot" />
          <span>{done} complete</span>
          {failed > 0 && (
            <>
              <span className="dot" />
              <span className="failed-stat">{failed} failed</span>
            </>
          )}
        </div>
      </div>

      <ul className="job-list">
        {jobs.map((job) => (
          <li key={job.id}>
            <button
              type="button"
              className={`job-row${selectedId === job.id ? ' selected' : ''}`}
              onClick={() => onSelect(job.id)}
            >
              <span className="job-name">{job.file.name}</span>
              <span className={`job-badge status-${job.status}`}>
                {STATUS_LABEL[job.status] ?? job.status}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

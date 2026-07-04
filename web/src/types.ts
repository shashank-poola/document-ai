export type JobStatus =
  | 'pending'
  | 'queued'
  | 'preprocessing'
  | 'ocr'
  | 'boundary_detection'
  | 'classification'
  | 'extraction'
  | 'validation'
  | 'output'
  | 'completed'
  | 'failed'
  | 'needs_review'

export interface JobStatusResponse {
  job_id: string
  status: JobStatus
  original_filename: string
  page_count: number
  segment_count: number
  error_stage: string | null
  error_message: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface SegmentOutput {
  segment: {
    segment_id: string
    page_start: number
    page_end: number
    document_type: string
    classification_confidence: number
  }
  extraction: {
    document_type: string
    fields: Record<string, string | null>
    extraction_confidence: number
  }
  validation: {
    overall_confidence: number
    needs_review: boolean
  }
  markdown: string
  json_path: string
  markdown_path: string
}

export interface PipelineOutput {
  job_id: string
  status: JobStatus
  original_filename: string
  page_count: number
  segments: SegmentOutput[]
  completed_at: string
  schema_version: string
}

export interface TrackedJob {
  id: string
  file: File
  status: JobStatus
  pageCount: number
  submitted: boolean
  error?: string
  result?: PipelineOutput
}

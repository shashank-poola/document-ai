import { useCallback, useRef, useState } from 'react'

const ACCEPTED = '.pdf,.png,.jpg,.jpeg,.tiff,.tif,.webp,.docx'

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void
  disabled?: boolean
}

export function UploadZone({ onFilesSelected, disabled }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList?.length || disabled) return
      onFilesSelected(Array.from(fileList))
    },
    [disabled, onFilesSelected],
  )

  return (
    <div
      className={`upload-card${dragging ? ' dragging' : ''}${disabled ? ' disabled' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        if (!disabled) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        handleFiles(e.dataTransfer.files)
      }}
    >
      <div className="upload-icons" aria-hidden="true">
        <svg viewBox="0 0 48 56" className="doc-icon doc-back">
          <rect x="4" y="8" width="36" height="44" rx="4" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M14 24h20M14 32h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <svg viewBox="0 0 48 56" className="doc-icon doc-mid">
          <rect x="6" y="4" width="36" height="44" rx="4" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <circle cx="24" cy="26" r="8" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M18 38l4-5 3 3 5-7 4 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <svg viewBox="0 0 48 56" className="doc-icon doc-front">
          <rect x="8" y="0" width="36" height="44" rx="4" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M20 18l6 6-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      <p className="upload-title">
        Drag &amp; drop <span className="accent">PDFs</span>, <span className="accent">images</span>, or{' '}
        <span className="accent">DOCX</span>
      </p>
      <p className="upload-subtitle">
        or{' '}
        <button
          type="button"
          className="link-btn"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          browse files
        </button>{' '}
        on your computer
      </p>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        multiple
        hidden
        onChange={(e) => handleFiles(e.target.files)}
      />

      <button
        type="button"
        className="upload-btn"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        Upload
      </button>
    </div>
  )
}

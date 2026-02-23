import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import { evidenceApi, uploadToS3 } from '@/services/api';
import type { ArtefactType } from '@/types';

interface Props {
  testCaseId?: string;
  testPlanId?: string;
  artefactType: ArtefactType;
  onUploaded?: () => void;
  maxSizeMb?: number;
}

interface UploadState {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'registering' | 'done' | 'error';
  error?: string;
}

export function EvidenceUploader({
  testCaseId, testPlanId, artefactType,
  onUploaded, maxSizeMb = 25
}: Props) {
  const [uploads, setUploads] = useState<UploadState[]>([]);

  const updateUpload = (idx: number, patch: Partial<UploadState>) => {
    setUploads((prev) => prev.map((u, i) => (i === idx ? { ...u, ...patch } : u)));
  };

  const processFile = async (file: File, idx: number) => {
    try {
      updateUpload(idx, { status: 'uploading', progress: 0 });

      // Step 1: Get pre-signed URL
      const presigned = await evidenceApi.getPresignedUpload({
        test_case_id: testCaseId,
        test_plan_id: testPlanId,
        artefact_type: artefactType,
        filename: file.name,
        content_type: file.type || 'application/octet-stream',
        file_size_bytes: file.size,
      });

      // Step 2: Upload directly to S3
      await uploadToS3(presigned, file, (pct) => updateUpload(idx, { progress: pct }));

      // Step 3: Register evidence in UTAP
      updateUpload(idx, { status: 'registering', progress: 100 });
      await evidenceApi.register({
        test_case_id: testCaseId,
        test_plan_id: testPlanId,
        artefact_type: artefactType,
        original_filename: file.name,
        s3_object_key: presigned.s3_object_key,
        s3_bucket: presigned.s3_bucket,
        file_size_bytes: file.size,
        content_type: file.type || 'application/octet-stream',
      });

      updateUpload(idx, { status: 'done' });
      onUploaded?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      updateUpload(idx, { status: 'error', error: msg });
    }
  };

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const startIdx = uploads.length;
      const newUploads = acceptedFiles.map((file) => ({
        file,
        progress: 0,
        status: 'pending' as const,
      }));
      setUploads((prev) => [...prev, ...newUploads]);
      acceptedFiles.forEach((file, i) => processFile(file, startIdx + i));
    },
    [uploads.length]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxSize: maxSizeMb * 1024 * 1024,
    multiple: true,
  });

  const clearDone = () => setUploads((prev) => prev.filter((u) => u.status !== 'done'));

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={clsx(
          'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
        )}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto text-gray-400 mb-2" size={24} />
        <p className="text-sm text-gray-600">
          {isDragActive ? 'Drop files here...' : 'Drag & drop files, or click to select'}
        </p>
        <p className="text-xs text-gray-400 mt-1">Max {maxSizeMb} MB per file</p>
      </div>

      {uploads.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-600">Uploads</span>
            <button onClick={clearDone} className="text-xs text-blue-600 hover:underline">
              Clear completed
            </button>
          </div>
          {uploads.map((u, i) => (
            <div key={i} className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg p-3">
              <div className="shrink-0">
                {u.status === 'done' && <CheckCircle size={16} className="text-green-500" />}
                {u.status === 'error' && <AlertCircle size={16} className="text-red-500" />}
                {(u.status === 'uploading' || u.status === 'registering' || u.status === 'pending') && (
                  <Loader2 size={16} className="text-blue-500 animate-spin" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{u.file.name}</div>
                <div className="text-xs text-gray-500">
                  {(u.file.size / 1024 / 1024).toFixed(2)} MB
                  {u.status === 'uploading' && ` — ${u.progress}%`}
                  {u.status === 'registering' && ' — Registering...'}
                  {u.status === 'done' && ' — Complete'}
                  {u.status === 'error' && ` — Error: ${u.error}`}
                </div>
                {u.status === 'uploading' && (
                  <div className="mt-1 h-1 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: `${u.progress}%` }}
                    />
                  </div>
                )}
              </div>
              <button
                onClick={() => setUploads((prev) => prev.filter((_, idx) => idx !== i))}
                className="shrink-0 text-gray-400 hover:text-gray-600"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

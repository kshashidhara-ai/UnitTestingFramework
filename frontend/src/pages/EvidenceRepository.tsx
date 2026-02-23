import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Download, Archive } from 'lucide-react';
import { evidenceApi } from '@/services/api';
import type { ArtefactType } from '@/types';

const ARTEFACT_TYPE_OPTIONS: ArtefactType[] = [
  'SNOWFLAKE_QUERY_RESULT', 'SNOWFLAKE_SCREENSHOT', 'SNOWFLAKE_EXPLAIN_PLAN', 'SNOWFLAKE_RECONCILIATION',
  'IICS_ACTIVITY_LOG', 'IICS_SESSION_LOG', 'IICS_MONITOR_SCREENSHOT', 'IICS_REJECTION_FILE',
  'SCREENSHOT', 'CSV_EXPORT', 'PDF_DOCUMENT', 'LOG_FILE', 'OTHER',
];

export function EvidenceRepository() {
  const [artefactType, setArtefactType] = useState<ArtefactType | ''>('');
  const [uploadedBy, setUploadedBy] = useState('');
  const [queryId, setQueryId] = useState('');
  const [page, setPage] = useState(1);

  const { data: evidence, isLoading } = useQuery({
    queryKey: ['evidence-all', artefactType, uploadedBy, queryId, page],
    queryFn: () => evidenceApi.list({
      artefact_type: artefactType || undefined,
      uploaded_by: uploadedBy || undefined,
      query_id: queryId || undefined,
      page,
      page_size: 25,
    }),
  });

  const handleDownload = async (id: string) => {
    const { download_url } = await evidenceApi.getDownloadUrl(id);
    window.open(download_url, '_blank');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Evidence Repository</h1>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Archive size={16} />
          <span>All uploaded artefacts</span>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by Query ID / Run ID..."
              value={queryId}
              onChange={(e) => setQueryId(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm"
            />
          </div>
          <select
            value={artefactType}
            onChange={(e) => setArtefactType(e.target.value as ArtefactType | '')}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Types</option>
            {ARTEFACT_TYPE_OPTIONS.map((t) => (
              <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Filter by uploader email..."
            value={uploadedBy}
            onChange={(e) => setUploadedBy(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Filename</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Type</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Size</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Uploaded By</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Date</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Hold</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {evidence?.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3">
                    <div className="font-medium text-gray-800 truncate max-w-xs">
                      {e.original_filename || e.s3_object_key.split('/').pop()}
                    </div>
                    {e.description && (
                      <div className="text-xs text-gray-400 mt-0.5 truncate">{e.description}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                      {e.artefact_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {e.file_size_bytes ? `${(e.file_size_bytes / 1024).toFixed(0)} KB` : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{e.uploaded_by}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {new Date(e.uploaded_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    {e.is_legal_hold && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
                        Legal Hold
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDownload(e.id)}
                      className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                    >
                      <Download size={12} />
                      Download
                    </button>
                  </td>
                </tr>
              ))}
              {(!evidence || evidence.length === 0) && (
                <tr>
                  <td colSpan={7} className="px-5 py-10 text-center text-gray-400 text-sm">
                    No evidence artefacts found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {/* Pagination */}
          <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100">
            <span className="text-xs text-gray-500">
              Page {page}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!evidence || evidence.length < 25}
                className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

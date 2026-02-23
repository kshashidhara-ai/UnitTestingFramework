import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Save, Clock } from 'lucide-react';
import { testCasesApi, evidenceApi } from '@/services/api';
import { EvidenceUploader } from '@/components/evidence/EvidenceUploader';
import { StatusBadge } from '@/components/common/StatusBadge';
import type { TestCase } from '@/types';

const ARTEFACT_TYPES_SNOWFLAKE = [
  'SNOWFLAKE_QUERY_RESULT', 'SNOWFLAKE_SCREENSHOT',
  'SNOWFLAKE_EXPLAIN_PLAN', 'SNOWFLAKE_RECONCILIATION',
];
const ARTEFACT_TYPES_IICS = [
  'IICS_ACTIVITY_LOG', 'IICS_SESSION_LOG',
  'IICS_MONITOR_SCREENSHOT', 'IICS_REJECTION_FILE',
];
const ARTEFACT_TYPES_GENERIC = ['SCREENSHOT', 'CSV_EXPORT', 'PDF_DOCUMENT', 'LOG_FILE', 'OTHER'];

export function TestCaseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: tc, isLoading } = useQuery({
    queryKey: ['test-case', id],
    queryFn: () => testCasesApi.get(id!),
    enabled: !!id,
  });

  const { data: evidence } = useQuery({
    queryKey: ['evidence', id],
    queryFn: () => evidenceApi.list({ test_case_id: id }),
    enabled: !!id,
  });

  const [form, setForm] = useState<Partial<TestCase>>({});
  const [selectedArtefactType, setSelectedArtefactType] = useState('SNOWFLAKE_QUERY_RESULT');
  const [autosaveLabel, setAutosaveLabel] = useState('');

  const updateMutation = useMutation({
    mutationFn: (data: Partial<TestCase>) => testCasesApi.update(id!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['test-case', id] });
      setAutosaveLabel('Saved');
      setTimeout(() => setAutosaveLabel(''), 2000);
    },
  });

  const handleChange = (field: keyof TestCase, value: unknown) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    if (Object.keys(form).length === 0) return;
    updateMutation.mutate(form);
    setForm({});
  };

  // Autosave on blur
  const handleBlur = () => {
    if (Object.keys(form).length > 0) {
      handleSave();
    }
  };

  if (isLoading) return (
    <div className="flex items-center justify-center h-48">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  );
  if (!tc) return <div className="text-gray-500">Test case not found.</div>;

  const val = (field: keyof TestCase) =>
    (form[field] !== undefined ? form[field] : tc[field]) as string ?? '';

  const artefactTypes = [
    ...(tc.component === 'SNOWFLAKE' || tc.component === 'BOTH' ? ARTEFACT_TYPES_SNOWFLAKE : []),
    ...(tc.component === 'IICS' || tc.component === 'BOTH' ? ARTEFACT_TYPES_IICS : []),
    ...ARTEFACT_TYPES_GENERIC,
  ];

  return (
    <div className="max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-700">
            <ArrowLeft size={20} />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-gray-500">{tc.testcase_id}</span>
              <StatusBadge status={tc.status} type="test_case" size="md" />
              {tc.is_template && (
                <span className="text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full">
                  Template: {tc.template_name}
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-gray-900 mt-0.5 line-clamp-1">{tc.objective}</h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {autosaveLabel && (
            <span className="flex items-center gap-1 text-xs text-green-600">
              <Clock size={12} /> {autosaveLabel}
            </span>
          )}
          {Object.keys(form).length > 0 && (
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
            >
              <Save size={14} />
              Save
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Test Definition */}
        <div className="lg:col-span-2 space-y-4">
          {/* Status Selector */}
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Execution Status</h2>
            <div className="flex flex-wrap gap-2">
              {['NOT_RUN', 'IN_PROGRESS', 'PASS', 'FAIL', 'BLOCKED', 'WAIVED'].map((s) => (
                <button
                  key={s}
                  onClick={() => handleChange('status', s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    val('status') === s
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-blue-400'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>

            {(val('status') === 'FAIL') && (
              <div className="mt-3">
                <label className="text-xs font-medium text-gray-600 block mb-1">Defect Reference *</label>
                <input
                  type="text"
                  value={val('defect_reference')}
                  onChange={(e) => handleChange('defect_reference', e.target.value)}
                  onBlur={handleBlur}
                  placeholder="JIRA-1234"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            )}

            {val('status') === 'WAIVED' && (
              <div className="mt-3">
                <label className="text-xs font-medium text-gray-600 block mb-1">Waiver Reason *</label>
                <textarea
                  value={val('waiver_reason')}
                  onChange={(e) => handleChange('waiver_reason', e.target.value)}
                  onBlur={handleBlur}
                  rows={2}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none"
                />
              </div>
            )}
          </div>

          {/* Test Definition */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-gray-700">Test Definition</h2>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Objective</label>
              <textarea
                value={val('objective')}
                onChange={(e) => handleChange('objective', e.target.value)}
                onBlur={handleBlur}
                rows={2}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Preconditions</label>
              <textarea
                value={val('preconditions')}
                onChange={(e) => handleChange('preconditions', e.target.value)}
                onBlur={handleBlur}
                rows={2}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none font-mono"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Test Steps</label>
              <textarea
                value={val('test_steps')}
                onChange={(e) => handleChange('test_steps', e.target.value)}
                onBlur={handleBlur}
                rows={5}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none font-mono"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Expected Result</label>
              <textarea
                value={val('expected_result')}
                onChange={(e) => handleChange('expected_result', e.target.value)}
                onBlur={handleBlur}
                rows={2}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Actual Result</label>
              <textarea
                value={val('actual_result')}
                onChange={(e) => handleChange('actual_result', e.target.value)}
                onBlur={handleBlur}
                rows={3}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none"
                placeholder="Document the actual outcome here..."
              />
            </div>
          </div>

          {/* Snowflake Fields */}
          {(tc.component === 'SNOWFLAKE' || tc.component === 'BOTH') && (
            <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <span className="w-2 h-2 bg-cyan-500 rounded-full" />
                Snowflake Evidence
              </h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Query ID(s)</label>
                  <input
                    type="text"
                    placeholder="01abc123-... (comma separated)"
                    value={(tc.snowflake_query_ids ?? []).join(', ')}
                    onChange={(e) => handleChange('snowflake_query_ids', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
                    onBlur={handleBlur}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Warehouse</label>
                  <input
                    type="text"
                    value={val('snowflake_warehouse')}
                    onChange={(e) => handleChange('snowflake_warehouse', e.target.value)}
                    onBlur={handleBlur}
                    placeholder="COMPUTE_WH"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div className="col-span-2">
                  <label className="text-xs font-medium text-gray-600 block mb-1">Database.Schema.Object</label>
                  <input
                    type="text"
                    value={val('snowflake_database_schema_object')}
                    onChange={(e) => handleChange('snowflake_database_schema_object', e.target.value)}
                    onBlur={handleBlur}
                    placeholder="SALES_DWH.FACTS.FACT_SALES"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Rows Produced</label>
                  <input
                    type="text"
                    value={val('snowflake_rows_produced')}
                    onChange={(e) => handleChange('snowflake_rows_produced', e.target.value)}
                    onBlur={handleBlur}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Duration (ms)</label>
                  <input
                    type="text"
                    value={val('snowflake_execution_duration_ms')}
                    onChange={(e) => handleChange('snowflake_execution_duration_ms', e.target.value)}
                    onBlur={handleBlur}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div className="col-span-2">
                  <label className="text-xs font-medium text-gray-600 block mb-1">SQL Executed</label>
                  <textarea
                    value={val('sql_executed')}
                    onChange={(e) => handleChange('sql_executed', e.target.value)}
                    onBlur={handleBlur}
                    rows={5}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono resize-none"
                    placeholder="SELECT ..."
                  />
                </div>
              </div>
            </div>
          )}

          {/* IICS Fields */}
          {(tc.component === 'IICS' || tc.component === 'BOTH') && (
            <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <span className="w-2 h-2 bg-indigo-500 rounded-full" />
                IICS Evidence
              </h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Run ID(s)</label>
                  <input
                    type="text"
                    placeholder="(comma separated)"
                    value={(tc.iics_run_ids ?? []).join(', ')}
                    onChange={(e) => handleChange('iics_run_ids', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
                    onBlur={handleBlur}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Org</label>
                  <input
                    type="text"
                    value={val('iics_org')}
                    onChange={(e) => handleChange('iics_org', e.target.value)}
                    onBlur={handleBlur}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Asset Name</label>
                  <input
                    type="text"
                    value={val('iics_asset_name')}
                    onChange={(e) => handleChange('iics_asset_name', e.target.value)}
                    onBlur={handleBlur}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Run Status</label>
                  <select
                    value={val('iics_run_status')}
                    onChange={(e) => handleChange('iics_run_status', e.target.value)}
                    onBlur={handleBlur}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  >
                    <option value="">— Select —</option>
                    {['Success', 'Failed', 'Warning', 'Stopped'].map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: Evidence Panel */}
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Evidence Upload</h2>
            <div className="mb-3">
              <label className="text-xs font-medium text-gray-600 block mb-1">Artefact Type</label>
              <select
                value={selectedArtefactType}
                onChange={(e) => setSelectedArtefactType(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              >
                {artefactTypes.map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <EvidenceUploader
              testCaseId={id}
              artefactType={selectedArtefactType as any}
              onUploaded={() => qc.invalidateQueries({ queryKey: ['evidence', id] })}
            />
          </div>

          {evidence && evidence.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">
                Evidence Files ({evidence.length})
              </h2>
              <div className="space-y-2">
                {evidence.map((e) => (
                  <div key={e.id} className="flex items-center justify-between border border-gray-100 rounded-lg p-2.5">
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-gray-700 truncate">
                        {e.original_filename || e.s3_object_key.split('/').pop()}
                      </div>
                      <div className="text-xs text-gray-400">
                        {e.artefact_type.replace(/_/g, ' ')} ·{' '}
                        {e.file_size_bytes ? `${(e.file_size_bytes / 1024).toFixed(0)} KB` : ''}
                      </div>
                    </div>
                    <button
                      onClick={async () => {
                        const { download_url } = await evidenceApi.getDownloadUrl(e.id);
                        window.open(download_url, '_blank');
                      }}
                      className="text-xs text-blue-600 hover:underline shrink-0 ml-2"
                    >
                      Download
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Execution metadata */}
          {tc.executed_by && (
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
              <div className="text-xs text-gray-500 space-y-1">
                <div><span className="font-medium">Executed by:</span> {tc.executed_by}</div>
                <div><span className="font-medium">Executed at:</span>{' '}
                  {tc.executed_at ? new Date(tc.executed_at).toLocaleString() : '—'}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

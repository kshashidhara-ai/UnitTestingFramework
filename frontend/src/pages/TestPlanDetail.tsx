import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft, Lock, Send, Download, FileText,
  Archive, CheckCircle, Plus, Upload
} from 'lucide-react';
import { testPlansApi, testCasesApi, signoffsApi, exportApi, triggerDownload } from '@/services/api';
import { StatusBadge } from '@/components/common/StatusBadge';
import { CompletenessBar } from '@/components/common/CompletenessBar';
import { useAuth, useRequireRole } from '@/contexts/AuthContext';
import type { TestCase } from '@/types';

const STATUS_OPTIONS = ['NOT_RUN', 'IN_PROGRESS', 'PASS', 'FAIL', 'BLOCKED', 'WAIVED'];

export function TestPlanDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const canReview = useRequireRole('reviewer');
  const canRelease = useRequireRole('release_manager');

  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [submitComment, setSubmitComment] = useState('');

  const { data: plan, isLoading } = useQuery({
    queryKey: ['test-plan', id],
    queryFn: () => testPlansApi.get(id!),
    enabled: !!id,
  });

  const { data: cases } = useQuery({
    queryKey: ['test-cases', id],
    queryFn: () => testCasesApi.list({ test_plan_id: id }),
    enabled: !!id,
  });

  const { data: signoffs } = useQuery({
    queryKey: ['signoffs', id],
    queryFn: () => signoffsApi.list(id!),
    enabled: !!id,
  });

  const submitMutation = useMutation({
    mutationFn: () => testPlansApi.submitReview(id!, submitComment),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['test-plan', id] });
      setShowSubmitModal(false);
    },
  });

  const updateCaseMutation = useMutation({
    mutationFn: ({ caseId, status }: { caseId: string; status: string }) =>
      testCasesApi.update(caseId, { status: status as TestCase['status'] }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['test-cases', id] }),
  });

  const handleExportPdf = async () => {
    const res = await exportApi.downloadPdf(id!);
    triggerDownload(res.data, `UTAP_${id!.slice(0, 8)}_evidence.pdf`);
  };

  const handleExportZip = async () => {
    const res = await exportApi.downloadZip(id!);
    triggerDownload(res.data, `UTAP_${id!.slice(0, 8)}_evidence_pack.zip`);
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-48"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;
  }

  if (!plan) return <div className="text-gray-500">Test plan not found.</div>;

  const statCounts = {
    total: cases?.length ?? 0,
    pass: cases?.filter((c) => c.status === 'PASS').length ?? 0,
    fail: cases?.filter((c) => c.status === 'FAIL').length ?? 0,
    not_run: cases?.filter((c) => c.status === 'NOT_RUN').length ?? 0,
  };

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-700">
            <ArrowLeft size={20} />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-gray-900">{plan.plan_name}</h1>
              {plan.is_locked && <Lock size={16} className="text-slate-500" />}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <StatusBadge status={plan.status} type="test_plan" size="md" />
              <span className="text-sm text-gray-400">by {plan.created_by}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!plan.is_locked && plan.status === 'DRAFT' && (
            <button
              onClick={() => setShowSubmitModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              <Send size={15} />
              Submit for Review
            </button>
          )}
          <button
            onClick={handleExportPdf}
            className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
          >
            <FileText size={15} />
            PDF
          </button>
          <button
            onClick={handleExportZip}
            className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
          >
            <Archive size={15} />
            ZIP Pack
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Cases', value: statCounts.total, color: 'text-gray-900' },
          { label: 'Pass', value: statCounts.pass, color: 'text-green-600' },
          { label: 'Fail', value: statCounts.fail, color: 'text-red-600' },
          { label: 'Not Run', value: statCounts.not_run, color: 'text-gray-500' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-xl p-4">
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
            <div className="text-xs text-gray-500 mt-1">{label}</div>
          </div>
        ))}
      </div>

      {/* Completeness */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <CompletenessBar score={plan.evidence_completeness_score} />
      </div>

      {/* Test Cases Table */}
      <div className="bg-white border border-gray-200 rounded-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-800">Test Cases</h2>
          {!plan.is_locked && (
            <Link
              to={`/test-cases/new?plan_id=${id}`}
              className="flex items-center gap-1.5 text-sm text-blue-600 hover:underline"
            >
              <Plus size={14} />
              Add Case
            </Link>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">ID</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Category</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Objective</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Component</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Evidence</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {cases?.map((tc) => (
                <tr key={tc.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{tc.testcase_id}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{tc.category}</td>
                  <td className="px-4 py-3 text-gray-800 max-w-xs">
                    <span className="line-clamp-2">{tc.objective}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      tc.component === 'SNOWFLAKE' ? 'bg-cyan-100 text-cyan-700' :
                      tc.component === 'IICS' ? 'bg-indigo-100 text-indigo-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {tc.component}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {!plan.is_locked ? (
                      <select
                        value={tc.status}
                        onChange={(e) => updateCaseMutation.mutate({ caseId: tc.id, status: e.target.value })}
                        className="text-xs border border-gray-200 rounded px-2 py-1 bg-white"
                      >
                        {STATUS_OPTIONS.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    ) : (
                      <StatusBadge status={tc.status} type="test_case" />
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium ${(tc.evidence_count ?? 0) > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                      {tc.evidence_count ?? 0} file(s)
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/test-cases/${tc.id}`}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
              {(!cases || cases.length === 0) && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-400">
                    No test cases yet.{' '}
                    {!plan.is_locked && (
                      <Link to={`/test-cases/new?plan_id=${id}`} className="text-blue-600 hover:underline">
                        Add the first one.
                      </Link>
                    )}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Sign-offs */}
      {signoffs && signoffs.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Sign-off Chain</h2>
          <div className="space-y-3">
            {signoffs.map((so) => (
              <div key={so.id} className="flex items-center justify-between border border-gray-100 rounded-lg p-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">{so.level} Review</span>
                    <StatusBadge status={so.decision} type="signoff" />
                  </div>
                  {so.signed_by_name && (
                    <p className="text-xs text-gray-500 mt-0.5">
                      {so.decision} by {so.signed_by_name} · {so.signed_at ? new Date(so.signed_at).toLocaleDateString() : ''}
                    </p>
                  )}
                  {so.comments && <p className="text-xs text-gray-600 mt-1 italic">"{so.comments}"</p>}
                </div>
                {so.decision === 'PENDING' && canReview && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => signoffsApi.decide(so.id, { decision: 'APPROVED' }).then(() => qc.invalidateQueries({ queryKey: ['signoffs', id] }))}
                      className="px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => {
                        const reason = prompt('Rejection reason:');
                        if (reason) signoffsApi.decide(so.id, { decision: 'REJECTED', rejection_reason: reason }).then(() => qc.invalidateQueries({ queryKey: ['signoffs', id] }));
                      }}
                      className="px-3 py-1.5 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700"
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Submit Modal */}
      {showSubmitModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Submit for Review</h3>
            <p className="text-sm text-gray-600 mb-4">
              This will lock the test plan for editing until reviewed. All validation rules will be enforced.
            </p>
            <textarea
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none"
              rows={3}
              placeholder="Optional comments for the reviewer..."
              value={submitComment}
              onChange={(e) => setSubmitComment(e.target.value)}
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setShowSubmitModal(false)}
                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => submitMutation.mutate()}
                disabled={submitMutation.isPending}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {submitMutation.isPending ? 'Submitting...' : 'Submit'}
              </button>
            </div>
            {submitMutation.isError && (
              <p className="text-xs text-red-600 mt-2">
                {(submitMutation.error as Error)?.message || 'Submission failed. Check all rules are met.'}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

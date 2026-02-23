import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, Search, Lock, Filter } from 'lucide-react';
import { testPlansApi } from '@/services/api';
import { StatusBadge } from '@/components/common/StatusBadge';
import { CompletenessBar } from '@/components/common/CompletenessBar';
import type { TestPlanStatus } from '@/types';

const STATUS_OPTIONS: TestPlanStatus[] = ['DRAFT', 'IN_REVIEW', 'APPROVED', 'LOCKED', 'REJECTED'];

export function TestPlans() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<TestPlanStatus | ''>('');

  const { data: plans, isLoading } = useQuery({
    queryKey: ['test-plans', statusFilter],
    queryFn: () => testPlansApi.list({ status: statusFilter || undefined }),
  });

  const filtered = plans?.filter((p) =>
    !search || p.plan_name.toLowerCase().includes(search.toLowerCase())
  ) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Test Plans</h1>
        <Link
          to="/test-plans/new"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          <Plus size={15} />
          New Test Plan
        </Link>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search test plans..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter size={15} className="text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as TestPlanStatus | '')}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
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
                <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Plan Name</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Cases</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase w-40">Completeness</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Created By</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((plan) => (
                <tr key={plan.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      {plan.is_locked && <Lock size={13} className="text-slate-400 shrink-0" />}
                      <Link
                        to={`/test-plans/${plan.id}`}
                        className="font-medium text-gray-900 hover:text-blue-600 transition-colors"
                      >
                        {plan.plan_name}
                      </Link>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={plan.status} type="test_plan" />
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    {plan.test_case_count ?? 0} total ·{' '}
                    <span className="text-green-600">{plan.pass_count ?? 0} pass</span> ·{' '}
                    <span className="text-red-600">{plan.fail_count ?? 0} fail</span>
                  </td>
                  <td className="px-4 py-3 w-40">
                    <CompletenessBar score={plan.evidence_completeness_score} showLabel={false} />
                    <div className="text-xs text-gray-400 mt-0.5 text-right">
                      {plan.evidence_completeness_score.toFixed(0)}%
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{plan.created_by}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {new Date(plan.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/test-plans/${plan.id}`}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-5 py-10 text-center text-gray-400 text-sm">
                    No test plans found.{' '}
                    <Link to="/test-plans/new" className="text-blue-600 hover:underline">
                      Create your first one.
                    </Link>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

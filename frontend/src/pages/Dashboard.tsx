import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  ClipboardList, FolderKanban, CheckSquare, Clock,
  TrendingUp, AlertTriangle, Lock
} from 'lucide-react';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { dashboardApi } from '@/services/api';
import { StatusBadge } from '@/components/common/StatusBadge';
import { CompletenessBar } from '@/components/common/CompletenessBar';
import { useAuth } from '@/contexts/AuthContext';

const STATUS_COLORS: Record<string, string> = {
  PASS: '#22c55e', FAIL: '#ef4444', NOT_RUN: '#94a3b8',
  BLOCKED: '#f97316', WAIVED: '#a855f7', IN_PROGRESS: '#3b82f6',
};

function StatCard({
  title, value, icon: Icon, color, subtitle
}: {
  title: string; value: number; icon: React.ElementType;
  color: string; subtitle?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${color}`}>
          <Icon size={22} className="text-white" />
        </div>
      </div>
    </div>
  );
}

export function Dashboard() {
  const { user } = useAuth();
  const { data: summary, isLoading } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: dashboardApi.getSummary,
    refetchInterval: 30_000,
  });
  const { data: myPlans } = useQuery({
    queryKey: ['my-plans'],
    queryFn: dashboardApi.getMyPlans,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const tc = summary?.test_case_stats;
  const pieData = tc ? [
    { name: 'Pass', value: tc.pass, color: STATUS_COLORS.PASS },
    { name: 'Fail', value: tc.fail, color: STATUS_COLORS.FAIL },
    { name: 'Not Run', value: tc.not_run, color: STATUS_COLORS.NOT_RUN },
    { name: 'Blocked', value: tc.blocked, color: STATUS_COLORS.BLOCKED },
    { name: 'Waived', value: tc.waived, color: STATUS_COLORS.WAIVED },
  ].filter((d) => d.value > 0) : [];

  const planBarData = summary ? Object.entries(summary.test_plan_stats).map(([status, count]) => ({
    status, count,
  })) : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.display_name?.split(' ')[0] || 'User'}
        </h1>
        <p className="text-gray-500 text-sm mt-1">Here's what's happening across your test portfolio.</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="My Test Plans"
          value={summary?.my_test_plans ?? 0}
          icon={ClipboardList}
          color="bg-blue-600"
        />
        <StatCard
          title="Pending Reviews"
          value={summary?.pending_reviews ?? 0}
          icon={Clock}
          color="bg-amber-500"
          subtitle="Awaiting your action"
        />
        <StatCard
          title="Active Projects"
          value={summary?.active_projects ?? 0}
          icon={FolderKanban}
          color="bg-emerald-600"
        />
        <StatCard
          title="Pass Rate"
          value={tc?.pass_rate ?? 0}
          icon={TrendingUp}
          color="bg-violet-600"
          subtitle={`${tc?.pass ?? 0} / ${tc?.total ?? 0} test cases`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Test Case Pie Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Test Case Status</h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => [v, '']} />
                <Legend iconType="circle" iconSize={8} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
              No test cases yet
            </div>
          )}
        </div>

        {/* Test Plan Status Bar Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Test Plans by Status</h2>
          {planBarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={planBarData} margin={{ top: 5, right: 5, bottom: 5, left: -20 }}>
                <XAxis dataKey="status" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
              No test plans yet
            </div>
          )}
        </div>

        {/* Quick actions */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Quick Actions</h2>
          <div className="space-y-2">
            <Link
              to="/test-plans/new"
              className="flex items-center gap-3 p-3 rounded-lg bg-blue-50 hover:bg-blue-100 transition-colors"
            >
              <ClipboardList size={18} className="text-blue-600" />
              <span className="text-sm font-medium text-blue-700">Create Test Plan</span>
            </Link>
            <Link
              to="/test-plans?status=IN_REVIEW"
              className="flex items-center gap-3 p-3 rounded-lg bg-amber-50 hover:bg-amber-100 transition-colors"
            >
              <Clock size={18} className="text-amber-600" />
              <span className="text-sm font-medium text-amber-700">
                Review Plans ({summary?.pending_reviews ?? 0})
              </span>
            </Link>
            <Link
              to="/evidence"
              className="flex items-center gap-3 p-3 rounded-lg bg-emerald-50 hover:bg-emerald-100 transition-colors"
            >
              <CheckSquare size={18} className="text-emerald-600" />
              <span className="text-sm font-medium text-emerald-700">Evidence Repository</span>
            </Link>
          </div>
        </div>
      </div>

      {/* My Recent Plans */}
      {myPlans && myPlans.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">My Recent Test Plans</h2>
            <Link to="/test-plans" className="text-xs text-blue-600 hover:underline">
              View all
            </Link>
          </div>
          <div className="divide-y divide-gray-50">
            {myPlans.slice(0, 5).map((plan) => (
              <div key={plan.id} className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 transition-colors">
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/test-plans/${plan.id}`}
                    className="text-sm font-medium text-gray-900 hover:text-blue-600 truncate block"
                  >
                    {plan.plan_name}
                  </Link>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {plan.test_case_count ?? 0} cases ·{' '}
                    {plan.pass_count ?? 0} pass ·{' '}
                    {plan.fail_count ?? 0} fail
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <CompletenessBar score={plan.evidence_completeness_score} showLabel={false} />
                  <StatusBadge status={plan.status} type="test_plan" />
                  {plan.is_locked && <Lock size={14} className="text-slate-500" />}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

import clsx from 'clsx';
import type { TestCaseStatus, TestPlanStatus, SignoffDecision } from '@/types';

const TC_STATUS_STYLES: Record<TestCaseStatus, string> = {
  PASS:        'bg-green-100 text-green-800 border-green-200',
  FAIL:        'bg-red-100 text-red-800 border-red-200',
  NOT_RUN:     'bg-gray-100 text-gray-600 border-gray-200',
  IN_PROGRESS: 'bg-blue-100 text-blue-800 border-blue-200',
  BLOCKED:     'bg-orange-100 text-orange-800 border-orange-200',
  WAIVED:      'bg-purple-100 text-purple-800 border-purple-200',
};

const PLAN_STATUS_STYLES: Record<TestPlanStatus, string> = {
  DRAFT:       'bg-gray-100 text-gray-700 border-gray-200',
  IN_REVIEW:   'bg-blue-100 text-blue-800 border-blue-200',
  APPROVED:    'bg-green-100 text-green-800 border-green-200',
  LOCKED:      'bg-slate-100 text-slate-800 border-slate-200',
  REJECTED:    'bg-red-100 text-red-800 border-red-200',
};

const SIGNOFF_STYLES: Record<SignoffDecision, string> = {
  APPROVED: 'bg-green-100 text-green-800 border-green-200',
  REJECTED: 'bg-red-100 text-red-800 border-red-200',
  PENDING:  'bg-amber-100 text-amber-800 border-amber-200',
};

interface Props {
  status: string;
  type: 'test_case' | 'test_plan' | 'signoff';
  size?: 'sm' | 'md';
}

export function StatusBadge({ status, type, size = 'sm' }: Props) {
  let style = 'bg-gray-100 text-gray-600 border-gray-200';

  if (type === 'test_case') style = TC_STATUS_STYLES[status as TestCaseStatus] ?? style;
  if (type === 'test_plan') style = PLAN_STATUS_STYLES[status as TestPlanStatus] ?? style;
  if (type === 'signoff') style = SIGNOFF_STYLES[status as SignoffDecision] ?? style;

  return (
    <span
      className={clsx(
        'inline-flex items-center border rounded-full font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm',
        style
      )}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
}

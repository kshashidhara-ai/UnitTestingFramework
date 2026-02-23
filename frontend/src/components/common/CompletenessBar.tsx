import clsx from 'clsx';

interface Props {
  score: number;
  threshold?: number;
  showLabel?: boolean;
}

export function CompletenessBar({ score, threshold = 90, showLabel = true }: Props) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct >= threshold ? 'bg-green-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="space-y-1">
      {showLabel && (
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>Evidence Completeness</span>
          <span className={clsx('font-semibold', pct >= threshold ? 'text-green-600' : 'text-red-600')}>
            {pct.toFixed(1)}%
          </span>
        </div>
      )}
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-500', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex justify-end">
          <span className="text-xs text-gray-400">Threshold: {threshold}%</span>
        </div>
      )}
    </div>
  );
}

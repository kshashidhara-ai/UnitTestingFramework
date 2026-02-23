import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Shield, Search } from 'lucide-react';
import api from '@/services/api';

export function AuditLog() {
  const [page, setPage] = useState(1);
  const [userEmail, setUserEmail] = useState('');
  const [entityType, setEntityType] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['audit-log', page, userEmail, entityType],
    queryFn: () =>
      api.get('/audit', {
        params: {
          page,
          page_size: 50,
          user_email: userEmail || undefined,
          entity_type: entityType || undefined,
        },
      }).then((r) => r.data),
  });

  const ACTION_COLORS: Record<string, string> = {
    LOGIN: 'bg-green-100 text-green-700',
    LOGOUT: 'bg-gray-100 text-gray-600',
    CREATE: 'bg-blue-100 text-blue-700',
    UPDATE: 'bg-amber-100 text-amber-700',
    DELETE: 'bg-red-100 text-red-700',
    STATUS_CHANGE: 'bg-purple-100 text-purple-700',
    ARTEFACT_UPLOAD: 'bg-cyan-100 text-cyan-700',
    SIGNOFF: 'bg-emerald-100 text-emerald-700',
    LOCK: 'bg-slate-100 text-slate-700',
    EXPORT: 'bg-indigo-100 text-indigo-700',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Shield size={22} className="text-slate-600" />
        <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Filter by user email..."
            value={userEmail}
            onChange={(e) => setUserEmail(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm"
          />
        </div>
        <select
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Entities</option>
          {['Project', 'Release', 'TestPlan', 'TestCase', 'EvidenceArtefact', 'Signoff'].map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>
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
                <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Timestamp</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">User</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Role</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Action</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Entity</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Description</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data?.items?.map((item: any) => (
                <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3 text-xs text-gray-500 font-mono whitespace-nowrap">
                    {new Date(item.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-700 truncate max-w-[160px]">{item.user_email}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{item.user_role}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ACTION_COLORS[item.action_type] || 'bg-gray-100 text-gray-600'}`}>
                      {item.action_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {item.entity_type}{item.entity_id && <span className="text-gray-300"> #{item.entity_id.slice(0, 8)}</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">{item.description}</td>
                  <td className="px-4 py-3 text-xs text-gray-400 font-mono">{item.ip_address}</td>
                </tr>
              ))}
              {(!data?.items || data.items.length === 0) && (
                <tr>
                  <td colSpan={7} className="px-5 py-10 text-center text-gray-400 text-sm">
                    No audit records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100">
            <span className="text-xs text-gray-500">
              {data?.total ?? 0} total records · Page {page}
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
                disabled={!data?.items || data.items.length < 50}
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

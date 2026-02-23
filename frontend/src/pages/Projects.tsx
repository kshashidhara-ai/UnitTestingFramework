import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Globe, Package } from 'lucide-react';
import { projectsApi } from '@/services/api';
import { useRequireRole } from '@/contexts/AuthContext';

export function Projects() {
  const qc = useQueryClient();
  const canCreate = useRequireRole('developer');
  const [search, setSearch] = useState('');
  const [country, setCountry] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', domain: '', owner_team: '', country: '', vendor: '', frequency: '' });

  const { data, isLoading } = useQuery({
    queryKey: ['projects', search, country],
    queryFn: () => projectsApi.list({ search: search || undefined, country: country || undefined }),
  });

  const createMutation = useMutation({
    mutationFn: () => projectsApi.create(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] });
      setShowCreate(false);
      setForm({ name: '', domain: '', owner_team: '', country: '', vendor: '', frequency: '' });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
        {canCreate && (
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            <Plus size={15} />
            New Project
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm"
          />
        </div>
        <select
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Countries</option>
          {['US', 'UK', 'DE', 'AU', 'CA'].map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* Projects Grid */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.items.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-blue-200 transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center group-hover:bg-blue-100 transition-colors">
                  <Package size={20} className="text-blue-600" />
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  project.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}>
                  {project.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <h3 className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">{project.name}</h3>
              <p className="text-sm text-gray-500 mt-1">{project.domain}</p>
              <div className="flex items-center gap-3 mt-3 text-xs text-gray-400">
                {project.country && (
                  <span className="flex items-center gap-1">
                    <Globe size={11} />
                    {project.country}
                  </span>
                )}
                {project.vendor && <span>{project.vendor}</span>}
                {project.frequency && <span>{project.frequency}</span>}
              </div>
            </Link>
          ))}
          {(!data?.items || data.items.length === 0) && (
            <div className="col-span-3 py-12 text-center text-gray-400">
              No projects found. Create the first one!
            </div>
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Create Project</h3>
            <div className="space-y-3">
              {[
                { field: 'name', label: 'Project Name *', placeholder: 'Sales_DWH' },
                { field: 'domain', label: 'Domain', placeholder: 'Data Warehouse' },
                { field: 'owner_team', label: 'Owner Team', placeholder: 'DWH Engineering' },
                { field: 'country', label: 'Country', placeholder: 'US' },
                { field: 'vendor', label: 'Vendor', placeholder: 'IQVIA' },
              ].map(({ field, label, placeholder }) => (
                <div key={field}>
                  <label className="text-xs font-medium text-gray-600 block mb-1">{label}</label>
                  <input
                    type="text"
                    value={form[field as keyof typeof form]}
                    onChange={(e) => setForm((p) => ({ ...p, [field]: e.target.value }))}
                    placeholder={placeholder}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              ))}
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Frequency</label>
                <select
                  value={form.frequency}
                  onChange={(e) => setForm((p) => ({ ...p, frequency: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">Select...</option>
                  {['Daily', 'Weekly', 'Monthly', 'Quarterly'].map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button
                onClick={() => setShowCreate(false)}
                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => createMutation.mutate()}
                disabled={!form.name || createMutation.isPending}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {createMutation.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

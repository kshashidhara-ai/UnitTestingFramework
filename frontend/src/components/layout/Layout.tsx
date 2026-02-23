import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, FolderKanban, ClipboardList, TestTube2,
  Archive, LogOut, ChevronLeft, ChevronRight, User, Shield,
  FileText, Bell
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { authApi } from '@/services/api';
import clsx from 'clsx';

const NAV_ITEMS = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/projects', icon: FolderKanban, label: 'Projects' },
  { path: '/test-plans', icon: ClipboardList, label: 'Test Plans' },
  { path: '/evidence', icon: Archive, label: 'Evidence Repository' },
];

const ADMIN_ITEMS = [
  { path: '/audit', icon: Shield, label: 'Audit Log' },
];

const ROLE_BADGE: Record<string, string> = {
  developer: 'bg-blue-100 text-blue-800',
  reviewer: 'bg-purple-100 text-purple-800',
  release_manager: 'bg-amber-100 text-amber-800',
  admin: 'bg-red-100 text-red-800',
};

export function Layout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = async () => {
    await authApi.logout();
    navigate('/auth/login');
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={clsx(
          'flex flex-col bg-slate-900 text-white transition-all duration-200 shrink-0',
          collapsed ? 'w-16' : 'w-64'
        )}
      >
        {/* Logo */}
        <div className={clsx('flex items-center border-b border-slate-700 h-16 px-4', collapsed ? 'justify-center' : 'gap-3')}>
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center shrink-0">
            <TestTube2 size={18} className="text-white" />
          </div>
          {!collapsed && (
            <div>
              <div className="text-sm font-bold leading-tight">UTAP</div>
              <div className="text-xs text-slate-400 leading-tight">Unit Test Artefact Portal</div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
          {NAV_ITEMS.map(({ path, icon: Icon, label }) => (
            <Link
              key={path}
              to={path}
              className={clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                location.pathname === path || (path !== '/' && location.pathname.startsWith(path))
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              )}
              title={collapsed ? label : undefined}
            >
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </Link>
          ))}

          {(user?.role === 'admin' || user?.role === 'release_manager') && (
            <>
              <div className={clsx('pt-4 pb-1 px-1', collapsed && 'hidden')}>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Admin</p>
              </div>
              {ADMIN_ITEMS.map(({ path, icon: Icon, label }) => (
                <Link
                  key={path}
                  to={path}
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                    location.pathname.startsWith(path)
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  )}
                  title={collapsed ? label : undefined}
                >
                  <Icon size={18} className="shrink-0" />
                  {!collapsed && <span>{label}</span>}
                </Link>
              ))}
            </>
          )}
        </nav>

        {/* User Profile */}
        <div className="border-t border-slate-700 p-3">
          {!collapsed ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-slate-600 flex items-center justify-center shrink-0">
                  <User size={15} />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">{user?.display_name || user?.email}</div>
                  <span className={clsx('text-xs px-1.5 py-0.5 rounded font-medium', ROLE_BADGE[user?.role || 'developer'])}>
                    {user?.role?.replace('_', ' ')}
                  </span>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 w-full text-xs text-slate-400 hover:text-white px-2 py-1.5 rounded hover:bg-slate-800 transition-colors"
              >
                <LogOut size={14} />
                Sign out
              </button>
            </div>
          ) : (
            <button
              onClick={handleLogout}
              className="flex justify-center w-full text-slate-400 hover:text-white p-1.5 rounded hover:bg-slate-800 transition-colors"
              title="Sign out"
            >
              <LogOut size={18} />
            </button>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute left-full top-1/2 -translate-y-1/2 w-5 h-10 bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center rounded-r-md hover:bg-slate-600 transition-colors z-10"
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Top bar */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
          <div className="text-lg font-semibold text-gray-800">
            {/* Page title will be set by individual pages */}
          </div>
          <div className="flex items-center gap-4">
            <button className="text-gray-500 hover:text-gray-700 relative">
              <Bell size={20} />
            </button>
            <div className="text-sm text-gray-600">
              {user?.email}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

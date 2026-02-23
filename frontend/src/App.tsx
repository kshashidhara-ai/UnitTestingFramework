import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Projects } from '@/pages/Projects'
import { TestPlans } from '@/pages/TestPlans'
import { TestPlanDetail } from '@/pages/TestPlanDetail'
import { TestCaseDetail } from '@/pages/TestCaseDetail'
import { EvidenceRepository } from '@/pages/EvidenceRepository'
import { AuditLog } from '@/pages/AuditLog'
import { useAuth } from '@/contexts/AuthContext'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto" />
          <p className="text-sm text-gray-500">Loading UTAP...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    window.location.href = '/api/v1/auth/login'
    return null
  }

  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/projects" element={<Projects />} />
                <Route path="/test-plans" element={<TestPlans />} />
                <Route path="/test-plans/:id" element={<TestPlanDetail />} />
                <Route path="/test-cases/:id" element={<TestCaseDetail />} />
                <Route path="/evidence" element={<EvidenceRepository />} />
                <Route path="/audit" element={<AuditLog />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

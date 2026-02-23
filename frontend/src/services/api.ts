import axios from 'axios';
import type {
  Project, ProjectList, Release, DevelopmentActivity,
  TestPlan, TestCase, EvidenceArtefact, Signoff,
  DashboardSummary, PresignedUploadResponse, CurrentUser
} from '@/types';

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      window.location.href = '/api/v1/auth/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  getMe: () => api.get<CurrentUser>('/auth/me').then((r) => r.data),
  logout: () => api.get('/auth/logout'),
};

// ── Dashboard ─────────────────────────────────────────────────────────────────

export const dashboardApi = {
  getSummary: () => api.get<DashboardSummary>('/dashboard/summary').then((r) => r.data),
  getMyPlans: () => api.get<TestPlan[]>('/dashboard/my-plans').then((r) => r.data),
};

// ── Projects ─────────────────────────────────────────────────────────────────

export const projectsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<ProjectList>('/projects', { params }).then((r) => r.data),
  get: (id: string) => api.get<Project>(`/projects/${id}`).then((r) => r.data),
  create: (data: Partial<Project>) => api.post<Project>('/projects', data).then((r) => r.data),
  update: (id: string, data: Partial<Project>) =>
    api.patch<Project>(`/projects/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/projects/${id}`),
};

// ── Releases ─────────────────────────────────────────────────────────────────

export const releasesApi = {
  list: (projectId?: string) =>
    api.get<Release[]>('/releases', { params: { project_id: projectId } }).then((r) => r.data),
  get: (id: string) => api.get<Release>(`/releases/${id}`).then((r) => r.data),
  create: (data: Partial<Release>) => api.post<Release>('/releases', data).then((r) => r.data),
  update: (id: string, data: Partial<Release>) =>
    api.patch<Release>(`/releases/${id}`, data).then((r) => r.data),
};

// ── Dev Activities ────────────────────────────────────────────────────────────

export const devActivitiesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<DevelopmentActivity[]>('/dev-activities', { params }).then((r) => r.data),
  get: (id: string) => api.get<DevelopmentActivity>(`/dev-activities/${id}`).then((r) => r.data),
  create: (data: Partial<DevelopmentActivity>) =>
    api.post<DevelopmentActivity>('/dev-activities', data).then((r) => r.data),
  update: (id: string, data: Partial<DevelopmentActivity>) =>
    api.patch<DevelopmentActivity>(`/dev-activities/${id}`, data).then((r) => r.data),
};

// ── Test Plans ────────────────────────────────────────────────────────────────

export const testPlansApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<TestPlan[]>('/test-plans', { params }).then((r) => r.data),
  get: (id: string) => api.get<TestPlan>(`/test-plans/${id}`).then((r) => r.data),
  create: (data: Partial<TestPlan>) => api.post<TestPlan>('/test-plans', data).then((r) => r.data),
  update: (id: string, data: Partial<TestPlan>) =>
    api.patch<TestPlan>(`/test-plans/${id}`, data).then((r) => r.data),
  submitReview: (id: string, comments?: string) =>
    api.post<TestPlan>(`/test-plans/${id}/submit-review`, { comments }).then((r) => r.data),
  lockOverride: (id: string, reason: string) =>
    api.post<TestPlan>(`/test-plans/${id}/lock-override`, { reason }).then((r) => r.data),
};

// ── Test Cases ────────────────────────────────────────────────────────────────

export const testCasesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<TestCase[]>('/test-cases', { params }).then((r) => r.data),
  get: (id: string) => api.get<TestCase>(`/test-cases/${id}`).then((r) => r.data),
  create: (data: Partial<TestCase>) =>
    api.post<TestCase>('/test-cases', data).then((r) => r.data),
  update: (id: string, data: Partial<TestCase>) =>
    api.patch<TestCase>(`/test-cases/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/test-cases/${id}`),
  bulkImport: (planId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.post(`/test-cases/bulk-import?test_plan_id=${planId}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ── Evidence ──────────────────────────────────────────────────────────────────

export const evidenceApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<EvidenceArtefact[]>('/evidence', { params }).then((r) => r.data),
  getDownloadUrl: (id: string) =>
    api.get<{ download_url: string; expires_in: number }>(`/evidence/${id}/download`).then((r) => r.data),
  getPresignedUpload: (data: {
    test_case_id?: string;
    test_plan_id?: string;
    artefact_type: string;
    filename: string;
    content_type: string;
    file_size_bytes: number;
  }) => api.post<PresignedUploadResponse>('/evidence/presigned-upload', data).then((r) => r.data),
  register: (data: Partial<EvidenceArtefact>) =>
    api.post<EvidenceArtefact>('/evidence', data).then((r) => r.data),
  delete: (id: string) => api.delete(`/evidence/${id}`),
};

// ── S3 Direct Upload ──────────────────────────────────────────────────────────

export async function uploadToS3(
  presigned: PresignedUploadResponse,
  file: File,
  onProgress?: (pct: number) => void
): Promise<void> {
  const form = new FormData();
  if (presigned.fields) {
    Object.entries(presigned.fields).forEach(([k, v]) => form.append(k, v));
  }
  form.append('file', file);

  await axios.post(presigned.upload_url, form, {
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded / evt.total) * 100));
      }
    },
  });
}

// ── Signoffs ──────────────────────────────────────────────────────────────────

export const signoffsApi = {
  list: (planId: string) =>
    api.get<Signoff[]>('/signoffs', { params: { test_plan_id: planId } }).then((r) => r.data),
  request: (data: { test_plan_id: string; level: string; comments?: string }) =>
    api.post<Signoff>('/signoffs', data).then((r) => r.data),
  decide: (id: string, data: { decision: string; comments?: string; rejection_reason?: string }) =>
    api.post<Signoff>(`/signoffs/${id}/decide`, data).then((r) => r.data),
};

// ── Export ────────────────────────────────────────────────────────────────────

export const exportApi = {
  downloadPdf: (planId: string) =>
    api.get(`/export/test-plan/${planId}/pdf`, { responseType: 'blob' }),
  downloadCsv: (planId: string) =>
    api.get(`/export/test-plan/${planId}/csv`, { responseType: 'blob' }),
  downloadZip: (planId: string) =>
    api.get(`/export/test-plan/${planId}/zip`, { responseType: 'blob' }),
};

export function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default api;

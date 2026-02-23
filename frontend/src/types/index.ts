// ── Enums ────────────────────────────────────────────────────────────────────

export type EnvironmentScope = 'SIT' | 'UAT' | 'PROD';
export type ReleaseStatus = 'PLANNED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
export type ActivityType = 'SNOWFLAKE' | 'IICS' | 'MIXED' | 'OTHER';
export type TestPlanStatus = 'DRAFT' | 'IN_REVIEW' | 'APPROVED' | 'LOCKED' | 'REJECTED';
export type TestCaseStatus = 'NOT_RUN' | 'IN_PROGRESS' | 'PASS' | 'FAIL' | 'BLOCKED' | 'WAIVED';
export type TestCaseCategory = 'FUNCTIONAL' | 'REGRESSION' | 'PERFORMANCE' | 'DATA_QUALITY' | 'INTEGRATION' | 'RECONCILIATION' | 'IDEMPOTENCY' | 'NEGATIVE';
export type TestCaseComponent = 'SNOWFLAKE' | 'IICS' | 'BOTH' | 'OTHER';
export type ArtefactType =
  | 'SNOWFLAKE_QUERY_RESULT' | 'SNOWFLAKE_SCREENSHOT' | 'SNOWFLAKE_EXPLAIN_PLAN' | 'SNOWFLAKE_RECONCILIATION'
  | 'IICS_ACTIVITY_LOG' | 'IICS_SESSION_LOG' | 'IICS_MONITOR_SCREENSHOT' | 'IICS_REJECTION_FILE'
  | 'SCREENSHOT' | 'CSV_EXPORT' | 'PDF_DOCUMENT' | 'LOG_FILE' | 'OTHER';
export type SignoffLevel = 'PEER' | 'QA' | 'RELEASE';
export type SignoffDecision = 'APPROVED' | 'REJECTED' | 'PENDING';

// ── User / Auth ──────────────────────────────────────────────────────────────

export interface CurrentUser {
  email: string;
  name: string;
  display_name: string;
  role: 'developer' | 'reviewer' | 'release_manager' | 'admin';
  groups: string[];
}

// ── Projects ─────────────────────────────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  domain?: string;
  description?: string;
  owner_team?: string;
  country?: string;
  dataset?: string;
  vendor?: string;
  frequency?: string;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface ProjectList {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
}

// ── Releases ─────────────────────────────────────────────────────────────────

export interface Release {
  id: string;
  project_id: string;
  release_name: string;
  description?: string;
  environment_scope: EnvironmentScope;
  status: ReleaseStatus;
  planned_deploy_date?: string;
  actual_deploy_date?: string;
  created_by: string;
  created_at: string;
}

// ── Dev Activities ────────────────────────────────────────────────────────────

export interface SnowflakeObject {
  database: string;
  schema_name: string;
  object_name: string;
  object_type: string;
}

export interface IICSAsset {
  org: string;
  asset_type: string;
  asset_name: string;
  asset_id?: string;
}

export interface DevelopmentActivity {
  id: string;
  project_id: string;
  release_id: string;
  title: string;
  description?: string;
  activity_type: ActivityType;
  jira_id?: string;
  git_repo?: string;
  pr_link?: string;
  commit_hash?: string;
  snowflake_objects?: SnowflakeObject[];
  iics_assets?: IICSAsset[];
  created_by: string;
  created_at: string;
}

// ── Test Plans ────────────────────────────────────────────────────────────────

export interface TestPlan {
  id: string;
  dev_activity_id: string;
  plan_name: string;
  scope?: string;
  test_strategy?: string;
  entry_criteria?: string;
  exit_criteria?: string;
  status: TestPlanStatus;
  evidence_completeness_score: number;
  is_locked: boolean;
  submitted_for_review_at?: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
  last_autosave_at?: string;
  test_case_count?: number;
  pass_count?: number;
  fail_count?: number;
  not_run_count?: number;
}

// ── Test Cases ────────────────────────────────────────────────────────────────

export interface TestCase {
  id: string;
  test_plan_id: string;
  testcase_id: string;
  category: TestCaseCategory;
  component: TestCaseComponent;
  objective: string;
  preconditions?: string;
  test_steps: string;
  expected_result: string;
  actual_result?: string;
  status: TestCaseStatus;
  defect_reference?: string;
  waiver_reason?: string;
  snowflake_query_ids?: string[];
  snowflake_warehouse?: string;
  snowflake_database_schema_object?: string;
  sql_executed?: string;
  snowflake_execution_timestamp?: string;
  snowflake_rows_produced?: string;
  snowflake_execution_duration_ms?: string;
  iics_run_ids?: string[];
  iics_org?: string;
  iics_asset_type?: string;
  iics_asset_name?: string;
  iics_run_start?: string;
  iics_run_end?: string;
  iics_run_status?: string;
  executed_by?: string;
  executed_at?: string;
  reviewer_comment?: string;
  is_template: boolean;
  template_name?: string;
  evidence_count?: number;
  created_by: string;
  created_at: string;
}

// ── Evidence ──────────────────────────────────────────────────────────────────

export interface EvidenceArtefact {
  id: string;
  test_case_id?: string;
  test_plan_id?: string;
  artefact_type: ArtefactType;
  description?: string;
  original_filename?: string;
  s3_object_key: string;
  s3_bucket: string;
  file_size_bytes?: number;
  content_type?: string;
  metadata_json?: Record<string, unknown>;
  is_legal_hold: boolean;
  uploaded_by: string;
  uploaded_at: string;
}

export interface PresignedUploadResponse {
  upload_url: string;
  s3_object_key: string;
  s3_bucket: string;
  fields?: Record<string, string>;
  expires_in: number;
}

// ── Signoffs ──────────────────────────────────────────────────────────────────

export interface Signoff {
  id: string;
  test_plan_id: string;
  level: SignoffLevel;
  decision: SignoffDecision;
  comments?: string;
  rejection_reason?: string;
  signed_by?: string;
  signed_by_name?: string;
  signed_at?: string;
  requested_at: string;
  requested_by: string;
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardSummary {
  my_test_plans: number;
  pending_reviews: number;
  pending_signoffs: number;
  active_projects: number;
  test_case_stats: {
    total: number;
    pass: number;
    fail: number;
    not_run: number;
    blocked: number;
    waived: number;
    pass_rate: number;
  };
  test_plan_stats: Record<string, number>;
}

// ── Pagination ────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

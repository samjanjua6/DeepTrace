export type RiskTier = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ActionDirective =
  | "STRAIGHT_THROUGH_APPROVAL"
  | "MANUAL_SUPERVISOR_REVIEW"
  | "ENHANCED_DUE_DILIGENCE"
  | "IMMEDIATE_REJECTION"
  | "MANDATORY_STR_AND_ACCOUNT_FREEZE"
  | "ENHANCED_TRANSACTION_MONITORING"
  | "SECONDARY_SCAN"
  | "HUMAN_REVIEW"
  | "ESCALATION_REQUIRED"
  | (string & {});

export const RECOMMENDATION_MAP: Record<string, string> = {
  IMMEDIATE_REJECTION: "Recommend: Reject / Escalate to Fraud Unit",
  MANDATORY_STR_AND_ACCOUNT_FREEZE: "Recommend: Mandatory STR Escalation & Freeze Review",
  ENHANCED_TRANSACTION_MONITORING: "Recommend: Enhanced Due Diligence / Compliance Review",
  ESCALATION_REQUIRED: "Recommend: Escalate to Senior Underwriter",
  HUMAN_REVIEW: "Recommend: Human Review & Operational Verification",
  SECONDARY_SCAN: "Recommend: Secondary Branch / Counterfoil Verification",
  STRAIGHT_THROUGH_APPROVAL: "Recommend: Straight-Through Approval (Standard Underwriting)",
  MANUAL_SUPERVISOR_REVIEW: "Recommend: Human Review & Operational Verification",
  ENHANCED_DUE_DILIGENCE: "Recommend: Enhanced Due Diligence / Compliance Review",
};

export function formatRecommendation(directive?: string | null, tier?: string | null): string {
  if (!directive) return "Recommend: Operational Verification";
  const norm = directive.trim().toUpperCase();
  if (RECOMMENDATION_MAP[norm]) {
    return RECOMMENDATION_MAP[norm];
  }
  if (norm.includes("REJECT")) return "Recommend: Reject / Escalate to Fraud Unit";
  if (norm.includes("FREEZE") || norm.includes("STR")) return "Recommend: Mandatory STR Escalation & Freeze Review";
  if (norm.includes("MONITOR") || norm.includes("EDD")) return "Recommend: Enhanced Due Diligence / Compliance Review";
  if (norm.includes("APPROV") || norm.includes("STRAIGHT")) return "Recommend: Straight-Through Processing (Standard Underwriting)";
  const cleaned = norm.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
  return `Recommend: ${cleaned}`;
}

export type PipelineStatus =
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type FindingSeverity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface BoundingBox {
  id: string;
  evidenceItemId: string;
  pageNumber: number;
  x: number;
  y: number;
  width: number;
  height: number;
  xPts?: number;
  yPts?: number;
  widthPts?: number;
  heightPts?: number;
  label?: string;
  color?: string;
  source?: string;
  createdAt?: string;
}

export type AnchorType =
  | "DOCUMENT_METADATA"
  | "TABLE_ROW"
  | "PAGE_REGION"
  | "DOCUMENT_HEADER"
  | "MULTI_PAGE_SPAN"
  | "STATEMENT_SUMMARY"
  | "LEDGER_TERMINAL";

export interface EvidenceAnchor {
  id?: string;
  type: AnchorType | string;
  pageNumber?: number | null;
  pageEnd?: number | null;
  rowNumber?: number | null;
  label: string;
  bboxId?: string;
}

export interface EvidenceItem {
  id: string;
  documentId: string;
  pipelineStageId?: string;
  ruleId: string;
  category: string;
  severity: FindingSeverity;
  title: string;
  description: string;
  pageNumber?: number;
  rowNumber?: number;
  anchorType?: "DOCUMENT_METADATA" | "PAGE_REGION" | "DOCUMENT_HEADER" | "LEDGER_ROW" | "MULTI_PAGE_SPAN" | string;
  anchors?: EvidenceAnchor[];
  expectedValue?: string;
  actualValue?: string;
  discrepancy?: string;
  riskPoints: number;
  isDeterministic?: boolean;
  technicalDetails?: Record<string, any>;
  boundingBoxes?: BoundingBox[];
  createdAt: string;
}

export interface RiskSignal {
  id: string;
  category: string;
  ruleId: string;
  severity: FindingSeverity;
  rawPoints: number;
  weightedPoints: number;
  riskContribution: number;
  isDeterministic: boolean;
}

export type AuthenticityTier = "VERIFIED_AUTHENTIC" | "SUSPECT_DOCUMENT" | "FORGERY_DETECTED";
export type TransactionRiskTier = "CLEAN" | "MONITORED" | "HIGH_AML_RISK" | "CRITICAL_PROSCRIBED";

export interface RiskAssessment {
  id: string;
  investigationId: string;
  overallScore: number;
  riskTier: RiskTier;
  actionDirective: ActionDirective;
  recommendedAction?: string;
  confidenceScore: number;
  isDeterministicOverride: boolean;
  overriddenById?: string;
  overriddenScore?: number;
  overriddenTier?: RiskTier;
  overrideReason?: string;
  overriddenAt?: string;
  computedAt: string;
  riskSignals: RiskSignal[];
  authenticityScore?: number;
  tamperScore?: number;
  authenticityTier?: AuthenticityTier | string;
  transactionRiskScore?: number;
  transactionRiskTier?: TransactionRiskTier | string;
  fusionParameters?: Record<string, unknown>;
}


export interface DocumentPage {
  id: string;
  documentId: string;
  pageNumber: number;
  widthPx: number;
  heightPx: number;
  widthPts: number;
  heightPts: number;
  imageStoragePath: string;
  thumbnailStoragePath?: string;
  renderedImageUrl: string;
}

export interface Document {
  id: string;
  investigationId: string;
  fileName: string;
  fileSize: number;
  mimeType: string;
  sha256Hash: string;
  md5Hash?: string;
  documentType: string;
  pageCount: number;
  processingStatus: string;
  uploadedAt: string;
  pages?: DocumentPage[];
}

export interface PipelineStage {
  id: string;
  stageType: string;
  stageOrder: number;
  status: PipelineStatus;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  errorMessage?: string;
  outputPayload?: Record<string, any>;
}

export interface PipelineRun {
  id: string;
  investigationId: string;
  status: PipelineStatus;
  stagesCount: number;
  stages: PipelineStage[];
  parameters?: Record<string, any>;
  startedAt?: string;
  completedAt?: string;
}

export interface LedgerRow {
  date: string;
  particulars: string;
  debit?: number;
  credit?: number;
  expectedBalance: number;
  recordedBalance: number;
  discrepancy: number;
  isTampered: boolean;
  pageNumber?: number;
  rowType?: string;
  rawLine?: string;
  fontDiscrepancy?: RowTypographyDiscrepancy;
}

export interface RowTypographyDiscrepancy {
  hasAnomaly: boolean;
  fontFamily?: string;
  expectedFont?: string;
  baselineOffsetPts?: number;
  ruleId?: string;
  severity?: FindingSeverity;
  description?: string;
  evidenceItemId?: string;
}

export interface Investigation {
  id: string;
  caseNumber: string;
  title: string;
  notes?: string;
  status: string;
  organizationId: string;
  createdAt: string;
  updatedAt: string;
  documents?: Document[];
  pipelineRuns?: PipelineRun[];
  riskAssessment?: RiskAssessment;
}

export interface RFC3161Seal {
  status: string;
  verified: boolean;
  tsa_provider: string;
  is_pakistan_accredited?: boolean;
  gen_time: string;
  serial_number: string;
  digest_algorithm?: string;
  message_imprint?: string;
  token_storage_path?: string;
  token_b64?: string;
  legal_framework?: string;
  is_offline_local_seal?: boolean;
}

export interface CustodyEvent {
  id: string;
  investigationId: string;
  eventType: string;
  description?: string;
  sha256Hash?: string;
  actor: string;
  ipAddress?: string;
  payload?: Record<string, any>;
  metadata?: {
    rfc3161?: RFC3161Seal;
    [key: string]: any;
  };
  timestamp: string;
}

export interface AgentMessage {
  id: string;
  role: "USER" | "ASSISTANT";
  content: string;
  tokensIn?: number;
  tokensOut?: number;
  sequenceOrder: number;
  createdAt: string;
  evidenceReferences?: string[];
}

export interface AskResponse {
  answer: string;
  agentSessionId: string;
  evidenceReferences: string[];
  tokensUsed: number;
}

export interface AgentSessionInfo {
  id: string;
  agentRole: string;
  modelProvider?: string | null;
  modelName?: string | null;
  totalTokensIn: number;
  totalTokensOut: number;
  totalCostUsd: number;
  status: string;
  startedAt: string;
  completedAt?: string | null;
}

export interface AskHistoryResponse {
  sessionId?: string | null;
  modelProvider?: string | null;
  modelName?: string | null;
  status?: string;
  messages: AgentMessage[];
}

export interface ApiKeyItem {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  created_at: string;
  expires_at?: string | null;
  last_used_at?: string | null;
  is_expired: boolean;
}

export interface ApiKeyCreatedResponse extends ApiKeyItem {
  plaintext_key: string;
}

export interface WebhookEndpointItem {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  description: string | null;
  failure_count: number;
  created_at: string;
  secret?: string;
}

export interface WebhookEndpointCreated extends WebhookEndpointItem {
  secret: string;
}

export interface WebhookDeliveryLog {
  id: string;
  event_type: string;
  http_status_code: number | null;
  attempt: number;
  response_duration_ms: number | null;
  response_body: string | null;
  delivered_at: string | null;
  failed_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface WebhookTestResult {
  success: boolean;
  http_status_code: number | null;
  response_duration_ms: number;
  signature_header: string;
  payload_sent: Record<string, any>;
  response_body: string | null;
  error_message: string | null;
}

export interface OrganizationDetails {
  id: string;
  name: string;
  slug: string;
  subscription_tier: string;
  monthly_doc_limit: number;
  monthly_doc_used: number;
  remaining_docs: number;
  usage_percentage: number;
  domain: string | null;
  settings: Record<string, any> | null;
  billing_cycle_start: string | null;
  days_until_renewal: number;
}

export interface OrganizationUsageStats {
  subscription_tier: string;
  monthly_doc_limit: number;
  monthly_doc_used: number;
  remaining: number;
  usage_percentage: number;
  days_until_renewal: number;
  billing_cycle_start: string | null;
  document_type_breakdown: Record<string, number>;
}

export interface TierUpgradePayload {
  target_tier: "FREE" | "FINTECH_GROWTH" | "BUSINESS_SCALE" | "ENTERPRISE";
}

export interface BillingStatement {
  id: string;
  period: string;
  documents_processed: number;
  allowance: number;
  overage_units: number;
  amount_pkr: number;
  status: "SETTLED" | "PENDING" | "WAIVED";
  issued_at: string;
}

export type OrgUserRole = "OWNER" | "ADMIN" | "ANALYST" | "VIEWER";

export interface OrgMemberItem {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: OrgUserRole;
  is_active: boolean;
  mfa_enabled: boolean;
  failed_login_count: number;
  is_locked: boolean;
  locked_until: string | null;
  last_login_at: string | null;
  created_at: string;
}

export interface InviteUserPayload {
  email: string;
  first_name: string;
  last_name: string;
  role: OrgUserRole;
  temp_password?: string;
}

export interface InviteUserResponse {
  user: OrgMemberItem;
  temp_password: string;
  login_url: string;
  dispatch_memo: string;
}

export interface UpdateRolePayload {
  role: OrgUserRole;
}

export interface UpdateStatusPayload {
  is_active: boolean;
}

export interface UserActionResponse {
  success: boolean;
  message: string;
}

// ── Executive Fraud Analytics & Risk Command Center ──────────────────────────

export interface ScannedDocumentsMetric {
  month_to_date: number;
  monthly_limit: number;
  quota_usage_percentage: number;
  remaining_capacity: number;
  total_lifetime: number;
  days_until_renewal: number;
  tier: string;
}

export interface TamperingDetectionMetric {
  rate_percentage: number;
  critical_count: number;
  high_count: number;
  elevated_count: number;
  moderate_count: number;
  low_count: number;
  total_evaluated: number;
  risk_status: string;
}

export interface FinancialExposureMetric {
  total_prevented_pkr: number;
  total_prevented_formatted: string;
  total_prevented_short: string;
  flagged_cases_count: number;
  average_inflation_pkr: number;
  largest_single_inflation_pkr: number;
}

export interface VerificationLatencyMetric {
  p50_ms: number;
  p95_ms: number;
  p50_formatted: string;
  p95_formatted: string;
  deterministic_p50_ms: number;
  deterministic_formatted: string;
  multi_page_ocr_p95_ms: number;
  multi_page_ocr_formatted: string;
  stage_latencies: Record<string, number>;
}

export interface CriticalAlertItem {
  id: string;
  case_number: string;
  title: string;
  document_type: string;
  risk_score: number | null;
  risk_tier: string;
  action_directive: string;
  prevented_rupees: number | null;
  prevented_rupees_formatted: string | null;
  client_reference: string | null;
  created_at: string;
}

export interface DashboardMetrics {
  organization_id: string;
  organization_name: string;
  tenant_slug: string;
  total_scanned: ScannedDocumentsMetric;
  tampering_detection: TamperingDetectionMetric;
  financial_exposure: FinancialExposureMetric;
  verification_latency: VerificationLatencyMetric;
  recent_critical_alerts: CriticalAlertItem[];
  document_type_distribution: Record<string, number>;
  generated_at: string;
}

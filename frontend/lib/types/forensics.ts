export type RiskTier = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ActionDirective =
  | "STRAIGHT_THROUGH_APPROVAL"
  | "MANUAL_SUPERVISOR_REVIEW"
  | "ENHANCED_DUE_DILIGENCE"
  | "IMMEDIATE_REJECTION";

export type PipelineStatus =
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type FindingSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

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
}

export interface EvidenceItem {
  id: string;
  documentId: string;
  pipelineStageId: string;
  category: string;
  severity: FindingSeverity;
  ruleId: string;
  riskPoints: number;
  title: string;
  description: string;
  isDeterministic: boolean;
  pageNumber?: number;
  expectedValue?: string;
  actualValue?: string;
  discrepancy?: string;
  technicalDetails?: Record<string, any>;
  boundingBoxes: BoundingBox[];
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

export interface RiskAssessment {
  id: string;
  investigationId: string;
  overallScore: number;
  riskTier: RiskTier;
  actionDirective: ActionDirective;
  confidenceScore: number;
  isDeterministicOverride: boolean;
  overriddenById?: string;
  overriddenScore?: number;
  overriddenTier?: RiskTier;
  overrideReason?: string;
  overriddenAt?: string;
  computedAt: string;
  riskSignals: RiskSignal[];
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




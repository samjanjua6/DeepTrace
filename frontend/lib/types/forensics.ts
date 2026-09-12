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

export interface CustodyEvent {
  id: string;
  investigationId: string;
  eventType: string;
  actor: string;
  ipAddress?: string;
  payload?: Record<string, any>;
  timestamp: string;
}

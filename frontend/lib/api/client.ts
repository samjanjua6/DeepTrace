import {
  Investigation,
  Document,
  DocumentPage,
  EvidenceItem,
  RiskAssessment,
  PipelineRun,
  CustodyEvent,
  AgentMessage,
  AskResponse,
  AgentSessionInfo,
  AskHistoryResponse,
  ApiKeyItem,
  ApiKeyCreatedResponse,
  WebhookEndpointItem,
  WebhookEndpointCreated,
  WebhookDeliveryLog,
  WebhookTestResult,
  OrganizationDetails,
  OrganizationUsageStats,
  OrgMemberItem,
  InviteUserPayload,
  InviteUserResponse,
  UserActionResponse,
  OrgUserRole,
  DashboardMetrics,
} from "../types/forensics";

const API_BASE = "/api/v1";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  mfa_required?: boolean;
  temp_token?: string;
  message?: string;
}

export interface UserProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  organization_id: string;
  mfa_enabled: boolean;
  organization_name?: string;
  organization_slug?: string;
}

export interface OrganizationOption {
  id: string;
  name: string;
  slug: string;
  domain?: string;
  subscription_tier?: string;
}

export interface SsoProviderOption {
  id: string;
  name: string;
  protocol: string;
  description: string;
}

export interface SsoInitiateResponse {
  provider: string;
  sso_url: string;
  entity_id: string;
  protocol: string;
  message: string;
}

let authToken: string | null = null;
let refreshPromise: Promise<TokenResponse | null> | null = null;

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== "undefined") {
    authToken =
      sessionStorage.getItem("deeptrace_access_token") ||
      localStorage.getItem("deeptrace_access_token");
  }
  return authToken;
}

export function getStoredRefreshToken(): string | null {
  if (typeof window !== "undefined") {
    return (
      sessionStorage.getItem("deeptrace_refresh_token") ||
      localStorage.getItem("deeptrace_refresh_token")
    );
  }
  return null;
}

export function setAuthToken(token: string, rememberDevice: boolean = true) {
  authToken = token;
  if (typeof window !== "undefined") {
    if (rememberDevice) {
      localStorage.setItem("deeptrace_access_token", token);
      sessionStorage.removeItem("deeptrace_access_token");
    } else {
      sessionStorage.setItem("deeptrace_access_token", token);
      localStorage.removeItem("deeptrace_access_token");
    }
  }
}

export function setAuthTokens(
  access: string,
  refresh?: string,
  rememberDevice: boolean = true
) {
  authToken = access;
  if (typeof window !== "undefined") {
    if (rememberDevice) {
      localStorage.setItem("deeptrace_access_token", access);
      if (refresh) localStorage.setItem("deeptrace_refresh_token", refresh);
      sessionStorage.removeItem("deeptrace_access_token");
      sessionStorage.removeItem("deeptrace_refresh_token");
    } else {
      sessionStorage.setItem("deeptrace_access_token", access);
      if (refresh) sessionStorage.setItem("deeptrace_refresh_token", refresh);
      localStorage.removeItem("deeptrace_access_token");
      localStorage.removeItem("deeptrace_refresh_token");
    }
  }
}

export function clearAuthTokens() {
  authToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("deeptrace_access_token");
    localStorage.removeItem("deeptrace_refresh_token");
    localStorage.removeItem("deeptrace_user");
    sessionStorage.removeItem("deeptrace_access_token");
    sessionStorage.removeItem("deeptrace_refresh_token");
    sessionStorage.removeItem("deeptrace_user");
  }
}

export function getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  const token = getAuthToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function refreshSession(): Promise<TokenResponse | null> {
  const refresh = getStoredRefreshToken();
  if (!refresh) {
    clearAuthTokens();
    return null;
  }
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) {
          clearAuthTokens();
          return null;
        }
        const data: TokenResponse = await res.json();
        setAuthTokens(data.access_token, data.refresh_token);
        return data;
      } catch {
        clearAuthTokens();
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const token = getAuthToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    // Attempt session refresh once
    const refreshed = await refreshSession();
    if (refreshed?.access_token) {
      headers.set("Authorization", `Bearer ${refreshed.access_token}`);
      res = await fetch(url, { ...options, headers });
    }
  }

  return res;
}

export async function loginUser(req: {
  email: string;
  password: string;
  mfa_code?: string;
  remember_me?: boolean;
}): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const message =
      err.error?.message || err.detail?.message || err.detail || `Authentication failed (${res.status})`;
    throw new Error(message);
  }

  const data: TokenResponse = await res.json();
  if (!data.mfa_required && data.access_token) {
    setAuthTokens(data.access_token, data.refresh_token, req.remember_me ?? true);
  }
  return data;
}

export async function verifyMfaLogin(
  tempToken: string,
  mfaCode: string,
  rememberMe: boolean = true
): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/mfa/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ temp_token: tempToken, mfa_code: mfaCode, remember_me: rememberMe }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const message =
      err.error?.message || err.detail?.message || err.detail || `2FA verification failed (${res.status})`;
    throw new Error(message);
  }

  const data: TokenResponse = await res.json();
  if (data.access_token) {
    setAuthTokens(data.access_token, data.refresh_token, rememberMe);
  }
  return data;
}

export async function getSsoProviders(): Promise<SsoProviderOption[]> {
  const res = await fetch(`${API_BASE}/auth/sso/providers`);
  if (!res.ok) return [];
  return res.json();
}

export async function initiateSso(req: {
  provider: string;
  tenant_domain?: string;
  redirect_uri?: string;
}): Promise<SsoInitiateResponse> {
  const res = await fetch(`${API_BASE}/auth/sso/initiate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    throw new Error("Failed to initiate enterprise SSO federation");
  }
  return res.json();
}


export async function loginAnalyst(
  username?: string,
  password?: string,
  mfaCode?: string
): Promise<string> {
  if (!username || !password) {
    // Return existing token if available
    const existing = getAuthToken();
    if (existing) return existing;
    throw new Error("Credentials required for authentication.");
  }
  const data = await loginUser({ email: username, password, mfa_code: mfaCode });
  return data.access_token;
}

export async function getCurrentUser(): Promise<UserProfile> {
  const res = await fetchWithAuth(`${API_BASE}/auth/me`);
  if (!res.ok) throw new Error("Failed to fetch user profile");
  return res.json();
}

export async function getOrganizations(): Promise<OrganizationOption[]> {
  const res = await fetchWithAuth(`${API_BASE}/auth/organizations`);
  if (!res.ok) throw new Error("Failed to fetch organizations");
  return res.json();
}

export async function switchOrganization(
  organizationId: string
): Promise<{ access_token: string; refresh_token: string; organization: OrganizationOption }> {
  const res = await fetchWithAuth(`${API_BASE}/auth/switch-org`, {
    method: "POST",
    body: JSON.stringify({ organization_id: organizationId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || "Failed to switch organization");
  }
  const data = await res.json();
  if (data.access_token && data.refresh_token) {
    setAuthTokens(data.access_token, data.refresh_token);
  }
  return data;
}

export async function logoutUser(): Promise<void> {
  const refresh = getStoredRefreshToken();
  if (refresh) {
    await fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    }).catch(() => {});
  }
  clearAuthTokens();
}

export async function setupMfa(): Promise<{ secret: string; otpauth_uri: string }> {
  const res = await fetchWithAuth(`${API_BASE}/auth/mfa/setup`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || "Failed to initialize 2FA setup");
  }
  return res.json();
}

export async function enableMfa(secret: string, code: string): Promise<void> {
  const res = await fetchWithAuth(`${API_BASE}/auth/mfa/enable`, {
    method: "POST",
    body: JSON.stringify({ secret, code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || "Invalid authenticator code");
  }
}

export async function disableMfa(password: string, code: string): Promise<void> {
  const res = await fetchWithAuth(`${API_BASE}/auth/mfa/disable`, {
    method: "POST",
    body: JSON.stringify({ password, code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || "Failed to disable 2FA. Verify password and code.");
  }
}

export async function ensureAuth(): Promise<string> {
  const token = getAuthToken();
  if (token) return token;
  const refreshed = await refreshSession();
  return refreshed?.access_token || "";
}

// ── Investigations ────────────────────────────────────────────────────────────

export async function getInvestigations(): Promise<Investigation[]> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/investigations`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch investigations");
  const list = await res.json();
  return (list || []).map((data: any) => ({
    id: data.id,
    caseNumber: data.case_number || data.caseNumber || "",
    title: data.title || "",
    notes: data.description || data.notes || "",
    status: data.status,
    organizationId: data.organization_id || data.organizationId || "",
    createdAt: data.created_at || data.createdAt,
    updatedAt: data.updated_at || data.updatedAt,
  }));
}

export async function getInvestigation(id: string): Promise<Investigation> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/investigations/${id}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch investigation ${id}`);
  const data = await res.json();
  return {
    id: data.id,
    caseNumber: data.case_number || data.caseNumber || "",
    title: data.title || "",
    notes: data.description || data.notes || "",
    status: data.status,
    organizationId: data.organization_id || data.organizationId || "",
    createdAt: data.created_at || data.createdAt,
    updatedAt: data.updated_at || data.updatedAt,
  };
}

export async function createInvestigation(data: {
  title: string;
  case_number?: string;
  notes?: string;
}): Promise<Investigation> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/investigations`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      title: data.title,
      description: data.notes || data.title,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create investigation");
  }
  const ret = await res.json();
  return {
    id: ret.id,
    caseNumber: ret.case_number || ret.caseNumber || "",
    title: ret.title || "",
    notes: ret.description || ret.notes || "",
    status: ret.status,
    organizationId: ret.organization_id || ret.organizationId || "",
    createdAt: ret.created_at || ret.createdAt,
    updatedAt: ret.updated_at || ret.updatedAt,
  };
}

// ── Documents ─────────────────────────────────────────────────────────────────

export async function getDocuments(investigationId: string): Promise<Document[]> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/investigations/${investigationId}/documents`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch documents");
  const raw = await res.json();
  return (raw || []).map((d: any) => ({
    id: d.id,
    investigationId: d.investigation_id || d.investigationId || investigationId,
    fileName: d.original_filename || d.fileName || "",
    fileSize: d.file_size_bytes || d.fileSize || 0,
    mimeType: d.mime_type || d.mimeType || "application/pdf",
    sha256Hash: d.sha256_hash || d.sha256Hash || "",
    md5Hash: d.md5_hash || d.md5Hash,
    documentType: d.document_type || d.documentType || "OTHER",
    pageCount: d.page_count ?? d.pageCount ?? 1,
    processingStatus: d.processing_status || d.processingStatus || "UPLOADED",
    uploadedAt: d.created_at || d.createdAt || new Date().toISOString(),
  }));
}

export async function uploadDocument(
  investigationId: string,
  file: File,
  documentType = "BANK_STATEMENT"
): Promise<Document> {
  await ensureAuth().catch(() => {});
  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_type", documentType);

  const headers: HeadersInit = {};
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/documents`,
    {
      method: "POST",
      headers,
      body: formData,
    }
  );

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Upload failed with status ${res.status}`
    );
  }
  const d = await res.json();
  return {
    id: d.id,
    investigationId: d.investigation_id || d.investigationId || investigationId,
    fileName: d.original_filename || d.fileName || "",
    fileSize: d.file_size_bytes || d.fileSize || 0,
    mimeType: d.mime_type || d.mimeType || "application/pdf",
    sha256Hash: d.sha256_hash || d.sha256Hash || "",
    md5Hash: d.md5_hash || d.md5Hash,
    documentType: d.document_type || d.documentType || "OTHER",
    pageCount: d.page_count ?? d.pageCount ?? 1,
    processingStatus: d.processing_status || d.processingStatus || "UPLOADED",
    uploadedAt: d.created_at || d.createdAt || new Date().toISOString(),
  };
}

export async function getDocumentPages(
  investigationId: string,
  documentId: string
): Promise<DocumentPage[]> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/documents/${documentId}/pages`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) throw new Error("Failed to fetch document pages");
  const pages = await res.json();
  return (pages || []).map((p: any) => ({
    id: p.id,
    documentId: p.document_id || p.documentId || documentId,
    pageNumber: p.page_number ?? p.pageNumber ?? 1,
    widthPx: p.width_px ?? p.widthPx ?? 1240,
    heightPx: p.height_px ?? p.heightPx ?? 1755,
    widthPts: p.width_pts ?? p.widthPts ?? 595,
    heightPts: p.height_pts ?? p.heightPts ?? 842,
    imageStoragePath: p.rendered_image_path || p.imageStoragePath || "",
    thumbnailStoragePath: p.thumbnail_storage_path || p.thumbnailStoragePath,
    renderedImageUrl:
      p.rendered_image_url ||
      p.renderedImageUrl ||
      `/api/v1/storage/deeptrace-documents/${p.rendered_image_path || p.imageStoragePath}`,
  }));
}

export async function getCustodyEvents(
  investigationId: string
): Promise<CustodyEvent[]> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/custody`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) throw new Error("Failed to fetch custody events");
  const events = await res.json();
  return (events || []).map((e: any) => ({
    id: e.id,
    investigationId: e.investigation_id || e.investigationId || investigationId,
    eventType: e.event_type || e.eventType || "",
    description: e.description || "",
    sha256Hash: e.sha256_hash || e.sha256Hash,
    actor: e.actor_id || e.actorId || e.actor || e.actor_type || "system",
    ipAddress: e.ip_address || e.ipAddress,
    payload: e.metadata || e.payload,
    metadata: e.metadata || e.payload,
    timestamp: e.timestamp || e.created_at || new Date().toISOString(),
  }));
}

export async function downloadRFC3161Token(
  investigationId: string,
  eventId: string
): Promise<Blob> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/custody/${eventId}/rfc3161-token`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) throw new Error("Failed to download RFC 3161 token");
  return await res.blob();
}

export async function verifyRFC3161Token(
  investigationId: string,
  eventId: string
): Promise<any> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/custody/${eventId}/rfc3161-verify`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) throw new Error("Failed to verify RFC 3161 token");
  return await res.json();
}

// ── Pipeline Orchestration ────────────────────────────────────────────────────

export async function triggerPipeline(
  investigationId: string,
  documentId?: string
): Promise<PipelineRun> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/analyze`,
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(documentId ? { document_id: documentId } : {}),
    }
  );
  if (!res.ok) throw new Error("Failed to trigger pipeline");
  const data = await res.json();
  return {
    id: data.id,
    investigationId: data.investigation_id || data.investigationId || investigationId,
    status: data.status,
    stagesCount: (data.stages || []).length,
    stages: (data.stages || []).map((s: any) => ({
      id: s.id,
      stageType: s.stage_type || s.stageType,
      stageOrder: s.stage_order ?? s.stageOrder,
      status: s.status,
      durationMs: s.duration_ms ?? s.durationMs,
      errorMessage: s.error_message || s.errorMessage,
      outputPayload: s.output_payload || s.outputPayload,
    })),
  };
}

export async function getPipelineStatus(
  investigationId: string
): Promise<PipelineRun> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/pipeline`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) throw new Error("Failed to fetch pipeline status");
  const data = await res.json();
  return {
    id: data.id,
    investigationId: data.investigation_id || data.investigationId || investigationId,
    status: data.status,
    stagesCount: (data.stages || []).length,
    stages: (data.stages || []).map((s: any) => ({
      id: s.id,
      stageType: s.stage_type || s.stageType,
      stageOrder: s.stage_order ?? s.stageOrder,
      status: s.status,
      durationMs: s.duration_ms ?? s.durationMs,
      errorMessage: s.error_message || s.errorMessage,
      outputPayload: s.output_payload || s.outputPayload,
    })),
  };
}

// ── Evidence & Risk ───────────────────────────────────────────────────────────

export async function getEvidence(
  investigationId: string
): Promise<EvidenceItem[]> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/evidence`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) throw new Error("Failed to fetch evidence items");
  const raw = await res.json();
  return (raw || []).map((item: any) => ({
    id: item.id,
    documentId: item.document_id || item.documentId || "",
    pipelineStageId: item.pipeline_stage_id || item.pipelineStageId || "",
    category: item.category || "GENERAL",
    severity: item.severity || "LOW",
    ruleId: item.rule_id || item.ruleId || "",
    riskPoints: item.risk_points ?? item.riskPoints ?? 0,
    title: item.title || "",
    description: item.description || "",
    isDeterministic: item.is_deterministic ?? item.isDeterministic ?? false,
    pageNumber: item.page_number ?? item.pageNumber,
    expectedValue: item.expected_value || item.expectedValue,
    actualValue: item.actual_value || item.actualValue,
    discrepancy: item.discrepancy,
    technicalDetails: item.technical_details || item.technicalDetails,
    boundingBoxes: (item.bounding_boxes || item.boundingBoxes || []).map((b: any) => ({
      id: b.id,
      evidenceItemId: b.evidence_item_id || b.evidenceItemId || item.id,
      pageNumber: b.page_number ?? b.pageNumber ?? 1,
      x: b.x,
      y: b.y,
      width: b.width,
      height: b.height,
      xPts: b.x_pts ?? b.xPts,
      yPts: b.y_pts ?? b.yPts,
      widthPts: b.width_pts ?? b.widthPts,
      heightPts: b.height_pts ?? b.heightPts,
      label: b.label,
      color: b.color,
    })),
    createdAt: item.created_at || item.createdAt || new Date().toISOString(),
  }));
}

export async function getRiskAssessment(
  investigationId: string
): Promise<RiskAssessment> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/risk`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) throw new Error("Failed to fetch risk assessment");
  const r = await res.json();
  return {
    id: r.id,
    investigationId: r.investigation_id || r.investigationId || investigationId,
    overallScore: r.overall_score ?? r.overallScore ?? 0,
    riskTier: r.risk_tier || r.riskTier || "LOW",
    actionDirective: r.action_directive || r.actionDirective || "STRAIGHT_THROUGH_APPROVAL",
    confidenceScore: r.confidence_score ?? r.confidenceScore ?? 1.0,
    isDeterministicOverride: r.is_deterministic_override ?? r.isDeterministicOverride ?? false,
    overriddenScore: r.overridden_score ?? r.overriddenScore,
    overriddenTier: r.overridden_tier || r.overriddenTier,
    overrideReason: r.override_reason || r.overrideReason,
    computedAt: r.computed_at || r.computedAt || new Date().toISOString(),
    riskSignals: (r.risk_signals || r.riskSignals || []).map((s: any) => ({
      id: s.id || s.signal_category || s.signalCategory || "signal",
      category: s.signal_category || s.signalCategory || "GENERAL",
      ruleId: s.rule_id || s.ruleId || s.signal_category || "",
      severity: s.severity || "LOW",
      rawPoints: s.raw_score ?? s.rawScore ?? s.rawPoints ?? 0,
      weightedPoints: s.weighted_score ?? s.weightedScore ?? s.weightedPoints ?? 0,
      riskContribution: s.weighted_score ?? s.weightedScore ?? 0,
      isDeterministic: s.is_deterministic ?? s.isDeterministic ?? false,
    })),
  };
}

export async function overrideRiskScore(
  investigationId: string,
  score: number,
  reason: string
): Promise<RiskAssessment> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/risk/override`,
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ score, reason }),
    }
  );
  if (!res.ok) throw new Error("Failed to override risk score");
  return res.json();
}

export async function getLeadInvestigatorAnalysis(
  investigationId: string
): Promise<any> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/analysis`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) throw new Error("Failed to fetch Lead Investigator analysis");
  return res.json();
}

export async function askAgentStream(
  investigationId: string,
  question: string,
  onChunk: (chunk: string) => void
): Promise<AskResponse> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/investigations/${investigationId}/ask`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
      Accept: "text/event-stream, application/json",
    },
    body: JSON.stringify({ question, stream: true }),
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => "");
    throw new Error(`Failed to consult Lead Investigator: ${res.status} ${errText}`);
  }

  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json") || !res.body) {
    const data = await res.json();
    const answer = data.answer || "";
    onChunk(answer);
    return {
      answer,
      agentSessionId: data.agent_session_id || "",
      evidenceReferences: data.evidence_references || [],
      tokensUsed: data.tokens_used || 0,
    };
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let fullAnswer = "";
  let finalResult: Partial<AskResponse> = {};

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const jsonStr = trimmed.replace(/^data:\s*/, "");
      if (!jsonStr) continue;

      try {
        const payload = JSON.parse(jsonStr);
        if (payload.chunk) {
          fullAnswer += payload.chunk;
          onChunk(payload.chunk);
        }
        if (payload.done) {
          finalResult = {
            answer: payload.answer || fullAnswer,
            agentSessionId: payload.agent_session_id || "",
            evidenceReferences: payload.evidence_references || [],
            tokensUsed: payload.tokens_used || 0,
          };
        }
      } catch {
        // Ignore partial JSON parse errors
      }
    }
  }

  return {
    answer: finalResult.answer || fullAnswer,
    agentSessionId: finalResult.agentSessionId || "",
    evidenceReferences: finalResult.evidenceReferences || [],
    tokensUsed: finalResult.tokensUsed || 0,
  };
}

export async function askAgent(
  investigationId: string,
  question: string
): Promise<AskResponse> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/investigations/${investigationId}/ask`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question, stream: false }),
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => "");
    throw new Error(`Failed to consult Lead Investigator: ${res.status} ${errText}`);
  }
  const data = await res.json();
  return {
    answer: data.answer,
    agentSessionId: data.agent_session_id,
    evidenceReferences: data.evidence_references || [],
    tokensUsed: data.tokens_used || 0,
  };
}

export async function getAgentChatHistory(
  investigationId: string
): Promise<AskHistoryResponse> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/ask/history`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) {
    return { messages: [] };
  }
  const data = await res.json();
  return {
    sessionId: data.session_id,
    modelProvider: data.model_provider,
    modelName: data.model_name,
    status: data.status,
    messages: (data.messages || []).map((m: any) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      tokensIn: m.tokens_in ?? m.tokensIn ?? 0,
      tokensOut: m.tokens_out ?? m.tokensOut ?? 0,
      sequenceOrder: m.sequence_order ?? m.sequenceOrder ?? 0,
      createdAt: m.created_at || m.createdAt || new Date().toISOString(),
    })),
  };
}

export async function getAgentSessions(
  investigationId: string
): Promise<AgentSessionInfo[]> {
  await ensureAuth().catch(() => {});
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/agents`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) return [];
  const sessions = await res.json();
  return (sessions || []).map((s: any) => ({
    id: s.id,
    agentRole: s.agent_role || s.agentRole,
    modelProvider: s.model_provider || s.modelProvider,
    modelName: s.model_name || s.modelName,
    totalTokensIn: s.total_tokens_in ?? s.totalTokensIn ?? 0,
    totalTokensOut: s.total_tokens_out ?? s.totalTokensOut ?? 0,
    totalCostUsd: s.total_cost_usd ?? s.totalCostUsd ?? 0,
    status: s.status,
    startedAt: s.started_at || s.startedAt,
    completedAt: s.completed_at || s.completedAt,
  }));
}

export async function getApiKeys(includeRevoked: boolean = false): Promise<ApiKeyItem[]> {
  await ensureAuth().catch(() => {});
  const query = includeRevoked ? "?include_revoked=true" : "";
  const res = await fetch(`${API_BASE}/api-keys${query}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    if (res.status === 403) {
      throw new Error("403 Forbidden: Insufficient permissions. Admin access required.");
    }
    throw new Error(`Failed to fetch API keys: ${res.statusText}`);
  }
  return res.json();
}

export async function createApiKey(payload: {
  name: string;
  scopes: string[];
  expires_in_days?: number | null;
}): Promise<ApiKeyCreatedResponse> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/api-keys`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to create API key";
    throw new Error(message);
  }
  return res.json();
}

export async function revokeApiKey(keyId: string): Promise<void> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/api-keys/${keyId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to revoke API key";
    throw new Error(message);
  }
}

export async function getWebhooks(): Promise<WebhookEndpointItem[]> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/webhooks`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    if (res.status === 403) {
      throw new Error("403 Forbidden: Insufficient permissions. Admin access required.");
    }
    throw new Error(`Failed to fetch webhooks: ${res.statusText}`);
  }
  return res.json();
}

export async function createWebhook(payload: {
  url: string;
  events: string[];
  description?: string;
}): Promise<WebhookEndpointCreated> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/webhooks`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to register webhook endpoint";
    throw new Error(message);
  }
  return res.json();
}

export async function deleteWebhook(endpointId: string): Promise<void> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/webhooks/${endpointId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to deactivate webhook endpoint";
    throw new Error(message);
  }
}

export async function getWebhookSecret(endpointId: string): Promise<string> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/webhooks/${endpointId}/secret`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch webhook secret: ${res.statusText}`);
  }
  const data = await res.json();
  return data.secret;
}

export async function getWebhookDeliveries(endpointId: string): Promise<WebhookDeliveryLog[]> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/webhooks/${endpointId}/deliveries`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch webhook delivery history: ${res.statusText}`);
  }
  return res.json();
}

export async function testWebhookEndpoint(
  endpointId: string,
  eventType: string = "test.ping"
): Promise<WebhookTestResult> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/webhooks/${endpointId}/test`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ event_type: eventType }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Test ping failed";
    throw new Error(message);
  }
  return res.json();
}

export async function getOrganization(): Promise<OrganizationDetails> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/org`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to fetch organization details";
    throw new Error(message);
  }
  return res.json();
}

export async function getOrganizationUsage(): Promise<OrganizationUsageStats> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/org/usage`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to fetch organization usage statistics";
    throw new Error(message);
  }
  return res.json();
}

export async function updateOrganizationSettings(payload: {
  name?: string;
  domain?: string;
  settings?: Record<string, any>;
}): Promise<OrganizationDetails> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/org/settings`, {
    method: "PATCH",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to update organization settings";
    throw new Error(message);
  }
  return res.json();
}

export async function upgradeSubscriptionTier(targetTier: string): Promise<OrganizationDetails> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/org/tier`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ target_tier: targetTier }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to update subscription tier";
    throw new Error(message);
  }
  return res.json();
}

export async function getOrgUsers(): Promise<OrgMemberItem[]> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/users`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to retrieve organization member roster";
    throw new Error(message);
  }
  return res.json();
}

export async function inviteOrgUser(payload: InviteUserPayload): Promise<InviteUserResponse> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/users/invite`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to generate credential dispatch memo";
    throw new Error(message);
  }
  return res.json();
}

export async function updateUserRole(userId: string, role: OrgUserRole): Promise<OrgMemberItem> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/users/${userId}/role`, {
    method: "PATCH",
    headers: getAuthHeaders(),
    body: JSON.stringify({ role }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to update member role";
    throw new Error(message);
  }
  return res.json();
}

export async function updateUserStatus(userId: string, isActive: boolean): Promise<OrgMemberItem> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/users/${userId}/status`, {
    method: "PATCH",
    headers: getAuthHeaders(),
    body: JSON.stringify({ is_active: isActive }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to update member active status";
    throw new Error(message);
  }
  return res.json();
}

export async function unlockUserAccount(userId: string): Promise<UserActionResponse> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/users/${userId}/unlock`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to unlock account";
    throw new Error(message);
  }
  return res.json();
}

export async function resetUserMfa(userId: string): Promise<UserActionResponse> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/users/${userId}/reset-mfa`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to reset two-factor authentication";
    throw new Error(message);
  }
  return res.json();
}

export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  await ensureAuth().catch(() => {});
  const res = await fetch(`${API_BASE}/analytics/dashboard`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message =
      errorData?.detail?.message ||
      errorData?.error?.message ||
      errorData?.message ||
      "Failed to fetch executive fraud analytics metrics";
    throw new Error(message);
  }
  return res.json();
}






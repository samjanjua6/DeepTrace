import {
  Investigation,
  Document,
  DocumentPage,
  EvidenceItem,
  RiskAssessment,
  PipelineRun,
  CustodyEvent,
} from "../types/forensics";

const API_BASE = "/api/v1";

let authToken: string | null = null;
let authPromise: Promise<string> | null = null;

export function setAuthToken(token: string) {
  authToken = token;
}

export function getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  return headers;
}

export async function loginAnalyst(
  username = "analyst@meezan.pk",
  password = "Analyst@12345"
): Promise<string> {
  if (authToken) return authToken;

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: username,
      password: password,
    }),
  });

  if (!res.ok) {
    // Also try /token endpoint as fallback
    const formRes = await fetch(`${API_BASE}/auth/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: username,
        password: password,
      }),
    });
    if (!formRes.ok) {
      throw new Error(`Authentication failed with status ${res.status}`);
    }
    const data = await formRes.json();
    setAuthToken(data.access_token);
    return data.access_token;
  }

  const data = await res.json();
  const token = data.access_token;
  setAuthToken(token);
  return token;
}

export async function ensureAuth(): Promise<string> {
  if (authToken) return authToken;
  if (!authPromise) {
    authPromise = loginAnalyst().finally(() => {
      authPromise = null;
    });
  }
  return authPromise;
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


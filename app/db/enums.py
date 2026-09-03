"""
DeepTrace — Python Enum Mirrors for Prisma Enums

These Python enums mirror the Prisma schema enums exactly.
Use these in FastAPI route handlers, Pydantic models, and service logic
instead of raw strings to maintain type safety.

All values must stay in sync with prisma/schema.prisma.
"""

from enum import Enum


# =============================================================================
# Domain 1: Identity & Multi-Tenancy
# =============================================================================


class UserRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"
    API_SERVICE = "API_SERVICE"


class SubscriptionTier(str, Enum):
    FREE = "FREE"
    FINTECH_GROWTH = "FINTECH_GROWTH"
    BUSINESS_SCALE = "BUSINESS_SCALE"
    ENTERPRISE = "ENTERPRISE"

    @property
    def monthly_doc_limit(self) -> int:
        """Returns the default monthly document limit for this tier."""
        limits = {
            self.FREE: 100,
            self.FINTECH_GROWTH: 2_000,
            self.BUSINESS_SCALE: 15_000,
            self.ENTERPRISE: -1,  # Unlimited
        }
        return limits[self]


# =============================================================================
# Domain 2: Investigation Core
# =============================================================================


class InvestigationStatus(str, Enum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    REVIEWED = "REVIEWED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        """True if the investigation cannot transition to another state."""
        return self in {self.CLOSED, self.ARCHIVED, self.FAILED}

    @property
    def is_active(self) -> bool:
        """True if the investigation is currently being worked on."""
        return self in {
            self.CREATED,
            self.UPLOADING,
            self.QUEUED,
            self.PROCESSING,
            self.AWAITING_REVIEW,
        }


class DocumentType(str, Enum):
    BANK_STATEMENT = "BANK_STATEMENT"
    SALARY_SLIP = "SALARY_SLIP"
    UTILITY_BILL = "UTILITY_BILL"
    TAX_CERTIFICATE = "TAX_CERTIFICATE"
    IDENTITY_DOCUMENT = "IDENTITY_DOCUMENT"
    COMMERCIAL_INVOICE = "COMMERCIAL_INVOICE"
    DIGITAL_WALLET_LEDGER = "DIGITAL_WALLET_LEDGER"
    OTHER = "OTHER"


class DocumentSource(str, Enum):
    WEB_UPLOAD = "WEB_UPLOAD"
    API_UPLOAD = "API_UPLOAD"
    BATCH_IMPORT = "BATCH_IMPORT"
    EMAIL_INGESTION = "EMAIL_INGESTION"


# =============================================================================
# Domain 3: Forensic Pipeline Execution
# =============================================================================


class PipelineStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"

    @property
    def is_terminal(self) -> bool:
        return self in {self.COMPLETED, self.FAILED, self.CANCELLED, self.TIMED_OUT}


class PipelineStageType(str, Enum):
    CUSTODY_LOCK = "CUSTODY_LOCK"
    PDF_STRUCTURE = "PDF_STRUCTURE"
    FONT_GLYPH_ANALYSIS = "FONT_GLYPH_ANALYSIS"
    VISION_ELA = "VISION_ELA"
    OCR_EXTRACTION = "OCR_EXTRACTION"
    FINANCIAL_VERIFICATION = "FINANCIAL_VERIFICATION"
    EVIDENCE_FUSION = "EVIDENCE_FUSION"
    REPORT_GENERATION = "REPORT_GENERATION"

    @property
    def order(self) -> int:
        """Returns the canonical execution order (1-indexed)."""
        ordering = {
            self.CUSTODY_LOCK: 1,
            self.PDF_STRUCTURE: 2,
            self.FONT_GLYPH_ANALYSIS: 3,
            self.VISION_ELA: 4,
            self.OCR_EXTRACTION: 5,
            self.FINANCIAL_VERIFICATION: 6,
            self.EVIDENCE_FUSION: 7,
            self.REPORT_GENERATION: 8,
        }
        return ordering[self]

    @property
    def display_name(self) -> str:
        names = {
            self.CUSTODY_LOCK: "Evidence Acquisition & Custody",
            self.PDF_STRUCTURE: "PDF Structural & Metadata Forensics",
            self.FONT_GLYPH_ANALYSIS: "Font & Glyph Micro-Analysis",
            self.VISION_ELA: "Computer Vision & ELA Heatmaps",
            self.OCR_EXTRACTION: "OCR & Semantic Topology",
            self.FINANCIAL_VERIFICATION: "Deterministic Financial Verification",
            self.EVIDENCE_FUSION: "Multi-Signal Evidence Fusion",
            self.REPORT_GENERATION: "Forensic Dossier Generation",
        }
        return names[self]


# =============================================================================
# Domain 4: Evidence & Forensic Findings
# =============================================================================


class EvidenceSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def risk_weight(self) -> float:
        """Relative weight used in Bayesian evidence fusion."""
        weights = {
            self.INFO: 0.0,
            self.LOW: 0.25,
            self.MEDIUM: 0.5,
            self.HIGH: 0.75,
            self.CRITICAL: 1.0,
        }
        return weights[self]

    @property
    def ui_color(self) -> str:
        """Hex color for workbench UI overlays."""
        colors = {
            self.INFO: "#64748b",
            self.LOW: "#3b82f6",
            self.MEDIUM: "#f59e0b",
            self.HIGH: "#ef4444",
            self.CRITICAL: "#b91c1c",
        }
        return colors[self]


class EvidenceCategory(str, Enum):
    MATHEMATICAL_MISMATCH = "MATHEMATICAL_MISMATCH"
    IMAGE_ELA_MANIPULATION = "IMAGE_ELA_MANIPULATION"
    FONT_BASELINE_INCONSISTENCY = "FONT_BASELINE_INCONSISTENCY"
    PDF_OBJECT_ANOMALY = "PDF_OBJECT_ANOMALY"
    METADATA_TIMESTAMP_MISMATCH = "METADATA_TIMESTAMP_MISMATCH"
    IBAN_CHECKSUM_FAILURE = "IBAN_CHECKSUM_FAILURE"
    AI_GENERATION_ARTIFACT = "AI_GENERATION_ARTIFACT"
    OCR_CONFIDENCE_ANOMALY = "OCR_CONFIDENCE_ANOMALY"
    DATE_SEQUENCE_VIOLATION = "DATE_SEQUENCE_VIOLATION"
    TRANSACTION_FORMAT_VIOLATION = "TRANSACTION_FORMAT_VIOLATION"
    UTILITY_BILL_ANOMALY = "UTILITY_BILL_ANOMALY"
    SALARY_CALCULATION_MISMATCH = "SALARY_CALCULATION_MISMATCH"

    @property
    def max_risk_points(self) -> int:
        """Maximum risk points this category can contribute (from proposal §5.2)."""
        points = {
            self.MATHEMATICAL_MISMATCH: 20,
            self.IMAGE_ELA_MANIPULATION: 20,
            self.FONT_BASELINE_INCONSISTENCY: 15,
            self.PDF_OBJECT_ANOMALY: 15,
            self.METADATA_TIMESTAMP_MISMATCH: 10,
            self.IBAN_CHECKSUM_FAILURE: 10,
            self.AI_GENERATION_ARTIFACT: 10,
            self.OCR_CONFIDENCE_ANOMALY: 5,
            self.DATE_SEQUENCE_VIOLATION: 5,
            self.TRANSACTION_FORMAT_VIOLATION: 5,
            self.UTILITY_BILL_ANOMALY: 10,
            self.SALARY_CALCULATION_MISMATCH: 15,
        }
        return points[self]

    @property
    def is_deterministic(self) -> bool:
        """True = 100% deterministic rule. False = probabilistic (CV/LLM)."""
        probabilistic = {
            self.IMAGE_ELA_MANIPULATION,
            self.AI_GENERATION_ARTIFACT,
            self.OCR_CONFIDENCE_ANOMALY,
        }
        return self not in probabilistic


# =============================================================================
# Domain 5: Risk Assessment & Evidence Fusion
# =============================================================================


class RiskTier(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def score_range(self) -> tuple[int, int]:
        """Inclusive (min, max) score range for this tier."""
        ranges = {
            self.LOW: (0, 20),
            self.MODERATE: (21, 40),
            self.ELEVATED: (41, 60),
            self.HIGH: (61, 80),
            self.CRITICAL: (81, 100),
        }
        return ranges[self]

    @property
    def action_directive(self) -> str:
        """The standard action directive for this risk tier."""
        directives = {
            self.LOW: "STRAIGHT_THROUGH_APPROVAL",
            self.MODERATE: "SECONDARY_SCAN",
            self.ELEVATED: "HUMAN_REVIEW",
            self.HIGH: "ESCALATION_REQUIRED",
            self.CRITICAL: "IMMEDIATE_REJECTION",
        }
        return directives[self]

    @classmethod
    def from_score(cls, score: int) -> "RiskTier":
        """Classify a 0-100 risk score into the appropriate RiskTier."""
        if score <= 20:
            return cls.LOW
        elif score <= 40:
            return cls.MODERATE
        elif score <= 60:
            return cls.ELEVATED
        elif score <= 80:
            return cls.HIGH
        else:
            return cls.CRITICAL


# =============================================================================
# Domain 6: Multi-Agent AI Investigation
# =============================================================================


class AgentRole(str, Enum):
    STRUCTURAL_FORENSIC = "STRUCTURAL_FORENSIC"
    VISUAL_FORENSIC = "VISUAL_FORENSIC"
    SEMANTIC_PK_FINANCIAL = "SEMANTIC_PK_FINANCIAL"
    LEAD_INVESTIGATOR = "LEAD_INVESTIGATOR"
    INTERACTIVE_QA = "INTERACTIVE_QA"

    @property
    def display_name(self) -> str:
        names = {
            self.STRUCTURAL_FORENSIC: "Structural Forensic Agent",
            self.VISUAL_FORENSIC: "Visual Forensic Agent",
            self.SEMANTIC_PK_FINANCIAL: "Semantic & PK-Financial Agent",
            self.LEAD_INVESTIGATOR: "Lead Investigator Agent",
            self.INTERACTIVE_QA: "Interactive Q&A Assistant",
        }
        return names[self]


class AgentMessageRole(str, Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"


# =============================================================================
# Domain 7: Audit, Compliance & Chain of Custody
# =============================================================================


class AuditAction(str, Enum):
    # Authentication
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    USER_LOGIN_FAILED = "USER_LOGIN_FAILED"
    USER_MFA_ENABLED = "USER_MFA_ENABLED"
    USER_MFA_DISABLED = "USER_MFA_DISABLED"
    USER_PASSWORD_CHANGED = "USER_PASSWORD_CHANGED"
    USER_ACCOUNT_LOCKED = "USER_ACCOUNT_LOCKED"
    # Investigation lifecycle
    INVESTIGATION_CREATED = "INVESTIGATION_CREATED"
    INVESTIGATION_UPDATED = "INVESTIGATION_UPDATED"
    INVESTIGATION_REVIEWED = "INVESTIGATION_REVIEWED"
    INVESTIGATION_CLOSED = "INVESTIGATION_CLOSED"
    INVESTIGATION_ARCHIVED = "INVESTIGATION_ARCHIVED"
    INVESTIGATION_DELETED = "INVESTIGATION_DELETED"
    # Document
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_DOWNLOADED = "DOCUMENT_DOWNLOADED"
    DOCUMENT_VIEWED = "DOCUMENT_VIEWED"
    DOCUMENT_DELETED = "DOCUMENT_DELETED"
    # Pipeline
    PIPELINE_TRIGGERED = "PIPELINE_TRIGGERED"
    PIPELINE_COMPLETED = "PIPELINE_COMPLETED"
    PIPELINE_FAILED = "PIPELINE_FAILED"
    PIPELINE_RETRIED = "PIPELINE_RETRIED"
    PIPELINE_CANCELLED = "PIPELINE_CANCELLED"
    # Risk
    RISK_SCORE_COMPUTED = "RISK_SCORE_COMPUTED"
    RISK_SCORE_OVERRIDDEN = "RISK_SCORE_OVERRIDDEN"
    # Agent
    AGENT_SESSION_STARTED = "AGENT_SESSION_STARTED"
    AGENT_SESSION_COMPLETED = "AGENT_SESSION_COMPLETED"
    AGENT_QUERY_ASKED = "AGENT_QUERY_ASKED"
    # Export
    DOSSIER_GENERATED = "DOSSIER_GENERATED"
    DOSSIER_DOWNLOADED = "DOSSIER_DOWNLOADED"
    # API
    API_KEY_CREATED = "API_KEY_CREATED"
    API_KEY_REVOKED = "API_KEY_REVOKED"
    # Administration
    ORGANIZATION_SETTINGS_UPDATED = "ORGANIZATION_SETTINGS_UPDATED"
    USER_CREATED = "USER_CREATED"
    USER_ROLE_CHANGED = "USER_ROLE_CHANGED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    USER_REACTIVATED = "USER_REACTIVATED"

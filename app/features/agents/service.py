import asyncio
import json
import logging
import os
from typing import AsyncGenerator
from prisma import Prisma

from app.config import get_settings
from app.db.client import set_org_context
from app.features.agents import schemas
from app.features.agents.swarm.lead_investigator import LeadInvestigatorAgent

logger = logging.getLogger(__name__)
settings = get_settings()


async def _build_evidence_manifest(db: Prisma, investigation_id: str) -> dict:
    """Compile verified evidence items, risk assessment, and documents for the investigation."""
    inv = await db.investigation.find_unique(
        where={"id": investigation_id},
        include={"documents": True, "riskAssessment": True},
    )
    if not inv:
        return {}

    # Query all evidence items for this investigation (via document IDs)
    doc_ids = [d.id for d in (inv.documents or [])]
    evidence_items = []
    if doc_ids:
        items = await db.evidenceitem.find_many(
            where={"documentId": {"in": doc_ids}},
            include={"boundingBoxes": True},
        )
        for it in items:
            evidence_items.append({
                "id": it.id,
                "documentId": it.documentId,
                "ruleId": it.ruleId,
                "category": it.category,
                "severity": it.severity,
                "riskPoints": it.riskPoints,
                "title": it.title,
                "description": it.description,
                "expectedValue": it.expectedValue,
                "actualValue": it.actualValue,
                "discrepancy": it.discrepancy,
                "pageNumber": it.pageNumber,
                "isDeterministic": it.isDeterministic,
                "boundingBoxes": [
                    {
                        "id": b.id,
                        "pageNumber": b.pageNumber,
                        "xPts": b.xPts,
                        "yPts": b.yPts,
                        "widthPts": b.widthPts,
                        "heightPts": b.heightPts,
                        "label": b.label,
                        "color": b.color,
                    }
                    for b in (it.boundingBoxes or [])
                ],
            })

    risk_dict = {}
    if inv.riskAssessment:
        ra = inv.riskAssessment
        fp = ra.fusionParameters or {}
        if hasattr(fp, "data"):
            fp = fp.data
        elif hasattr(fp, "to_dict"):
            fp = fp.to_dict()
        if not isinstance(fp, dict):
            fp = {}
        doc_auth = fp.get("document_authenticity") or {}
        txn_risk = fp.get("transaction_risk") or {}

        tamper_score = doc_auth.get("tamper_score", ra.overallScore)
        auth_score = doc_auth.get("score", max(0, 100 - tamper_score))
        auth_tier = doc_auth.get(
            "tier",
            "VERIFIED_AUTHENTIC" if tamper_score <= 10 else ("SUSPECT_DOCUMENT" if tamper_score <= 40 else "FORGERY_DETECTED"),
        )
        txn_score = txn_risk.get("score", 0)
        txn_tier = txn_risk.get(
            "tier",
            "CRITICAL_PROSCRIBED" if txn_score >= 75 else ("HIGH_AML_RISK" if txn_score >= 45 else ("MONITORED" if txn_score >= 20 else "CLEAN")),
        )

        risk_dict = {
            "overallScore": ra.overallScore,
            "riskTier": ra.riskTier,
            "actionDirective": ra.actionDirective,
            "totalEvidenceCount": ra.totalEvidenceCount,
            "criticalCount": ra.criticalCount,
            "highCount": ra.highCount,
            "mediumCount": ra.mediumCount,
            "lowCount": ra.lowCount,
            "overriddenScore": ra.overriddenScore,
            "overriddenTier": str(ra.overriddenTier) if ra.overriddenTier else None,
            "overrideReason": ra.overrideReason,
            "overriddenById": ra.overriddenById,
            "overriddenAt": ra.overriddenAt.isoformat() if ra.overriddenAt else None,
            "authenticityScore": auth_score,
            "tamperScore": tamper_score,
            "authenticityTier": auth_tier,
            "transactionRiskScore": txn_score,
            "transactionRiskTier": txn_tier,
            "fusionParameters": fp,
        }

    return {
        "investigation": {
            "id": inv.id,
            "organizationId": getattr(inv, "organizationId", None),
            "caseNumber": inv.caseNumber,
            "title": inv.title,
            "status": inv.status,
            "priority": inv.priority,
        },
        "documents": [
            {
                "id": d.id,
                "originalFilename": d.originalFilename,
                "sha256Hash": d.sha256Hash,
                "fileSizeBytes": d.fileSizeBytes,
                "documentType": d.documentType,
                "pageCount": d.pageCount,
            }
            for d in (inv.documents or [])
        ],
        "risk_assessment": risk_dict,
        "evidence_items": evidence_items,
    }


async def run_interactive_qa(
    db: Prisma,
    investigation_id: str,
    user_id: str,
    question: str,
    stream: bool = False,
):
    """
    Dispatch an interactive Q&A query to the Lead Investigator Agent.
    The agent is constrained to the verified evidence manifest for this investigation
    (zero-hallucination policy from proposal §6).
    """
    manifest = await _build_evidence_manifest(db, investigation_id)
    lead_agent = LeadInvestigatorAgent(manifest)

    # Generate answer using LeadInvestigatorAgent (bound to verified evidence)
    answer_dict = await lead_agent.answer_query(question)
    answer_text = answer_dict["answer"]
    evidence_refs = answer_dict.get("evidence_references", [])
    tokens_used = answer_dict.get("tokens_used", 100)

    # Safely persist session & messages within tenant RLS context
    session_id = f"sess-{investigation_id}"
    org_id = manifest.get("investigation", {}).get("organizationId")

    async def _save_messages(target_db):
        sess = await target_db.agentsession.find_first(
            where={"investigationId": investigation_id, "agentRole": "INTERACTIVE_QA"},
            order={"createdAt": "desc"},
        )
        if not sess:
            provider = "groq" if (settings.groq_api_key or os.environ.get("GROQ_API_KEY")) else ("gemini" if settings.google_gemini_api_key else "deeptrace-rules")
            model = settings.groq_model_primary if (settings.groq_api_key or os.environ.get("GROQ_API_KEY")) else ("gemini-2.0-flash" if settings.google_gemini_api_key else "lead-investigator-v1")
            sess = await target_db.agentsession.create(
                data={
                    "investigationId": investigation_id,
                    "agentRole": "INTERACTIVE_QA",
                    "modelProvider": provider,
                    "modelName": model,
                    "status": "active",
                }
            )

        count = await target_db.agentmessage.count(where={"agentSessionId": sess.id})
        await target_db.agentmessage.create(
            data={
                "agentSessionId": sess.id,
                "role": "USER",
                "content": question,
                "sequenceOrder": count + 1,
            }
        )
        await target_db.agentmessage.create(
            data={
                "agentSessionId": sess.id,
                "role": "ASSISTANT",
                "content": answer_text,
                "tokensIn": len(question.split()),
                "tokensOut": tokens_used,
                "sequenceOrder": count + 2,
            }
        )
        await target_db.agentsession.update(
            where={"id": sess.id},
            data={
                "totalTokensIn": sess.totalTokensIn + len(question.split()),
                "totalTokensOut": sess.totalTokensOut + tokens_used,
            },
        )
        return sess.id

    try:
        if org_id and not getattr(db, "_tx_id", None):
            async with set_org_context(org_id) as tx:
                session_id = await _save_messages(tx)
        else:
            session_id = await _save_messages(db)
    except Exception as exc:
        logger.warning("Could not persist interactive QA messages for investigation %s: %s", investigation_id, exc)


    if stream:
        async def stream_generator() -> AsyncGenerator[str, None]:
            # Stream by words / small token chunks
            words = answer_text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                payload = {"chunk": chunk, "done": False}
                yield f"data: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.01)

            final_payload = {
                "done": True,
                "answer": answer_text,
                "agent_session_id": session_id,
                "evidence_references": evidence_refs,
                "tokens_used": tokens_used,
            }
            yield f"data: {json.dumps(final_payload)}\n\n"

        return stream_generator()

    return schemas.AskResponse(
        answer=answer_text,
        agent_session_id=session_id,
        evidence_references=evidence_refs,
        tokens_used=tokens_used,
    )


async def get_agent_sessions(db: Prisma, investigation_id: str) -> list[schemas.AgentSessionResponse]:
    """List all agent sessions (swarm + Q&A) for an investigation."""
    sessions = await db.agentsession.find_many(
        where={"investigationId": investigation_id},
        order={"createdAt": "desc"},
    )
    return [
        schemas.AgentSessionResponse(
            id=s.id,
            agent_role=str(s.agentRole),
            model_provider=s.modelProvider,
            model_name=s.modelName,
            total_tokens_in=s.totalTokensIn,
            total_tokens_out=s.totalTokensOut,
            total_cost_usd=s.totalCostUsd,
            status=s.status,
            started_at=s.startedAt,
            completed_at=s.completedAt,
        )
        for s in sessions
    ]


async def get_interactive_qa_history(db: Prisma, investigation_id: str) -> schemas.AskHistoryResponse:
    """Retrieve all messages from the interactive QA session for this investigation."""
    sess = await db.agentsession.find_first(
        where={"investigationId": investigation_id, "agentRole": "INTERACTIVE_QA"},
        include={"messages": True},
        order={"createdAt": "desc"},
    )
    if not sess:
        return schemas.AskHistoryResponse(messages=[])

    sorted_messages = sorted(sess.messages or [], key=lambda m: m.sequenceOrder)
    return schemas.AskHistoryResponse(
        session_id=sess.id,
        model_provider=sess.modelProvider,
        model_name=sess.modelName,
        status=sess.status,
        messages=[
            schemas.AgentMessageItem(
                id=m.id,
                role=str(m.role),
                content=m.content,
                tokens_in=m.tokensIn or 0,
                tokens_out=m.tokensOut or 0,
                sequence_order=m.sequenceOrder,
                created_at=m.createdAt,
            )
            for m in sorted_messages
        ],
    )


async def run_lead_investigator_analysis(
    db: Prisma,
    investigation_id: str,
) -> schemas.LeadInvestigatorAnalysisResponse:
    """
    Compile verified evidence manifest, run the LangGraph Lead Investigator Agent,
    and return bilingual English and Urdu briefings for credit officers.
    """
    manifest = await _build_evidence_manifest(db, investigation_id)
    lead_agent = LeadInvestigatorAgent(manifest)
    res = await lead_agent.analyze()

    org_id = manifest.get("investigation", {}).get("organizationId")

    async def _save_lead_session(target_db):
        sess = await target_db.agentsession.find_first(
            where={"investigationId": investigation_id, "agentRole": "LEAD_INVESTIGATOR"},
            order={"createdAt": "desc"},
        )
        if not sess:
            await target_db.agentsession.create(
                data={
                    "investigationId": investigation_id,
                    "agentRole": "LEAD_INVESTIGATOR",
                    "modelProvider": res.get("model_provider", "deeptrace-deterministic"),
                    "modelName": res.get("model_name", "lead-investigator-v1"),
                    "status": "completed",
                }
            )
        else:
            await target_db.agentsession.update(
                where={"id": sess.id},
                data={
                    "modelProvider": res.get("model_provider"),
                    "modelName": res.get("model_name"),
                    "status": "completed",
                },
            )

    try:
        if org_id and not getattr(db, "_tx_id", None):
            async with set_org_context(org_id) as tx:
                await _save_lead_session(tx)
        else:
            await _save_lead_session(db)
    except Exception as exc:
        logger.warning("Could not persist lead investigator session for %s: %s", investigation_id, exc)


    briefing_items = [
        schemas.CreditBriefingItem(
            page_number=b.get("page_number"),
            row_number=b.get("row_number"),
            title=b.get("title", ""),
            transaction_label=b.get("transaction_label"),
            expected_value=b.get("expected_value"),
            actual_value=b.get("actual_value"),
            discrepancy=b.get("discrepancy"),
            font_detected=b.get("font_detected"),
            expected_font=b.get("expected_font"),
            visual_cue=b.get("visual_cue"),
            summary_en=b.get("summary_en", ""),
            summary_ur=b.get("summary_ur", ""),
            severity=b.get("severity", "MEDIUM"),
            rule_id=b.get("rule_id"),
            evidence_id=b.get("evidence_id"),
        )
        for b in res.get("credit_briefing_items", [])
    ]

    return schemas.LeadInvestigatorAnalysisResponse(
        investigation_id=investigation_id,
        overall_score=res.get("overall_score", 0),
        risk_tier=res.get("risk_tier", "LOW"),
        action_directive=res.get("action_directive", "STRAIGHT_THROUGH_APPROVAL"),
        confidence_score=res.get("confidence_score", 0.95),
        anomalies_detected=res.get("anomalies_detected", 0),
        model_provider=res.get("model_provider", "groq"),
        model_name=res.get("model_name", "gpt-oss-120b"),
        english_summary=res.get("english_summary", ""),
        urdu_summary=res.get("urdu_summary", ""),
        narrative=res.get("narrative", ""),
        cross_signal_correlations=res.get("cross_signal_correlations", []),
        credit_briefing_items=briefing_items,
        evidence_citations=res.get("evidence_citations", []),
        specialist_reports=res.get("specialist_reports", {}),
    )


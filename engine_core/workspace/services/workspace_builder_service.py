import logging
from typing import Dict, Any, List
import uuid

from engine_core.db import get_connection
from engine_core.workspace.dtos.workspace_dto import (
    CompanyWorkspaceDTO,
    OverviewSection,
    BusinessSummarySection,
    InvestmentThesisSection,
    CompetitiveAdvantage,
    RiskProfile,
    GrowthDriver,
    FinancialMetrics,
    MonitoringItem,
    SourceReference
)

logger = logging.getLogger(__name__)

class CompanyKnowledgeNotFoundException(Exception):
    pass

class CompanyWorkspaceBuilderService:
    def __init__(self, conn=None):
        self.conn = conn
        self._owns_conn = False
        if not self.conn:
            self.conn = get_connection()
            self._owns_conn = True

    def close(self):
        if self._owns_conn and self.conn:
            self.conn.close()

    def build(self, company_id: str) -> CompanyWorkspaceDTO:
        # Read-only transaction logic
        cur = self.conn.cursor()
        try:
            # 1. Fetch Company Overview
            cur.execute(
                """
                SELECT company_id, symbol, name, sector, industry
                FROM ciw_company
                WHERE company_id = %s OR symbol = %s
                """,
                (company_id, company_id)
            )
            company_row = cur.fetchone()
            if not company_row:
                raise CompanyKnowledgeNotFoundException(f"Company {company_id} not found")

            actual_company_id = str(company_row[0])
            overview = OverviewSection(
                companyId=actual_company_id,
                symbol=company_row[1],
                name=company_row[2],
                sector=company_row[3],
                industry=company_row[4]
            )

            # Note: The PRD states no LLM, no extraction. We strictly project from CompanyKnowledge.
            # In a real implementation, we would fetch from `company_knowledge` joined with `ake_variable`.
            # Since this is a projection layer and we lack the full populated schema for all DTO fields,
            # we will project default/empty states for now if the tables don't have them, ensuring
            # zero inference or synthesis.

            cur.execute(
                """
                SELECT v.canonical_name, ck.current_value
                FROM CompanyKnowledge ck
                JOIN ake_variable v ON ck.variable_id = v.id
                WHERE ck.company_id = %s
                """,
                (actual_company_id,)
            )
            knowledge_rows = cur.fetchall()
            
            # Map knowledge to DTO sections
            knowledge_map = {row[0]: row[1] for row in knowledge_rows}
            
            # Pure projection mapping, no inference.
            business_summary = BusinessSummarySection(
                description=knowledge_map.get("business_description", "No description available."),
                businessModel=knowledge_map.get("business_model", "No business model documented.")
            )

            thesis = InvestmentThesisSection(
                coreThesis=knowledge_map.get("core_thesis", "No thesis documented."),
                convictionScore=float(knowledge_map.get("conviction_score", 0.0))
            )

            # We assume competitive_advantages, risks, etc. are stored as JSON arrays in current_value
            # or we project empty lists if missing.
            competitive_advantages = []
            for adv in knowledge_map.get("competitive_advantages", []):
                if isinstance(adv, dict):
                    competitive_advantages.append(CompetitiveAdvantage(**adv))

            risks = []
            for rsk in knowledge_map.get("risks", []):
                if isinstance(rsk, dict):
                    risks.append(RiskProfile(**rsk))

            growth_drivers = []
            for gd in knowledge_map.get("growth_drivers", []):
                if isinstance(gd, dict):
                    growth_drivers.append(GrowthDriver(**gd))

            financials = FinancialMetrics(
                revenueGrowth=knowledge_map.get("revenue_growth"),
                margins=knowledge_map.get("margins"),
                roce=knowledge_map.get("roce")
            )

            monitoring = []
            for mi in knowledge_map.get("monitoring_checklist", []):
                if isinstance(mi, dict):
                    monitoring.append(MonitoringItem(**mi))

            # Fetch Source Documents
            cur.execute(
                """
                SELECT document_id, title, uploaded_at
                FROM ciw_source_document
                WHERE company_id = %s
                """,
                (actual_company_id,)
            )
            doc_rows = cur.fetchall()
            source_documents = [
                SourceReference(documentId=str(r[0]), title=r[1], date=r[2])
                for r in doc_rows
            ]

            return CompanyWorkspaceDTO(
                overview=overview,
                businessSummary=business_summary,
                investmentThesis=thesis,
                competitiveAdvantages=competitive_advantages,
                risks=risks,
                growthDrivers=growth_drivers,
                financialHighlights=financials,
                monitoringChecklist=monitoring,
                sourceDocuments=source_documents
            )

        except CompanyKnowledgeNotFoundException:
            raise
        except Exception as e:
            # Wrap infrastructure errors
            raise Exception(f"Failed to project workspace: {str(e)}")
        finally:
            cur.close()

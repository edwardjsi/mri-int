from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class SourceReference(BaseModel):
    documentId: str
    title: str
    date: datetime

class OverviewSection(BaseModel):
    companyId: str
    symbol: str
    name: str
    sector: Optional[str]
    industry: Optional[str]

class BusinessSummarySection(BaseModel):
    description: str
    businessModel: str

class InvestmentThesisSection(BaseModel):
    coreThesis: str
    convictionScore: float

class CompetitiveAdvantage(BaseModel):
    type: str
    description: str
    durability: str

class RiskProfile(BaseModel):
    category: str
    description: str
    severity: str

class GrowthDriver(BaseModel):
    description: str
    timeline: str
    impact: str

class FinancialMetrics(BaseModel):
    revenueGrowth: Optional[str]
    margins: Optional[str]
    roce: Optional[str]

class MonitoringItem(BaseModel):
    metric: str
    target: str
    status: str

class CompanyWorkspaceDTO(BaseModel):
    overview: OverviewSection
    businessSummary: BusinessSummarySection
    investmentThesis: InvestmentThesisSection
    competitiveAdvantages: List[CompetitiveAdvantage]
    risks: List[RiskProfile]
    growthDrivers: List[GrowthDriver]
    financialHighlights: FinancialMetrics
    monitoringChecklist: List[MonitoringItem]
    sourceDocuments: List[SourceReference]

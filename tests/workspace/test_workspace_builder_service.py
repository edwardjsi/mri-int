import pytest
from engine_core.workspace.services.workspace_builder_service import (
    CompanyWorkspaceBuilderService,
    CompanyKnowledgeNotFoundException
)
from engine_core.workspace.dtos.workspace_dto import CompanyWorkspaceDTO
import uuid

class MockCursor:
    def __init__(self, responses):
        self.responses = responses
        self.call_idx = 0
        
    def execute(self, query, params=None):
        pass
        
    def fetchone(self):
        resp = self.responses[self.call_idx]
        self.call_idx += 1
        return resp
        
    def fetchall(self):
        resp = self.responses[self.call_idx]
        self.call_idx += 1
        return resp

    def close(self):
        pass

class MockConnection:
    def __init__(self, responses):
        self.responses = responses
        
    def cursor(self):
        return MockCursor(self.responses)
        
    def close(self):
        pass

def test_should_return_valid_dto_when_knowledge_exists():
    mock_company_id = str(uuid.uuid4())
    responses = [
        # 1. Company row (id, symbol, name, sector, industry)
        (mock_company_id, "TEST", "Test Co", "IT", "Software"),
        # 2. Knowledge rows (canonical_name, current_value)
        [
            ("business_description", "A test business"),
            ("business_model", "B2B SaaS"),
            ("core_thesis", "Strong growth"),
            ("conviction_score", 8.5),
            ("competitive_advantages", [{"type": "Moat", "description": "Network effect", "durability": "High"}]),
            ("risks", [{"category": "Regulatory", "description": "New laws", "severity": "Medium"}]),
            ("growth_drivers", [{"description": "Expansion", "timeline": "2027", "impact": "High"}]),
            ("revenue_growth", "20%"),
            ("margins", "15%"),
            ("roce", "25%"),
            ("monitoring_checklist", [{"metric": "Churn", "target": "<5%", "status": "Green"}])
        ],
        # 3. Source documents
        []
    ]
    
    conn = MockConnection(responses)
    service = CompanyWorkspaceBuilderService(conn=conn)
    dto = service.build(mock_company_id)
    
    assert isinstance(dto, CompanyWorkspaceDTO)
    assert dto.overview.symbol == "TEST"
    assert dto.investmentThesis.convictionScore == 8.5
    assert len(dto.competitiveAdvantages) == 1
    assert dto.competitiveAdvantages[0].durability == "High"

def test_should_throw_exception_when_knowledge_missing():
    responses = [
        # 1. Company row (None = not found)
        None
    ]
    
    conn = MockConnection(responses)
    service = CompanyWorkspaceBuilderService(conn=conn)
    
    with pytest.raises(CompanyKnowledgeNotFoundException):
        service.build("INVALID_ID")

def test_should_be_idempotent_across_multiple_calls():
    mock_company_id = str(uuid.uuid4())
    # We duplicate the responses sequence 3 times
    sequence = [
        (mock_company_id, "TEST", "Test Co", "IT", "Software"),
        [("business_description", "Test")],
        []
    ]
    responses = sequence * 3
    
    conn = MockConnection(responses)
    service = CompanyWorkspaceBuilderService(conn=conn)
    
    dto1 = service.build(mock_company_id)
    dto2 = service.build(mock_company_id)
    dto3 = service.build(mock_company_id)
    
    assert dto1.model_dump() == dto2.model_dump()
    assert dto2.model_dump() == dto3.model_dump()

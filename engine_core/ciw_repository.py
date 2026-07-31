import json
from typing import Optional, List, Dict, Any
from .db import get_connection
from .ciw_models import (
    CompanyWorkspace, CompanyIdentity, PortfolioContext, 
    KnowledgeState, TimelineEvent, KnowledgeNode,
    NodeType, Status, Confidence, EventType
)

class CompanyWorkspaceRepository:
    def __init__(self, conn=None):
        self.conn = conn or get_connection()
        self._owns_connection = (conn is None)

    def close(self):
        if self._owns_connection and self.conn:
            self.conn.close()

    def get_workspace(self, symbol: str) -> Optional[CompanyWorkspace]:
        """Fetch the full Aggregate Root for a company."""
        cur = self.conn.cursor()
        try:
            # 1. Fetch Company Core State
            cur.execute("SELECT * FROM ciw_company WHERE symbol = %s", (symbol,))
            company_row = cur.fetchone()
            if not company_row:
                return None

            company_id = company_row['company_id']

            # 2. Fetch Knowledge Nodes
            cur.execute("SELECT * FROM ciw_knowledge_node WHERE company_id = %s", (company_id,))
            nodes_rows = cur.fetchall()

            # 3. Fetch Timeline Events
            cur.execute(
                "SELECT * FROM ciw_timeline_event WHERE company_id = %s ORDER BY event_date DESC", 
                (company_id,)
            )
            timeline_rows = cur.fetchall()

            # --- Build the Aggregate ---
            
            # Identity
            identity = CompanyIdentity(
                company_id=str(company_id),
                symbol=company_row['symbol'],
                name=company_row['name'],
                sector=company_row['sector']
            )

            # Portfolio Context
            portfolio = PortfolioContext(
                status=company_row['portfolio_status'],
                allocation=float(company_row['portfolio_allocation'] or 0),
                average_cost=float(company_row['portfolio_avg_cost'] or 0)
            )

            # Process Knowledge Nodes
            understanding: Dict[str, KnowledgeNode] = {}
            risks: List[KnowledgeNode] = []
            catalysts: List[KnowledgeNode] = []
            monitoring: List[KnowledgeNode] = []

            for row in nodes_rows:
                node = KnowledgeNode(
                    id=str(row['id']),
                    node_type=NodeType(row['node_type']),
                    text=row['current_text'],
                    confidence=Confidence(row['confidence']),
                    status=Status(row['status']),
                    evidence=row['evidence'] if isinstance(row['evidence'], list) else [],
                    history=row['history'] if isinstance(row['history'], list) else [],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    metadata=row['metadata'] if isinstance(row['metadata'], dict) else {}
                )
                
                # Route the node to its correct collection
                if node.node_type in (NodeType.THESIS, NodeType.BUSINESS_QUALITY, NodeType.COMPETITIVE_ADVANTAGE):
                    # Lowercase enum for key e.g., 'thesis'
                    understanding[node.node_type.value.lower()] = node
                elif node.node_type == NodeType.RISK:
                    risks.append(node)
                elif node.node_type == NodeType.CATALYST:
                    catalysts.append(node)
                elif node.node_type == NodeType.MONITORING:
                    monitoring.append(node)

            # State
            state = KnowledgeState(
                last_updated=company_row['last_reviewed'],
                understanding=understanding,
                risks=risks,
                catalysts=catalysts,
                monitoring=monitoring
            )

            # Timeline
            timeline = []
            for row in timeline_rows:
                timeline.append(TimelineEvent(
                    id=str(row['id']),
                    event_date=row['event_date'],
                    event_type=EventType(row['event_type']),
                    summary=row['summary'],
                    reference_id=row['reference_id']
                ))

            # Assemble Workspace
            workspace = CompanyWorkspace(
                identity=identity,
                state=state,
                timeline=timeline,
                portfolio=portfolio,
                last_reviewed=company_row['last_reviewed'],
                current_decision=company_row['current_decision'],
                current_trend=company_row['current_trend']
            )

            return workspace

        finally:
            cur.close()

    # --- Basic writing methods for initial seeding / testing ---
    
    def seed_company(self, symbol: str, name: str, sector: str) -> str:
        """Create a company if it doesn't exist, returns company_id."""
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT company_id FROM ciw_company WHERE symbol = %s", (symbol,))
            row = cur.fetchone()
            if row:
                return str(row['company_id'])
                
            cur.execute(
                """
                INSERT INTO ciw_company (symbol, name, sector) 
                VALUES (%s, %s, %s) RETURNING company_id
                """,
                (symbol, name, sector)
            )
            self.conn.commit()
            return str(cur.fetchone()['company_id'])
        finally:
            cur.close()

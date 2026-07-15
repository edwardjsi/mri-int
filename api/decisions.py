"""Decisions API - serves the architectural decisions log"""
from fastapi import APIRouter, Query
from typing import Optional
import os
import re

router = APIRouter(prefix="/api/decisions", tags=["decisions"])

DECISIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Decisions.md")


def parse_decisions(content: str) -> list:
    """Parse Decisions.md into structured data"""
    decisions = []
    
    # Split by decision headers
    pattern = r'(## Decision \d+ — .+?)(?=\n## Decision \d+|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for match in matches:
        lines = match.strip().split('\n')
        if len(lines) < 1:
            continue
            
        # Parse header
        header = lines[0].replace('## ', '').strip()
        decision_match = re.match(r'Decision (\d+) — (.+)', header)
        if not decision_match:
            continue
            
        number = int(decision_match.group(1))
        title = decision_match.group(2).strip()
        
        # Parse body
        body = '\n'.join(lines[1:]).strip()
        
        # Extract fields
        date_match = re.search(r'Date:\s*(.+)', body)
        date = date_match.group(1).strip() if date_match else None
        
        status_match = re.search(r'Status:\s*(.+)', body)
        status = status_match.group(1).strip() if status_match else None
        
        # Get the main decision content (before "Reason:" or "Context:")
        reason_match = re.search(r'(?:Reason|Context):\s*(.+)', body, re.DOTALL)
        reason = reason_match.group(1).strip() if reason_match else body
        
        # Clean up reason - remove implementation log and other sections
        reason = re.split(r'\n(?:Implementation|Files changed|Next|Branch|Test count|Detailed|Owner|Decision-maker|Trigger):', reason)[0].strip()
        
        decisions.append({
            "number": number,
            "title": title,
            "date": date,
            "status": status,
            "reason": reason,
            "raw": match.strip()
        })
    
    # Sort by number descending (newest first)
    decisions.sort(key=lambda x: x["number"], reverse=True)
    return decisions


@router.get("")
async def get_all_decisions(
    limit: Optional[int] = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None)
):
    """Get all decisions with optional pagination and search"""
    if not os.path.exists(DECISIONS_FILE):
        return {"decisions": [], "total": 0}
    
    with open(DECISIONS_FILE, 'r') as f:
        content = f.read()
    
    decisions = parse_decisions(content)
    
    # Filter by search
    if search:
        search_lower = search.lower()
        decisions = [d for d in decisions if 
            search_lower in d["title"].lower() or 
            search_lower in d["reason"].lower() or
            search_lower in str(d["number"])]
    
    total = len(decisions)
    
    # Apply pagination
    if limit:
        decisions = decisions[offset:offset + limit]
    
    return {"decisions": decisions, "total": total}


@router.get("/{decision_number}")
async def get_decision(decision_number: int):
    """Get a specific decision by number"""
    if not os.path.exists(DECISIONS_FILE):
        return {"error": "Decisions file not found"}
    
    with open(DECISIONS_FILE, 'r') as f:
        content = f.read()
    
    decisions = parse_decisions(content)
    
    for decision in decisions:
        if decision["number"] == decision_number:
            return decision
    
    return {"error": f"Decision {decision_number} not found"}


@router.get("/raw")
async def get_raw_decisions():
    """Get raw Decisions.md content"""
    if not os.path.exists(DECISIONS_FILE):
        return {"content": ""}
    
    with open(DECISIONS_FILE, 'r') as f:
        content = f.read()
    
    return {"content": content}
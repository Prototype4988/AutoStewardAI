"""
FastAPI backend for AutoSteward AI UI
Serves API endpoints for the React frontend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

# Add parent directory to path to import autosteward_ai
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.autosteward_ai import AutoStewardAI

app = FastAPI(title="AutoSteward AI API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AutoSteward AI
autosteward = AutoStewardAI("config/config.yaml")

class Issue(BaseModel):
    id: int
    table: str
    test: str
    issue: str
    severity: str
    timestamp: str
    fixSql: str
    aiGenerated: bool
    model: str

class ScanRequest(BaseModel):
    table_fqn: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "AutoSteward AI API"}

@app.get("/api/issues")
async def get_issues():
    """Get current list of issues"""
    # In production, this would query the database or OpenMetadata
    # For now, return empty list (demo mode)
    return []

@app.post("/api/scan")
async def scan_for_issues(request: ScanRequest):
    """Scan for data quality issues"""
    try:
        table_fqn = request.table_fqn or "Ecommerce_test.jaffle_shop.mart.customers"
        
        # Run the detection and diagnosis
        diagnosis = autosteward.diagnose_root_cause(table_fqn)
        
        if diagnosis.get('status') == 'failed':
            # Generate fix
            fix_suggestion = autosteward.suggest_fix(table_fqn, diagnosis)
            
            if fix_suggestion:
                return {
                    "status": "issue_found",
                    "issue": {
                        "id": 1,
                        "table": table_fqn,
                        "test": fix_suggestion.get('test_name', 'unknown'),
                        "issue": fix_suggestion.get('issue', 'unknown'),
                        "severity": "high",
                        "timestamp": "2026-04-19T12:00:00Z",
                        "fixSql": fix_suggestion.get('fix_sql', ''),
                        "aiGenerated": fix_suggestion.get('ai_generated', False),
                        "model": fix_suggestion.get('model', 'unknown')
                    }
                }
        
        return {"status": "no_issues"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/approve")
async def approve_fix(issue_id: int):
    """Approve and apply a fix"""
    # In production, this would execute the SQL fix
    return {"status": "approved", "message": f"Fix #{issue_id} approved"}

@app.post("/api/reject")
async def reject_fix(issue_id: int):
    """Reject a fix"""
    return {"status": "rejected", "message": f"Fix #{issue_id} rejected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

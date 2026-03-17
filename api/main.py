import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.portfolio_review import router as portfolio_review_router

app = FastAPI()

# OPEN THE GATES: This stops the browser from blocking the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio_review_router)

# THE HEARTBEAT: Render needs this to stay green
@app.get("/")
async def root():
    return {"message": "MRI-Int API is active", "port": 10000}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}
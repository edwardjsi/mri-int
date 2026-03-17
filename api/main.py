import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import your routes
from api.portfolio_review import router as portfolio_review_router

# Load environment variables
load_dotenv()

# THE CRITICAL FIX: Render looks for this 'app' variable
app = FastAPI(title="MRI-Int API", version="1.0.0")

# CORS Configuration
cors_origins_str = os.getenv("CORS_ORIGINS", "https://mri-frontend.onrender.com")
origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(portfolio_review_router)

@app.get("/")
async def root():
    return {"status": "online", "message": "MRI-Int API is running"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

# Standard Debug Endpoints
@app.get("/api/db-debug")
async def db_debug():
    from src.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return {"total_tables": len(tables), "discovered": tables}
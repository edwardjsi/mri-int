import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import the portfolio router
from api.portfolio_review import router as portfolio_review_router

load_dotenv()

# THE CRITICAL VARIABLE: Render looks for 'app'
app = FastAPI(title="MRI-Int API")

# CORS setup: This allows the frontend to talk to the backend
# Using "*" (Allow All) temporarily to break through the "Not Found" errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the portfolio review routes
app.include_router(portfolio_review_router)

# ROOT HEARTBEAT: Render needs this to stay green and not shut down
@app.get("/")
async def root():
    return {"message": "MRI-Int API is Live", "status": "healthy"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}
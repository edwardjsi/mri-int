import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import the portfolio router
from api.portfolio_review import router as portfolio_review_router

load_dotenv()

# THE CRITICAL VARIABLE: Render looks for 'app'
app = FastAPI(title="MRI-Int API")

# CORS setup: Allows your frontend (mri-frontend.onrender.com) to communicate with this backend
cors_origins_str = os.getenv("CORS_ORIGINS", "*") # Setting to * temporarily for debugging
origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the portfolio review routes
app.include_router(portfolio_review_router)

@app.get("/")
async def root():
    return {"message": "MRI-Int API is Live", "status": "healthy"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}
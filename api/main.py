import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import your portfolio router
from api.portfolio_review import router as portfolio_review_router

load_dotenv()

# THE FIX: Render looks for this 'app' variable to start the ASGI server
app = FastAPI(title="MRI-Int API")

# CORS Setup
cors_origins_str = os.getenv("CORS_ORIGINS", "https://mri-frontend.onrender.com")
origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach routes
app.include_router(portfolio_review_router)

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "MRI-Int API is live"}
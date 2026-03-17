import os
from fastapi import FastAPI, APIRouter, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import routers
from api.auth import router as auth_router
from api.signals import router as signals_router
from api.actions import router as actions_router
from api.portfolio import router as portfolio_router
from api.portfolio_review import router as portfolio_review_router
from api.email_debug import router as email_debug_router

load_dotenv()

app = FastAPI(title="MRI-Int API")

# Wide open CORS to stop the browser from blocking you
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth_router)
app.include_router(signals_router)
app.include_router(actions_router)
app.include_router(portfolio_router)
app.include_router(portfolio_review_router)
app.include_router(email_debug_router)

@app.get("/")
async def root():
    return {"message": "MRI-Int API is Live"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}
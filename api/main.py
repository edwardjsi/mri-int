import os
from fastapi import FastAPI, APIRouter, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import the portfolio router
from api.portfolio_review import router as portfolio_review_router

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

# --- MISSING AUTH ROUTE START ---
auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

@auth_router.post("/login")
async def login(email: str = Form(...), name: str = Form("User")):
    # This is a simple pass-through to let you into the dashboard
    return {
        "status": "success",
        "user": {"email": email, "name": name},
        "message": "Login successful"
    }

app.include_router(auth_router)
# --- MISSING AUTH ROUTE END ---

app.include_router(portfolio_review_router)

@app.get("/")
async def root():
    return {"message": "MRI-Int API is Live"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}
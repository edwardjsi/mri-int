import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 1. Import your routers - ensure these match your file names
# If you have a separate auth file, import it here too
from api.portfolio_review import router as portfolio_review_router

load_dotenv()

# THE CRITICAL VARIABLE: Render needs 'app'
app = FastAPI(title="MRI-Int API")

# CORS Setup: Allows your frontend to talk to this backend
cors_origins_str = os.getenv("CORS_ORIGINS", "https://mri-frontend.onrender.com")
origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Register the routes
app.include_router(portfolio_review_router)

# 3. Add a basic health check so we can see if it's alive
@app.get("/api/health")
async def health():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "API is running. Use /api/health to verify."}
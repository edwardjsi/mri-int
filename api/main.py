import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.portfolio_review import router as portfolio_review_router

app = FastAPI()

# This tells the backend: "Accept requests from ANYWHERE" 
# We do this just to get you logged in, then we can tighten it later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio_review_router)

@app.get("/api/health")
async def health():
    return {"status": "healthy"}
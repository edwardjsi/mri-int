import os
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mri_api")

# Import routers
from api.auth import router as auth_router
from api.signals import router as signals_router
from api.actions import router as actions_router
from api.portfolio import router as portfolio_router
from api.portfolio_review import router as portfolio_review_router
from api.email_debug import router as email_debug_router

load_dotenv()

app = FastAPI(title="MRI-Int API")

# Custom Exception Handler to log validation errors (very useful for debugging "missing field" issues)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error(f"Validation Error: {exc.errors()}")
    logger.error(f"Request Method: {request.method} URL: {request.url}")
    logger.error(f"Request Body: {body.decode() if body else 'EMPTY'}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": body.decode() if body else None},
    )

# Wide open CORS for dev; you should restrict this in production via CORS_ORIGINS env var
origins_str = os.getenv("CORS_ORIGINS", "*")
cors_origins = [o.strip() for o in origins_str.split(",")]

# Note: allow_origins=["*"] is NOT compatible with allow_credentials=True.
# We handle this defensively here.
allow_all = "*" in cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else cors_origins,
    allow_credentials=not allow_all,
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
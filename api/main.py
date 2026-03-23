import os
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
from api.watchlist import router as watchlist_router

load_dotenv()

app = FastAPI(title="MRI-Int API")

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

# Custom Exception Handler to log validation errors
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

# Wide open CORS for dev
origins_str = os.getenv("CORS_ORIGINS", "*")
cors_origins = [o.strip() for o in origins_str.split(",")]

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
app.include_router(watchlist_router)

# Serve Frontend Static Files
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    # Mount assets folder explicitly if it exists
    assets_path = os.path.join(static_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Allow API/Auth calls to pass through normally.
        if full_path.startswith("api/") or full_path.startswith("auth/"):
             return JSONResponse(status_code=404, content={"detail": "Not Found"})
            
        # For everything else, serve index.html (React Router handles it)
        file_path = os.path.join(static_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_path, "index.html"))

@app.get("/api/health")
async def health():
    return {"status": "healthy"}
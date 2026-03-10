"""
Database connection and JWT dependency helpers for the MRI API.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta

# ── Config ──────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET", "mri-dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security = HTTPBearer()


# ── Database ────────────────────────────────────────────────
def get_db():
    """Yield a psycopg2 connection with RealDictCursor."""
    database_url = os.getenv("DATABASE_URL")
    ssl_mode = os.getenv("DB_SSL", "false").lower() == "true"

    if database_url:
        # Cloud-native: Neon.tech / Render.com style
        conn = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor,
            sslmode="require" if ssl_mode else "prefer",
        )
    else:
        # Local dev / ECS with individual env vars
        connect_kwargs = dict(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5433"),
            dbname=os.getenv("DB_NAME", "mri_db"),
            user=os.getenv("DB_USER", "mri_admin"),
            password=os.getenv("DB_PASSWORD", ""),
            cursor_factory=RealDictCursor,
        )
        if ssl_mode:
            connect_kwargs["sslmode"] = "require"
        conn = psycopg2.connect(**connect_kwargs)
    try:
        yield conn
    finally:
        conn.close()


# ── JWT Helpers ─────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_client(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn=Depends(get_db),
):
    """Parse JWT and return client dict from DB. Raises 401 on failure."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        client_id: str = payload.get("sub")
        if client_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")

    cur = conn.cursor()
    cur.execute("SELECT id, email, name, is_active, initial_capital, created_at FROM clients WHERE id = %s", (client_id,))
    client = cur.fetchone()
    if not client or not client["is_active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Client not found or inactive")
    return client

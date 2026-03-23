"""
Authentication endpoints: register, login, profile.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
import bcrypt
import psycopg2.extras

from api.deps import get_db, create_access_token, get_current_client
from src.email_service import send_password_reset_email_detailed
from src.mailerlite import add_subscriber

router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ── Schemas ─────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str
    initial_capital: float = 100000.0


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    client_id: str
    name: Optional[str] = "User"
    email: str
    has_pending_signals: bool = False


# ── Endpoints ───────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, conn=Depends(get_db)):
    cur = conn.cursor()

    cur.execute("SELECT id FROM clients WHERE email = %s", (req.email,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(req.password)
    cur.execute(
        """INSERT INTO clients (email, name, password_hash, initial_capital)
           VALUES (%s, %s, %s, %s) RETURNING id""",
        (req.email, req.name, hashed, req.initial_capital),
    )
    client_id = str(cur.fetchone()["id"])
    conn.commit()

    # Add to MailerLite mailing list (non-blocking — never raises)
    add_subscriber(email=req.email, name=req.name)

    token = create_access_token({"sub": client_id})
    return TokenResponse(
        access_token=token,
        client_id=client_id,
        name=req.name,
        email=req.email,
        has_pending_signals=False  # New account has no signals yet
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, conn=Depends(get_db)):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, password_hash, is_active FROM clients WHERE email = %s",
        (req.email,),
    )
    client = cur.fetchone()

    if not client or not verify_password(req.password, client["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not client["is_active"]:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token({"sub": str(client["id"])})
    
    # Check for pending signals
    cur.execute("""
        SELECT 1 FROM client_signals cs
        LEFT JOIN client_actions ca ON ca.signal_id = cs.id
        WHERE cs.client_id = %s AND ca.id IS NULL
        LIMIT 1
    """, (str(client["id"]),))
    has_pending = cur.fetchone() is not None

    return TokenResponse(
        access_token=token,
        client_id=str(client["id"]),
        name=client["name"],
        email=req.email,
        has_pending_signals=has_pending
    )


@router.get("/me")
def get_profile(client=Depends(get_current_client), conn=Depends(get_db)):
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) AS added FROM capital_additions WHERE client_id = %s",
        (str(client["id"]),),
    )
    added = float(cur.fetchone()["added"])
    total = float(client["initial_capital"]) + added
    return {
        "id": str(client["id"]),
        "email": client["email"],
        "name": client["name"],
        "initial_capital": float(client["initial_capital"]),
        "added_capital": added,
        "total_capital": total,
        "created_at": str(client["created_at"]),
    }


class UpdateCapitalRequest(BaseModel):
    amount: float


@router.post("/capital")
def add_capital(req: UpdateCapitalRequest, client=Depends(get_current_client), conn=Depends(get_db)):
    """Add more capital to the client's account."""
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS capital_additions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES clients(id),
            amount NUMERIC(14,2) NOT NULL,
            added_at TIMESTAMPTZ DEFAULT NOW()
        )"""
    )
    cur.execute(
        "INSERT INTO capital_additions (client_id, amount) VALUES (%s, %s)",
        (str(client["id"]), req.amount),
    )
    conn.commit()
    return {"message": f"₹{req.amount:,.0f} added", "new_amount": req.amount}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, conn=Depends(get_db)):
    """Generate a reset token and send an email."""
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM clients WHERE email = %s", (req.email,))
    client = cur.fetchone()

    if not client:
        raise HTTPException(status_code=404, detail="No account found with that email address.")

    token = secrets.token_urlsafe(32)
    client_id = str(client["id"])

    cur.execute(
        """CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES clients(id),
            token VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )"""
    )

    expires_at = datetime.now() + timedelta(hours=1)
    try:
        cur.execute(
            """INSERT INTO password_reset_tokens (client_id, token, expires_at)
               VALUES (%s, %s, %s)""",
            (client_id, token, expires_at),
        )

        success, err = send_password_reset_email_detailed(req.email, client["name"], token)
        if not success:
            conn.rollback()
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to send reset email: {err}. "
                    "Check /api/email/debug?check_identity=true on the API service."
                ),
            )

        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate reset email: {e}")

    return {"message": "Password reset link sent! Please check your email."}


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, conn=Depends(get_db)):
    """Verify token and update password."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if hasattr(conn, "cursor_factory") else conn.cursor()

    cur.execute(
        """SELECT id, client_id FROM password_reset_tokens
           WHERE token = %s AND used = FALSE AND expires_at > NOW()""",
        (req.token,),
    )
    token_record = cur.fetchone()

    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token.")

    client_id = str(token_record["client_id"] if isinstance(token_record, dict) else token_record[1])
    token_id = str(token_record["id"] if isinstance(token_record, dict) else token_record[0])

    hashed = hash_password(req.new_password)

    cur.execute("UPDATE clients SET password_hash = %s WHERE id = %s", (hashed, client_id))
    cur.execute("UPDATE password_reset_tokens SET used = TRUE WHERE id = %s", (token_id,))

    conn.commit()
    return {"message": "Password successfully reset."}

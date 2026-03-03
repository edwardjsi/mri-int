"""
Authentication endpoints: register, login, profile.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
import bcrypt

from api.deps import get_db, create_access_token, get_current_client

router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))



# ── Schemas ─────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str
    initial_capital: float = 100000.0


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    client_id: str
    name: str


# ── Endpoints ───────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, conn=Depends(get_db)):
    cur = conn.cursor()

    # Check if email exists
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

    token = create_access_token({"sub": client_id})
    return TokenResponse(access_token=token, client_id=client_id, name=req.name)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, conn=Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT id, name, password_hash, is_active FROM clients WHERE email = %s", (req.email,))
    client = cur.fetchone()

    if not client or not verify_password(req.password, client["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not client["is_active"]:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token({"sub": str(client["id"])})
    return TokenResponse(access_token=token, client_id=str(client["id"]), name=client["name"])


@router.get("/me")
def get_profile(client=Depends(get_current_client), conn=Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount), 0) AS added FROM capital_additions WHERE client_id = %s", (str(client["id"]),))
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

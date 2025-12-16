from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
import hashlib
import secrets
import re
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.core.config import settings
from app.db.supabase_client import get_supabase

router = APIRouter()
security = HTTPBearer()

ACCOUNT_TYPES = {"business", "user"}


class UserCreate(BaseModel):
    email: EmailStr
    phone_number: str
    password: str
    first_name: str
    last_name: str
    business_name: Optional[str] = None
    account_type: Optional[str] = "business"
    business_handle: Optional[str] = None

    @validator("account_type", pre=True, always=True)
    def normalize_account_type(cls, value):
        normalized = (value or "business").lower()
        if normalized not in ACCOUNT_TYPES:
            raise ValueError("account_type must be 'business' or 'user'")
        return normalized

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    account_type: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

def hash_password(password: str) -> str:
    # Use SHA-256 with salt
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt, stored_hash = hashed_password.split(":")
        password_hash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
        return password_hash == stored_hash
    except:
        return False

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def _generate_business_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "business"
    return f"{slug}_{secrets.token_hex(4)}"


def _sanitize_business_handle(handle: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", handle.lower()).strip("_")
    return slug


def _normalize_account_type(account_type: Optional[str]) -> str:
    normalized = (account_type or "business").lower()
    if normalized not in ACCOUNT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid account type")
    return normalized


def _normalize_phone_number(phone_number: Optional[str]) -> str:
    if not phone_number:
        return ""
    value = phone_number.strip()
    if not value:
        return ""
    if value.startswith("00"):
        value = "+" + value[2:]
    cleaned = []
    for idx, ch in enumerate(value):
        if ch == "+" and idx == 0:
            cleaned.append(ch)
        elif ch.isdigit():
            cleaned.append(ch)
    normalized = "".join(cleaned)
    if normalized.startswith("+") and len(normalized) == 1:
        normalized = ""
    if len(normalized) > 32:
        normalized = normalized[:32]
    return normalized


@router.post("/signup", response_model=Token)
@router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    account_type = _normalize_account_type(user_data.account_type)
    normalized_phone = _normalize_phone_number(user_data.phone_number)
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="A valid phone number is required")
    # Check if user exists for the same role
    supabase = get_supabase()
    existing_user = (
        supabase
        .table("users")
        .select("id")
        .eq("email", user_data.email)
        .eq("account_type", account_type)
        .execute()
    )
    if existing_user.data:
        raise HTTPException(status_code=400, detail=f"Email already registered for {account_type} account")

    existing_phone = (
        supabase
        .table("users")
        .select("id")
        .eq("phone_number", normalized_phone)
        .eq("account_type", account_type)
        .execute()
    )
    if existing_phone.data:
        raise HTTPException(status_code=400, detail=f"Phone number already registered for {account_type} account")
    
    business_id = None
    business_name = None

    if account_type == "business":
        business_name = user_data.business_name or f"{user_data.first_name}'s Business"
        if user_data.business_handle:
            business_id = _sanitize_business_handle(user_data.business_handle)
            if not business_id:
                raise HTTPException(status_code=400, detail="Invalid business handle")
        else:
            business_id = _generate_business_id(business_name)

        business_data = {
            "business_id": business_id,
            "business_name": business_name,
            "whatsapp_number": normalized_phone,
            "default_language": "en",
            "supported_languages": ["en"],
            "inventory": [],
            "active": True,
        }

        try:
            supabase.table("businesses").insert(business_data).execute()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Unable to create business: {exc}") from exc
    else:
        if not user_data.phone_number:
            raise HTTPException(status_code=400, detail="Phone number is required for user accounts")

    # Create user linked to business if applicable
    user_data_dict = {
        "email": user_data.email,
        "phone_number": normalized_phone,
        "password_hash": hash_password(user_data.password),
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "business_name": business_name,
        "business_id": business_id,
        "account_type": account_type
    }
    
    result = supabase.table("users").insert(user_data_dict).execute()
    user = result.data[0]
    if business_id:
        supabase.table("businesses").update({"owner_user_id": user["id"]}).eq("business_id", business_id).execute()
    
    # Create token
    token_payload = {
        "sub": user["email"],
        "user_id": user["id"],
        "role": account_type,
        "account_type": account_type,
    }
    access_token = create_access_token(data=token_payload)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    supabase = get_supabase()
    requested_account_type = _normalize_account_type(user_data.account_type) if user_data.account_type else None

    query = supabase.table("users").select("*").eq("email", user_data.email)
    if requested_account_type:
        query = query.eq("account_type", requested_account_type)
    result = query.execute()

    records: List[dict] = result.data or []
    if not records:
        # Check whether the email exists for another account type to show a clearer error
        other_accounts = supabase.table("users").select("account_type").eq("email", user_data.email).execute()
        if other_accounts.data:
            available_roles = {row.get("account_type", "business") for row in other_accounts.data}
            raise HTTPException(
                status_code=403,
                detail=(
                    "This email is registered for the following roles: "
                    + ", ".join(sorted(available_roles))
                    + ". Please choose one of them when logging in."
                ),
            )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if len(records) > 1:
        raise HTTPException(
            status_code=400,
            detail="Multiple accounts were found for this email. Please select an account type to continue.",
        )

    user = records[0]
    if not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored_account_type = user.get("account_type", "business")
    
    # Update last login
    supabase.table("users").update({"last_login": datetime.utcnow().isoformat()}).eq("id", user["id"]).execute()

    token_payload = {
        "sub": user["email"],
        "user_id": user["id"],
        "role": stored_account_type,
        "account_type": stored_account_type,
    }
    access_token = create_access_token(data=token_payload)
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        email: Optional[str] = payload.get("sub")
        user_id = payload.get("user_id")
        token_account_type = payload.get("account_type") or payload.get("role")
        if email is None and user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    supabase = get_supabase()
    if user_id is not None:
        result = supabase.table("users").select("*").eq("id", user_id).execute()
    else:
        query = supabase.table("users").select("*").eq("email", email)
        if token_account_type:
            query = query.eq("account_type", token_account_type)
        result = query.execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="User not found")
    
    user = result.data[0]
    
    return user

def require_business_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("account_type") != "business":
        raise HTTPException(status_code=403, detail="Business account required")
    if not current_user.get("business_id"):
        raise HTTPException(status_code=403, detail="Business profile incomplete")
    return current_user


@router.get("/me")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "phone_number": current_user["phone_number"],
        "first_name": current_user["first_name"],
        "last_name": current_user["last_name"],
        "business_name": current_user.get("business_name"),
        "business_id": current_user.get("business_id"),
        "account_type": current_user.get("account_type", "business"),
        "preferred_language": current_user.get("preferred_language"),
        "is_verified": current_user.get("is_verified"),
        "created_at": current_user["created_at"]
    }
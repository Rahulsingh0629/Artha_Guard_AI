from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.database.models import User
from app.auth.jwt_manager import create_access_token, get_password_hash

router = APIRouter()

# ----------- SCHEMAS -----------

class UserRegister(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str
    phone_number: str

class UserLogin(BaseModel):
    email: str
    password: str

# ----------- REGISTER (NO OTP) -----------

@router.post("/register")
async def register(user_data: UserRegister):

    if await User.find_one(User.email == user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        hashed_password=get_password_hash(user_data.password),
        is_active=True   # ✅ ACTIVE IMMEDIATELY
    )

    await user.create()

    return {
        "status": "success",
        "message": "Registration successful. Please login.",
        "email": user_data.email
    }

# ----------- LOGIN -----------

@router.post("/login")
async def login(login_data: UserLogin):

    user = await User.find_one(User.email == login_data.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    from app.auth.jwt_manager import verify_password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    token = create_access_token({"sub": user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email,
        "id": str(user.id)
    }

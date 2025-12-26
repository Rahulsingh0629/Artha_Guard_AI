from fastapi import APIRouter, HTTPException, Depends
from app.database.models import User
from app.auth.jwt_manager import create_access_token, verify_password, get_password_hash
from pydantic import BaseModel

router = APIRouter()

# Schema for inputs
class UserRegister(BaseModel):
    email: str
    password: str
    phone_number: str

class UserLogin(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register(user_data: UserRegister):
    # 1. Check if user already exists (MongoDB style)
    existing_user = await User.find_one(User.email == user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Create new User Document
    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        phone_number=user_data.phone_number
    )
    
    # 3. Save to MongoDB
    await new_user.create()
    
    return {"message": "User registered successfully", "email": new_user.email}

@router.post("/login")
async def login(login_data: UserLogin):
    # 1. Find user (MongoDB style)
    user = await User.find_one(User.email == login_data.email)
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2. Generate Token
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}
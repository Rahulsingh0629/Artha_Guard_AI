import random
import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.database.models import User, OTPVerification
from app.auth.jwt_manager import create_access_token, get_password_hash

router = APIRouter()

# ----------- SCHEMAS -----------

class UserRegister(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str
    phone_number: str

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class UserLogin(BaseModel):
    email: str
    password: str

# ----------- SEND EMAIL VIA SENDGRID -----------

def send_email_otp(email: str, otp: str):
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))

        message = Mail(
            from_email=os.getenv("EMAIL_SENDER"),
            to_emails=email,
            subject="ArthaGuard OTP Verification",
            html_content=f"""
            <h3>ArthaGuard AI</h3>
            <p>Your OTP code is:</p>
            <h2>{otp}</h2>
            <p>This OTP is valid for 10 minutes.</p>
            """
        )

        sg.send(message)
        print("✅ OTP email sent via SendGrid")

    except Exception as e:
        print(f"❌ SendGrid email failed: {e}")

# ----------- REGISTER -----------

@router.post("/register")
async def register(user_data: UserRegister, background_tasks: BackgroundTasks):

    if await User.find_one(User.email == user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        hashed_password=get_password_hash(user_data.password),
        is_active=False
    )
    await user.create()

    otp = str(random.randint(100000, 999999))

    await OTPVerification.find(
        OTPVerification.email == user_data.email
    ).delete()

    await OTPVerification(
        email=user_data.email,
        phone_number=user_data.phone_number,
        otp_code=otp
    ).create()

    background_tasks.add_task(send_email_otp, user_data.email, otp)

    return {
        "status": "success",
        "message": "OTP sent successfully",
        "email": user_data.email
    }

# ----------- VERIFY OTP -----------

@router.post("/verify-otp")
async def verify_otp(data: VerifyOTPRequest):

    record = await OTPVerification.find_one(
        OTPVerification.email == data.email,
        OTPVerification.otp_code == data.otp
    )

    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user = await User.find_one(User.email == data.email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    user.is_active = True
    await user.save()

    await record.delete()

    return {
        "status": "success",
        "message": "Account verified successfully. Please login."
    }

# ----------- LOGIN -----------

@router.post("/login")
async def login(login_data: UserLogin):

    user = await User.find_one(User.email == login_data.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    from app.auth.jwt_manager import verify_password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account not verified")

    token = create_access_token({"sub": user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email,
        "id": str(user.id)
    }

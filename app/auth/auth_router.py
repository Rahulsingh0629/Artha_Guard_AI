import random
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from twilio.rest import Client

# Import Models
from app.database.models import User, OTPVerification
from app.auth.jwt_manager import create_access_token, get_password_hash

router = APIRouter()

# --- INPUT SCHEMAS ---
# Updated to match your Android Register Screen
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

# --- HELPER: SEND OTP ---
def send_otp_background(email: str, phone: str, otp: str):
    """
    Sends OTP via Email (SMTP) and SMS (Twilio)
    """
    print(f"🔐 GENERATED OTP for {email}: {otp}") # Console log for testing
    
    # 1. Send Email
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD")
    if sender_email and sender_password:
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email
            msg['Subject'] = "ArthaGuard Verification Code"
            msg.attach(MIMEText(f"Your OTP is: {otp}", 'plain'))
            
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
        except Exception as e:
            print(f"❌ Email Failed: {e}")

    # 2. Send SMS (Twilio)
    twilio_sid = os.getenv("TWILIO_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
    
    if twilio_sid and twilio_token and twilio_phone:
        try:
            client = Client(twilio_sid, twilio_token)
            client.messages.create(
                body=f"Your ArthaGuard OTP is: {otp}",
                from_=twilio_phone,
                to=phone
            )
        except Exception as e:
            print(f"❌ SMS Failed: {e}")

# --- ROUTE 1: REGISTER (Step 1) ---
@router.post("/register")
async def register(user_data: UserRegister, background_tasks: BackgroundTasks):
    """
    1. Saves user details to MongoDB (marked as inactive).
    2. Generates OTP.
    3. Sends OTP via Email/SMS.
    """
    # 1. Check if email already exists
    if await User.find_one(User.email == user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Create User (Inactive until OTP verified)
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,     # Now saving Full Name
        # Note: 'username' isn't in your User model yet, usually email is username. 
        # You can add 'username' field to models.py if strict about it.
        phone_number=user_data.phone_number,
        hashed_password=get_password_hash(user_data.password),
        is_active=False # <--- Important: Not active yet!
    )
    await new_user.create()

    # 3. Generate 6-digit OTP
    otp_code = str(random.randint(100000, 999999))

    # 4. Save OTP to DB (Overwrites old OTP if exists)
    # First, delete any existing OTP for this email
    await OTPVerification.find(OTPVerification.email == user_data.email).delete()
    
    otp_entry = OTPVerification(
        email=user_data.email,
        phone_number=user_data.phone_number,
        otp_code=otp_code
    )
    await otp_entry.create()

    # 5. Send OTP in Background (Fast Response)
    background_tasks.add_task(send_otp_background, user_data.email, user_data.phone_number, otp_code)

    return {
        "status": "success", 
        "message": "OTP sent successfully", 
        "email": user_data.email
    }

# --- ROUTE 2: VERIFY OTP (Step 2) ---
@router.post("/verify-otp")
async def verify_otp(data: VerifyOTPRequest):
    """
    1. Checks OTP.
    2. Activates the User account.
    """
    # 1. Find the OTP record
    record = await OTPVerification.find_one(
        OTPVerification.email == data.email,
        OTPVerification.otp_code == data.otp
    )

    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # 2. Activate the User
    user = await User.find_one(User.email == data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    await user.save()

    # 3. Delete the used OTP
    await record.delete()

    return {"status": "success", "message": "Account verified successfully! Please login."}

# --- ROUTE 3: LOGIN ---
@router.post("/login")
async def login(login_data: UserLogin):
    # 1. Find User
    user = await User.find_one(User.email == login_data.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # 2. Check Password (assuming helper exists)
    # Note: Import verify_password from your jwt_manager or security file
    from app.auth.jwt_manager import verify_password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # 3. Check if Active
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account not verified. Please verify OTP.")

    # 4. Generate Token
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "email": user.email, "id": str(user.id)}
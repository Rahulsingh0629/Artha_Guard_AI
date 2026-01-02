import random
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from twilio.rest import Client
from dotenv import load_dotenv  # <--- IMPORT THIS

# Load environment variables immediately
load_dotenv()

# Import Models
from app.database.models import User, OTPVerification
from app.auth.jwt_manager import create_access_token, get_password_hash

router = APIRouter()

# ... [Input Schemas remain the same] ...
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
    print(f"🔐 [DEBUG] Generating OTP for {email}: {otp}")
    
    # --- 1. EMAIL LOGIC ---
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD")
    
    # Debug print to check if keys are loaded
    if not sender_email or not sender_password:
        print("❌ [ERROR] Email credentials missing in .env! Email not sent.")
    else:
        try:
            print(f"📧 Attempting to send email to {email}...")
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email
            msg['Subject'] = "ArthaGuard Verification Code"
            msg.attach(MIMEText(f"Your OTP is: {otp}", 'plain'))
            
            # Using port 587 for TLS
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            print("✅ Email sent successfully!")
        except Exception as e:
            print(f"❌ Email Failed: {str(e)}")

    # --- 2. SMS LOGIC (Twilio) ---
    twilio_sid = os.getenv("TWILIO_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
    
    if not twilio_sid or not twilio_token:
        print("❌ [ERROR] Twilio credentials missing in .env! SMS not sent.")
    else:
        try:
            print(f"📱 Attempting to send SMS to {phone}...")
            client = Client(twilio_sid, twilio_token)
            client.messages.create(
                body=f"Your ArthaGuard OTP is: {otp}",
                from_=twilio_phone,
                to=phone
            )
            print("✅ SMS sent successfully!")
        except Exception as e:
            print(f"❌ SMS Failed: {str(e)}")
            print("   (Hint: If using Twilio Trial, ensure the 'to' number is verified)")

# ... [Routes remain the same] ...
@router.post("/register")
async def register(user_data: UserRegister, background_tasks: BackgroundTasks):
    # 1. Check if email already exists
    if await User.find_one(User.email == user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Create User (Inactive)
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        hashed_password=get_password_hash(user_data.password),
        is_active=False 
    )
    await new_user.create()

    # 3. Generate OTP
    otp_code = str(random.randint(100000, 999999))

    # 4. Save OTP
    await OTPVerification.find(OTPVerification.email == user_data.email).delete()
    
    otp_entry = OTPVerification(
        email=user_data.email,
        phone_number=user_data.phone_number,
        otp_code=otp_code
    )
    await otp_entry.create()

    # 5. Send OTP
    background_tasks.add_task(send_otp_background, user_data.email, user_data.phone_number, otp_code)

    return {
        "status": "success", 
        "message": "OTP sent successfully", 
        "email": user_data.email
    }

# ... [Verify and Login routes remain exactly as they were] ...
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
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    await user.save()
    await record.delete()

    return {"status": "success", "message": "Account verified successfully! Please login."}

@router.post("/login")
async def login(login_data: UserLogin):
    user = await User.find_one(User.email == login_data.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    from app.auth.jwt_manager import verify_password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account not verified. Please verify OTP.")

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "email": user.email, "id": str(user.id)}
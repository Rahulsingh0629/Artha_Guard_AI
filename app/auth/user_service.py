from sqlalchemy.orm import Session
from app.database.models import User, UserPlan # Import the Enum class
from app.core.security import get_password_hash
from pydantic import BaseModel, EmailStr

# Input Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    username: str
    password: str

def create_new_user(user: UserCreate, db: Session):
    # 1. Check if email exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        return None 
    
    # 2. Create new user
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        password_hash=get_password_hash(user.password),
        
        # --- THE FIX ---
        # We explicitly use the Enum member. 
        # SQLAlchemy will extract the value "free" automatically.
        plan_type=UserPlan.FREE.value,  
        
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
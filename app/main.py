# ... existing imports ...
from app.auth import auth_router # <--- Import this
from app.database.mongodb import init_db
from fastapi import FastAPI
from app.api import portfolio_routes
from app.api import news_routes
from app.api import scanner_routes
from app.api import advisory_routes
from app.api import fraud_routes


app = FastAPI()

@app.on_event("startup")
async def start_database():
    
    await init_db()
    print("✅ Connected to MongoDB successfully!")

# Register the Auth Router
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])

# Register the Portfolio Router
app.include_router(portfolio_routes.router, prefix="/api/v1/portfolio", tags=["Portfolio"])

# Register the News Router
app.include_router(news_routes.router, prefix="/api/v1/news", tags=["News"])

# Register the Scanner Router
app.include_router(scanner_routes.router, prefix="/api/v1/scanner", tags=["Scanner"])

# Register the Advisory Router
app.include_router(advisory_routes.router, prefix="/api/v1/advisory", tags=["Advisory Agent"])

app.include_router(fraud_routes.router, prefix="/api/v1/fraud", tags=["Fraud Agent"])
# ... existing tip_routes include ...

@app.get("/")
def read_root():
    return {
        "project": "ArthaGuard AI", 
        "status": "active", 
        "message": "Backend is running smoothly! Visit /docs for the API."
    }
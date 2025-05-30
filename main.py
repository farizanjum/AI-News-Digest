import os
from dotenv import load_dotenv
import hashlib
import hmac
import secrets
import logging
from urllib.parse import unquote

# Load environment variables
load_dotenv()

# Configure logging for serverless
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"🚀 Starting AI News Digest Platform...")

from fastapi import FastAPI, Depends, HTTPException, Request, Form, Query, BackgroundTasks, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from typing import List, Optional
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
import urllib.parse
import asyncio
import html
import re
import time
from collections import defaultdict

# Initialize FastAPI app first
app = FastAPI(title="AI News Digest Platform", description="Autonomous News Digest with AI Curation")

# Global flags
DATABASE_AVAILABLE = False
SERVICES_AVAILABLE = False

# Check database availability
def check_database():
    global DATABASE_AVAILABLE
    try:
        from sqlalchemy.orm import Session
        from sqlalchemy import create_engine
        import database.models as models
        from database.models import Base
        from database.database import get_db, create_tables, init_database
        
        # Use PostgreSQL if DATABASE_URL is provided, otherwise SQLite
        db_url = os.getenv('DATABASE_URL', 'sqlite:///./news_digest.db')
        engine = create_engine(db_url)
        Base.metadata.create_all(bind=engine)
        create_tables()
        init_database()
        DATABASE_AVAILABLE = True
        logger.info("✅ Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Database not available: {e}")
        DATABASE_AVAILABLE = False
        return False

# Check services availability
def check_services():
    global SERVICES_AVAILABLE
    try:
        from services.email_service import EmailService
        from services.news_service import NewsService
        SERVICES_AVAILABLE = True
        logger.info("✅ Services available")
        return True
    except Exception as e:
        logger.error(f"⚠️ Services not available: {e}")
        SERVICES_AVAILABLE = False
        return False

# Lazy initialization
def get_db_session():
    if not DATABASE_AVAILABLE:
        return None
    try:
        from database.database import SessionLocal
        return SessionLocal()
    except:
        return None

def get_db():
    db = get_db_session()
    if db:
        try:
            yield db
        finally:
            db.close()
    else:
        yield None

# Security configuration
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY')
UNSUBSCRIBE_SECRET = os.getenv('UNSUBSCRIBE_SECRET', secrets.token_urlsafe(32))

# Security tracking
failed_attempts = defaultdict(list)
blocked_ips = defaultdict(float)
MAX_ATTEMPTS = 3
BLOCK_DURATION = 300  # 5 minutes

def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def is_ip_blocked(ip: str) -> bool:
    """Check if IP is currently blocked."""
    if ip in blocked_ips:
        if time.time() < blocked_ips[ip]:
            return True
        else:
            del blocked_ips[ip]
            if ip in failed_attempts:
                del failed_attempts[ip]
    return False

def record_failed_attempt(ip: str):
    """Record a failed login attempt."""
    current_time = time.time()
    failed_attempts[ip] = [
        attempt_time for attempt_time in failed_attempts[ip] 
        if current_time - attempt_time < 3600
    ]
    failed_attempts[ip].append(current_time)
    if len(failed_attempts[ip]) >= MAX_ATTEMPTS:
        blocked_ips[ip] = current_time + BLOCK_DURATION
        logger.warning(f"🔒 IP {ip} blocked due to {len(failed_attempts[ip])} failed attempts")

def verify_admin_key(request: Request, api_key: str = Header(None, alias="X-Admin-Key")):
    """Enhanced admin API key verification with rate limiting."""
    client_ip = get_client_ip(request)
    
    if is_ip_blocked(client_ip):
        remaining_time = int(blocked_ips[client_ip] - time.time())
        raise HTTPException(
            status_code=429, 
            detail=f"Too many failed attempts. Try again in {remaining_time} seconds."
        )
    
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="Admin authentication not configured")
    
    if not api_key or api_key != ADMIN_API_KEY:
        record_failed_attempt(client_ip)
        attempts_left = MAX_ATTEMPTS - len(failed_attempts[client_ip])
        if attempts_left <= 0:
            raise HTTPException(status_code=429, detail="Account locked. Too many failed attempts.")
        raise HTTPException(
            status_code=401, 
            detail=f"Invalid admin key. {attempts_left} attempts remaining."
        )
    
    if client_ip in failed_attempts:
        del failed_attempts[client_ip]
    
    return True

def generate_unsubscribe_token(email: str) -> str:
    """Generate secure unsubscribe token."""
    if not UNSUBSCRIBE_SECRET:
        raise ValueError("Unsubscribe secret not configured")
    message = f"{email}:unsubscribe"
    return hmac.new(UNSUBSCRIBE_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

def verify_unsubscribe_token(email: str, token: str) -> bool:
    """Verify unsubscribe token."""
    expected_token = generate_unsubscribe_token(email)
    return hmac.compare_digest(expected_token, token)

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')

# Initialize services with error handling
email_service = None
news_service = None

def get_email_service():
    global email_service
    if email_service is None and SERVICES_AVAILABLE:
        try:
            from services.email_service import EmailService
            email_service = EmailService()
            logger.info("✅ Email service initialized")
        except Exception as e:
            logger.error(f"❌ Email service initialization error: {e}")
    return email_service

def get_news_service():
    global news_service
    if news_service is None and SERVICES_AVAILABLE:
        try:
            from services.news_service import NewsService
            news_service = NewsService()
            logger.info("✅ News service initialized")
        except Exception as e:
            logger.error(f"❌ News service initialization error: {e}")
    return news_service

# Pydantic models
class SubscriberCreate(BaseModel):
    email: EmailStr
    name: str
    preferences: str = "all"
    digest_type: str = "tech"

class SubscriberResponse(BaseModel):
    id: int
    email: str
    name: str
    preferences: str
    digest_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PreferencesUpdate(BaseModel):
    email: EmailStr
    preferences: str
    digest_type: str = "tech"

class ContactForm(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str
    
    @validator('name')
    def validate_name(cls, v):
        v = html.escape(v.strip())
        if len(v) < 2 or len(v) > 100:
            raise ValueError('Name must be between 2 and 100 characters')
        if not re.match(r'^[a-zA-Z\s\-\.]+$', v):
            raise ValueError('Name contains invalid characters')
        return v
    
    @validator('subject')
    def validate_subject(cls, v):
        v = html.escape(v.strip())
        if len(v) < 5 or len(v) > 200:
            raise ValueError('Subject must be between 5 and 200 characters')
        return v
    
    @validator('message')
    def validate_message(cls, v):
        v = html.escape(v.strip())
        if len(v) < 10 or len(v) > 5000:
            raise ValueError('Message must be between 10 and 5000 characters')
        return v

class UnsubscribeTokenRequest(BaseModel):
    email: EmailStr

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 AI News Digest starting up...")
    check_database()
    check_services()
    
    # Try to mount static files
    try:
        from fastapi.staticfiles import StaticFiles
        app.mount("/static", StaticFiles(directory="static"), name="static")
        logger.info("✅ Static files mounted")
    except Exception as e:
        logger.warning(f"⚠️ Static files not available: {e}")
    
    logger.info("✅ Startup complete!")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for debugging deployment."""
    return {
        "status": "healthy",
        "database_available": DATABASE_AVAILABLE,
        "services_available": SERVICES_AVAILABLE,
        "admin_configured": bool(ADMIN_API_KEY),
        "email_configured": bool(SENDER_EMAIL and SENDER_PASSWORD),
        "environment": "serverless" if os.getenv("VERCEL") else "local",
        "message": "🚀 AI News Digest Platform is running!",
        "version": "2.0.0"
    }

# Main routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with beautiful template."""
    try:
        from fastapi.templating import Jinja2Templates
        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Template error: {e}")
        # Minimal fallback only if templates completely fail
        raise HTTPException(status_code=500, detail="Template service unavailable")

@app.get("/subscribe", response_class=HTMLResponse)
async def subscribe_page(request: Request):
    """Subscribe page with beautiful template."""
    try:
        from fastapi.templating import Jinja2Templates
        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("subscribe.html", {"request": request})
    except Exception as e:
        logger.error(f"Template error: {e}")
        raise HTTPException(status_code=500, detail="Template service unavailable")

@app.post("/subscribe", response_model=SubscriberResponse)
def create_subscriber(subscriber: SubscriberCreate, db = Depends(get_db)):
    """Create a new subscriber."""
    if not DATABASE_AVAILABLE or not db:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        import database.models as models
        
        # Check if email already exists
        existing_subscriber = db.query(models.Subscriber).filter(models.Subscriber.email == subscriber.email).first()
        if existing_subscriber:
            if existing_subscriber.is_active:
                raise HTTPException(status_code=400, detail="Email already subscribed")
            else:
                # Reactivate existing subscriber
                existing_subscriber.is_active = True
                existing_subscriber.name = subscriber.name
                existing_subscriber.preferences = subscriber.preferences
                existing_subscriber.digest_type = subscriber.digest_type
                existing_subscriber.updated_at = datetime.now()
                db.commit()
                db.refresh(existing_subscriber)
                
                # Send welcome email
                try:
                    email_svc = get_email_service()
                    if email_svc:
                        email_svc.send_welcome_email(
                            existing_subscriber.email, 
                            existing_subscriber.name, 
                            existing_subscriber.preferences,
                            existing_subscriber.digest_type
                        )
                except Exception as e:
                    logger.warning(f"Could not send welcome email: {e}")
                
                return existing_subscriber
        
        # Create new subscriber
        db_subscriber = models.Subscriber(
            email=subscriber.email,
            name=subscriber.name,
            preferences=subscriber.preferences,
            digest_type=subscriber.digest_type,
            is_active=True
        )
        db.add(db_subscriber)
        db.commit()
        db.refresh(db_subscriber)
        
        # Send welcome email
        try:
            email_svc = get_email_service()
            if email_svc:
                email_svc.send_welcome_email(
                    db_subscriber.email, 
                    db_subscriber.name, 
                    db_subscriber.preferences,
                    db_subscriber.digest_type
                )
        except Exception as e:
            logger.warning(f"Could not send welcome email: {e}")
        
        return db_subscriber
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscription error: {e}")
        raise HTTPException(status_code=500, detail="Subscription service error")

@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    """Contact page with beautiful template."""
    try:
        from fastapi.templating import Jinja2Templates
        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("contact.html", {"request": request})
    except Exception as e:
        logger.error(f"Template error: {e}")
        raise HTTPException(status_code=500, detail="Template service unavailable")

@app.post("/contact")
async def submit_contact(contact: ContactForm, db = Depends(get_db)):
    """Handle contact form submission."""
    try:
        logger.info(f"📧 Contact form submitted by {contact.email}")
        
        # Try to save to database if available
        if DATABASE_AVAILABLE and db:
            try:
                import database.models as models
                contact_message = models.ContactMessage(
                    name=contact.name,
                    email=contact.email,
                    subject=contact.subject,
                    message=contact.message
                )
                db.add(contact_message)
                db.commit()
                logger.info("✅ Contact message saved to database")
            except Exception as e:
                logger.error(f"❌ Database save error: {e}")
        
        # Try to send email if configured
        if SENDER_EMAIL and SENDER_PASSWORD:
            try:
                msg = MIMEText(f"From: {contact.name} ({contact.email})\nSubject: {contact.subject}\n\nMessage:\n{contact.message}")
                msg['From'] = SENDER_EMAIL
                msg['To'] = "contact.ainewsdigest@gmail.com"
                msg['Subject'] = f"Contact Form: {contact.subject}"
                
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                    server.starttls()
                    server.login(SENDER_EMAIL, SENDER_PASSWORD)
                    server.send_message(msg)
                
                logger.info("✅ Contact email sent successfully")
            except Exception as e:
                logger.error(f"❌ Email send error: {e}")
        
        return {"message": "Thank you for your message! We'll get back to you soon. 😊"}
        
    except Exception as e:
        logger.error(f"Contact form error: {e}")
        return {"message": "Thank you for your message. It has been received! 👍"}

# Admin routes
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔐 Admin Login - AI News Digest</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: 'Segoe UI', sans-serif; max-width: 400px; margin: 100px auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; }
            .login-container { background: rgba(255,255,255,0.1); padding: 40px; border-radius: 20px; backdrop-filter: blur(10px); }
            .form-group { margin: 20px 0; }
            label { display: block; margin-bottom: 8px; font-weight: bold; }
            input { width: 100%; padding: 12px; border: none; border-radius: 8px; background: rgba(255,255,255,0.9); color: #333; }
            button { width: 100%; background: linear-gradient(45deg, #ff6b6b, #ee5a24); color: white; padding: 15px; border: none; border-radius: 50px; cursor: pointer; font-weight: bold; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="login-container">
            <h2>🔐 Admin Login</h2>
            <form method="post" action="/api/admin/login">
                <div class="form-group">
                    <label for="api_key">Admin API Key:</label>
                    <input type="password" id="api_key" name="api_key" required>
                </div>
                <button type="submit">🚀 Login</button>
            </form>
            <p style="text-align: center; margin-top: 20px;">
                <a href="/" style="color: white;">← Back to Home</a>
            </p>
        </div>
    </body>
    </html>
    """)

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: bool = Depends(verify_admin_key)):
    """Admin dashboard with beautiful template."""
    try:
        from fastapi.templating import Jinja2Templates
        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("admin_dashboard.html", {"request": request})
    except Exception as e:
        logger.error(f"Template error: {e}")
        raise HTTPException(status_code=500, detail="Template service unavailable")

@app.get("/api/stats")
async def get_stats(request: Request, admin: bool = Depends(verify_admin_key)):
    """Get platform statistics."""
    try:
        if DATABASE_AVAILABLE:
            import database.models as models
            db = get_db_session()
            if db:
                total_subscribers = db.query(models.Subscriber).filter(models.Subscriber.is_active == True).count()
                tech_subscribers = db.query(models.Subscriber).filter(
                    models.Subscriber.is_active == True,
                    models.Subscriber.digest_type.in_(["tech", "both"])
                ).count()
                upsc_subscribers = db.query(models.Subscriber).filter(
                    models.Subscriber.is_active == True,
                    models.Subscriber.digest_type.in_(["upsc", "both"])
                ).count()
                db.close()
                return {
                    "total_subscribers": total_subscribers,
                    "tech_subscribers": tech_subscribers,
                    "upsc_subscribers": upsc_subscribers,
                    "emails_sent_today": 0,  # TODO: Implement email tracking
                    "status": "operational"
                }
        
        return {
            "total_subscribers": 0,
            "tech_subscribers": 0,
            "upsc_subscribers": 0,
            "emails_sent_today": 0,
            "status": "limited_mode"
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": str(e), "total_subscribers": 0}

@app.post("/api/admin/login")
async def admin_login_api(request: Request, api_key: str = Form(...)):
    """Admin login API with rate limiting."""
    client_ip = get_client_ip(request)
    
    if is_ip_blocked(client_ip):
        remaining_time = int(blocked_ips[client_ip] - time.time())
        raise HTTPException(
            status_code=429, 
            detail=f"Too many failed attempts. Try again in {remaining_time} seconds."
        )
    
    if not ADMIN_API_KEY or api_key != ADMIN_API_KEY:
        record_failed_attempt(client_ip)
        attempts_left = MAX_ATTEMPTS - len(failed_attempts[client_ip])
        if attempts_left <= 0:
            raise HTTPException(status_code=429, detail="Account locked. Too many failed attempts.")
        raise HTTPException(
            status_code=401, 
            detail=f"Invalid admin key. {attempts_left} attempts remaining."
        )
    
    if client_ip in failed_attempts:
        del failed_attempts[client_ip]
    
    return {"message": "Login successful", "redirect": "/admin/dashboard"}

@app.post("/api/generate-unsubscribe-token")
async def generate_unsubscribe_token_api(request: UnsubscribeTokenRequest, db = Depends(get_db)):
    """Generate unsubscribe token for a given email."""
    if not DATABASE_AVAILABLE or not db:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    import database.models as models
    subscriber = db.query(models.Subscriber).filter(models.Subscriber.email == request.email).first()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Email not found in our records")
    
    if not subscriber.is_active:
        raise HTTPException(status_code=400, detail="This email is already unsubscribed")
    
    token = generate_unsubscribe_token(request.email)
    return {"token": token}

# Mangum handler for Vercel serverless deployment
def create_handler():
    """Create the ASGI handler for Vercel deployment."""
    try:
        from mangum import Mangum
        return Mangum(app)
    except ImportError:
        logger.info("Mangum not available - using direct app")
        return app
    except Exception as e:
        logger.error(f"Mangum initialization failed: {e} - using direct app")
        return app

# Create handler for Vercel
handler = create_handler()

logger.info("🎉 Handler and app export initialized for deployment")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
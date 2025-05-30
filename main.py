import os
from dotenv import load_dotenv
import hashlib
import hmac
import secrets
import logging
from urllib.parse import unquote
import asyncio

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"🚀 Starting AI News Digest Platform with Supabase...")

from fastapi import FastAPI, Depends, HTTPException, Request, Form, Query, BackgroundTasks, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
import html
import re
import time
from collections import defaultdict

# Initialize FastAPI app
app = FastAPI(title="AI News Digest Platform", description="Autonomous News Digest with AI Curation")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("✅ Static files mounted")
except Exception as e:
    logger.warning(f"⚠️ Static files not available: {e}")

# Initialize templates
templates = Jinja2Templates(directory="templates")
logger.info("✅ Templates initialized")

# Import Supabase client
from database.supabase_client import supabase_client

# Global flags
DATABASE_AVAILABLE = False

# Security configuration
ADMIN_API_KEY = "AlP6rApaPAqjFyaEWqXm4L_pF1yR5lg__YRSsRMwLOU"
UNSUBSCRIBE_SECRET = "7x2s9OV5X3Z60WXTsWYirwf_1Iq9H_ngZAxwPCXmeGo"

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'subscribe.ainewsdigest@gmail.com')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')

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

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    global DATABASE_AVAILABLE
    logger.info("🚀 AI News Digest starting up with Supabase...")
    
    try:
        # Initialize Supabase
        success = await supabase_client.init_pool()
        if success:
            await supabase_client.create_tables()
            DATABASE_AVAILABLE = True
            logger.info("✅ Supabase database initialized successfully")
        else:
            logger.error("❌ Failed to initialize Supabase")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
    
    logger.info("✅ Startup complete!")

@app.on_event("shutdown")
async def shutdown_event():
    await supabase_client.close()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database_available": DATABASE_AVAILABLE,
        "admin_configured": bool(ADMIN_API_KEY),
        "email_configured": bool(SENDER_EMAIL and SENDER_PASSWORD),
        "environment": "serverless" if os.getenv("VERCEL") else "local",
        "message": "🚀 AI News Digest Platform is running with Supabase!",
        "version": "3.0.0"
    }

# Main routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with beautiful template."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/subscribe", response_class=HTMLResponse)
async def subscribe_page(request: Request):
    """Subscribe page with beautiful template."""
    return templates.TemplateResponse("subscribe.html", {"request": request})

@app.post("/subscribe")
async def create_subscriber(
    name: str = Form(...),
    email: str = Form(...),
    digest_type: str = Form(...),
    preferences: str = Form(default="all")
):
    """Create a new subscriber."""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        result = await supabase_client.add_subscriber(email, name, preferences, digest_type)
        
        if result["status"] == "exists":
            raise HTTPException(status_code=400, detail="Email already subscribed")
        
        # Send welcome email
        if SENDER_EMAIL and SENDER_PASSWORD:
            try:
                msg = MIMEMultipart('alternative')
                msg['From'] = SENDER_EMAIL
                msg['To'] = email
                msg['Subject'] = "Welcome to AI News Digest! 🚀"
                
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 20px; color: white; text-align: center;">
                        <h1>Welcome to AI News Digest! 🚀</h1>
                        <p>Hi {name},</p>
                        <p>Thank you for subscribing to our {digest_type.title()} digest!</p>
                        <p>You'll receive your personalized news digest daily at 8:00 PM.</p>
                        <p>Your preferences: {preferences}</p>
                        <hr style="margin: 30px 0; border: 1px solid rgba(255,255,255,0.3);">
                        <p style="font-size: 14px; opacity: 0.8;">
                            You can unsubscribe anytime by replying to any digest email.
                        </p>
                    </div>
                </body>
                </html>
                """
                
                msg.attach(MIMEText(html_content, 'html'))
                
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                    server.starttls()
                    server.login(SENDER_EMAIL, SENDER_PASSWORD)
                    server.send_message(msg)
                
                await supabase_client.log_email(email, "welcome", "Welcome to AI News Digest! 🚀", "sent")
            except Exception as e:
                logger.warning(f"Could not send welcome email: {e}")
                await supabase_client.log_email(email, "welcome", "Welcome to AI News Digest! 🚀", "failed", str(e))
        
        return RedirectResponse(url="/?subscribed=true", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscription error: {e}")
        raise HTTPException(status_code=500, detail="Subscription service error")

@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    """Contact page with beautiful template."""
    return templates.TemplateResponse("contact.html", {"request": request})

@app.post("/contact")
async def submit_contact(
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...)
):
    """Handle contact form submission."""
    try:
        logger.info(f"📧 Contact form submitted by {email}")
        
        # Save to database
        if DATABASE_AVAILABLE:
            await supabase_client.add_contact_message(name, email, subject, message)
        
        # Send email notification
        if SENDER_EMAIL and SENDER_PASSWORD:
            try:
                msg = MIMEText(f"From: {name} ({email})\nSubject: {subject}\n\nMessage:\n{message}")
                msg['From'] = SENDER_EMAIL
                msg['To'] = "contact.ainewsdigest@gmail.com"
                msg['Subject'] = f"Contact Form: {subject}"
                
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                    server.starttls()
                    server.login(SENDER_EMAIL, SENDER_PASSWORD)
                    server.send_message(msg)
                
                logger.info("✅ Contact email sent successfully")
            except Exception as e:
                logger.error(f"❌ Email send error: {e}")
        
        return RedirectResponse(url="/contact?sent=true", status_code=303)
        
    except Exception as e:
        logger.error(f"Contact form error: {e}")
        return RedirectResponse(url="/contact?error=true", status_code=303)

# Admin routes
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    """Admin login page with beautiful template."""
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: bool = Depends(verify_admin_key)):
    """Admin dashboard with beautiful template."""
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

@app.get("/api/stats")
async def get_stats(request: Request, admin: bool = Depends(verify_admin_key)):
    """Get platform statistics."""
    try:
        if DATABASE_AVAILABLE:
            stats = await supabase_client.get_subscriber_stats()
            stats["emails_sent_today"] = 0  # TODO: Implement from email_logs
            stats["status"] = "operational"
            return stats
        
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
        return RedirectResponse(url="/admin/login?error=invalid", status_code=303)
    
    if client_ip in failed_attempts:
        del failed_attempts[client_ip]
    
    # Set admin key in session (simplified for demo)
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie("admin_session", api_key, httponly=True, secure=True)
    return response

@app.post("/api/generate-unsubscribe-token")
async def generate_unsubscribe_token_api(request: UnsubscribeTokenRequest):
    """Generate unsubscribe token for a given email."""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    subscribers = await supabase_client.get_subscribers()
    subscriber_emails = [s['email'] for s in subscribers]
    
    if request.email not in subscriber_emails:
        raise HTTPException(status_code=404, detail="Email not found in our records")
    
    token = generate_unsubscribe_token(request.email)
    return {"token": token}

@app.get("/unsubscribe")
async def unsubscribe_page(request: Request, email: str = Query(...), token: str = Query(...)):
    """Unsubscribe page."""
    if not verify_unsubscribe_token(email, token):
        raise HTTPException(status_code=400, detail="Invalid unsubscribe link")
    
    success = await supabase_client.unsubscribe_user(email)
    return templates.TemplateResponse("unsubscribe.html", {
        "request": request, 
        "email": email, 
        "success": success
    })

# Mangum handler for Vercel
try:
    from mangum import Mangum
    handler = Mangum(app)
    logger.info("✅ Mangum handler created for Vercel deployment")
except ImportError:
    logger.info("⚠️ Mangum not available - using direct app")
    handler = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
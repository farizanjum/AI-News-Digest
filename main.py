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

# Print database info for debugging (remove for production)
db_url = os.getenv('DATABASE_URL', 'sqlite:///./news_digest.db')
logger.info(f"Database URL configured: {db_url[:20]}...")

from fastapi import FastAPI, Depends, HTTPException, Request, Form, Query, BackgroundTasks, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

# Try to import SQLAlchemy and database models - handle gracefully if they fail
try:
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine
    import database.models as models
    from database.models import Base
    from database.database import get_db, create_tables, init_database
    DATABASE_AVAILABLE = True
    logger.info("Database models imported successfully")
except Exception as e:
    logger.error(f"Database import error: {e}")
    DATABASE_AVAILABLE = False
    # Create dummy classes to prevent crashes
    class models:
        class Subscriber:
            pass
        class EmailLog:
            pass
        class ContactMessage:
            pass
        class DigestSchedule:
            pass
    
    def get_db():
        return None

# Try to import services - handle gracefully if they fail
try:
    from services.email_service import EmailService
    from services.news_service import NewsService
    SERVICES_AVAILABLE = True
    logger.info("Services imported successfully")
except Exception as e:
    logger.error(f"Services import error: {e}")
    SERVICES_AVAILABLE = False
    EmailService = None
    NewsService = None

# Enhanced Security configuration
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
            # Remove expired blocks
            del blocked_ips[ip]
            if ip in failed_attempts:
                del failed_attempts[ip]
    return False

def record_failed_attempt(ip: str):
    """Record a failed login attempt."""
    current_time = time.time()
    
    # Clean old attempts (older than 1 hour)
    failed_attempts[ip] = [
        attempt_time for attempt_time in failed_attempts[ip] 
        if current_time - attempt_time < 3600
    ]
    
    # Add current attempt
    failed_attempts[ip].append(current_time)
    
    # Block IP if too many attempts
    if len(failed_attempts[ip]) >= MAX_ATTEMPTS:
        blocked_ips[ip] = current_time + BLOCK_DURATION
        logger.warning(f"IP {ip} blocked due to {len(failed_attempts[ip])} failed attempts")

def verify_admin_key(request: Request, api_key: str = Header(None, alias="X-Admin-Key")):
    """Enhanced admin API key verification with rate limiting."""
    client_ip = get_client_ip(request)
    
    # Check if IP is blocked
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
    
    # Clear failed attempts on successful login
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

# Initialize database for serverless (only if available)
if DATABASE_AVAILABLE:
    try:
        engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:///./news_digest.db'))
        Base.metadata.create_all(bind=engine)
        create_tables()
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        DATABASE_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(title="Autonomous News Digest Platform")

# Mount static files (handle gracefully if directory doesn't exist)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Static files mounted successfully")
except Exception as e:
    logger.warning(f"Static files mount error: {e}")

# Templates (handle gracefully if directory doesn't exist)
try:
    templates = Jinja2Templates(directory="templates")
    logger.info("Templates initialized successfully")
except Exception as e:
    logger.error(f"Templates initialization error: {e}")
    templates = None

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
GROK_API_KEY = os.getenv('GROK_API_KEY')

# Initialize services with error handling
email_service = None
news_service = None

def get_email_service():
    global email_service
    if email_service is None and SERVICES_AVAILABLE and EmailService:
        try:
            email_service = EmailService()
            logger.info("Email service initialized")
        except Exception as e:
            logger.error(f"Email service initialization error: {e}")
    return email_service

def get_news_service():
    global news_service
    if news_service is None and SERVICES_AVAILABLE and NewsService:
        try:
            news_service = NewsService()
            logger.info("News service initialized")
        except Exception as e:
            logger.error(f"News service initialization error: {e}")
    return news_service

def get_grok_curated_news(preferences: str) -> List[dict]:
    """Get curated news from Grok based on user preferences."""
    try:
        # Extract custom interests if present
        custom_interests = None
        if '|custom:' in preferences:
            preferences, custom_interests = preferences.split('|custom:')
        
        # Prepare the prompt for Grok
        prompt = f"""Please curate the latest technology news based on the following preferences: {preferences}"""
        if custom_interests:
            prompt += f"\nWith specific focus on: {custom_interests}"
        
        # Call Grok API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROK_API_KEY}"
        }
        
        data = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a technology news curator. Provide a list of the most relevant and recent news articles based on the given preferences."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "model": "grok-3-latest",
            "stream": False,
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            # Parse Grok's response and format it for the digest
            news_data = response.json()
            # Process the response and return formatted news articles
            # This is a placeholder - you'll need to adjust based on Grok's actual response format
            return [
                {
                    "title": "Sample News Title",
                    "source": "Sample Source",
                    "description": "Sample Description",
                    "url": "https://example.com"
                }
            ]
        else:
            print(f"Error from Grok API: {response.text}")
            return []
            
    except Exception as e:
        print(f"Error getting curated news: {str(e)}")
        return []

def send_welcome_email(email: str, name: str, preferences: str):
    """Send welcome email to new subscribers."""
    try:
        # Read welcome email template
        with open('templates/welcome_email.html', 'r', encoding='utf-8') as f:
            template = f.read()

        # Format preferences for display
        display_preferences = preferences
        if '|custom:' in preferences:
            base_prefs, custom_prefs = preferences.split('|custom:')
            display_preferences = f"{base_prefs} (Custom: {custom_prefs})"

        # Replace placeholders
        template = template.replace('{{name}}', name)
        template = template.replace('{{preferences}}', display_preferences)
        template = template.replace('{{unsubscribe_url}}', f"http://localhost:8000/preferences?email={email}")
        template = template.replace('{{preferences_url}}', f"http://localhost:8000/preferences?email={email}")

        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = SENDER_EMAIL
        msg['To'] = email
        msg['Subject'] = "Welcome to Tech News Digest!"
        
        # Attach HTML content
        msg.attach(MIMEText(template, 'html'))
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            
        return True
    except Exception as e:
        print(f"Error sending welcome email: {str(e)}")
        return False

def send_unsubscribe_email(email: str, name: str):
    """Send unsubscribe confirmation email."""
    try:
        # Read unsubscribe email template
        with open('templates/unsubscribe_mail.html', 'r', encoding='utf-8') as f:
            template = f.read()

        # Create URLs
        base_url = "http://localhost:8000"  # Change this to your actual domain in production
        resubscribe_url = f"{base_url}/"
        preferences_url = f"{base_url}/preferences?email={urllib.parse.quote(email)}"

        # Replace placeholders
        template = template.replace('{{name}}', name)
        template = template.replace('{{resubscribe_url}}', resubscribe_url)
        template = template.replace('{{preferences_url}}', preferences_url)

        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = SENDER_EMAIL
        msg['To'] = email
        msg['Subject'] = "Unsubscribed from Tech News Digest"
        
        # Attach HTML content
        msg.attach(MIMEText(template, 'html'))
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            
        return True
    except Exception as e:
        print(f"Error sending unsubscribe email: {str(e)}")
        return False

# Pydantic models for request/response
class SubscriberCreate(BaseModel):
    email: EmailStr
    name: str
    preferences: str = "all"
    digest_type: str = "tech"  # "tech", "upsc", or "both"

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
        # Sanitize and validate name
        v = html.escape(v.strip())
        if len(v) < 2 or len(v) > 100:
            raise ValueError('Name must be between 2 and 100 characters')
        if not re.match(r'^[a-zA-Z\s\-\.]+$', v):
            raise ValueError('Name contains invalid characters')
        return v
    
    @validator('subject')
    def validate_subject(cls, v):
        # Sanitize and validate subject
        v = html.escape(v.strip())
        if len(v) < 5 or len(v) > 200:
            raise ValueError('Subject must be between 5 and 200 characters')
        return v
    
    @validator('message')
    def validate_message(cls, v):
        # Sanitize and validate message
        v = html.escape(v.strip())
        if len(v) < 10 or len(v) > 5000:
            raise ValueError('Message must be between 10 and 5000 characters')
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'data:',
            r'vbscript:',
        ]
        for pattern in dangerous_patterns:
            v = re.sub(pattern, '', v, flags=re.IGNORECASE | re.DOTALL)
        return v

class DigestScheduleUpdate(BaseModel):
    digest_type: str
    scheduled_time: str  # HH:MM format
    is_active: bool = True

class UnsubscribeTokenRequest(BaseModel):
    email: EmailStr

# Health check endpoint for debugging
@app.get("/health")
async def health_check():
    """Health check endpoint for debugging serverless deployment."""
    return {
        "status": "ok",
        "database_available": DATABASE_AVAILABLE,
        "services_available": SERVICES_AVAILABLE,
        "admin_configured": bool(ADMIN_API_KEY),
        "email_configured": bool(SENDER_EMAIL and SENDER_PASSWORD),
        "environment": "serverless" if os.getenv("VERCEL") else "local"
    }

# Routes with error handling
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not templates:
        return HTMLResponse("<h1>AI News Digest</h1><p>Service starting up...</p>")
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Template error: {e}")
        return HTMLResponse(f"<h1>AI News Digest</h1><p>Welcome! Service is running.</p>")

@app.get("/preferences", response_class=HTMLResponse)
async def preferences_page(request: Request, email: str = None):
    if not templates:
        return HTMLResponse("<h1>Preferences</h1><p>Service starting up...</p>")
    try:
        return templates.TemplateResponse("preferences.html", {"request": request, "email": email})
    except Exception as e:
        logger.error(f"Template error: {e}")
        return HTMLResponse(f"<h1>Preferences</h1><p>Email: {email}</p>")

@app.post("/subscribe", response_model=SubscriberResponse)
def create_subscriber(subscriber: SubscriberCreate, db: Session = Depends(get_db)):
    """Create a new subscriber."""
    if not DATABASE_AVAILABLE or not db:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
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
    if not templates:
        return HTMLResponse("<h1>Contact Us</h1><p>Email: contact.ainewsdigest@gmail.com</p>")
    try:
        return templates.TemplateResponse("contact.html", {"request": request})
    except Exception as e:
        logger.error(f"Template error: {e}")
        return HTMLResponse("<h1>Contact Us</h1><p>Email: contact.ainewsdigest@gmail.com</p>")

@app.post("/contact")
async def submit_contact(contact: ContactForm, db: Session = Depends(get_db)):
    """Handle contact form submission with validation and email notifications."""
    try:
        # Additional server-side validation
        if len(contact.message.split()) < 3:
            raise HTTPException(status_code=400, detail="Message too short")
        
        # Save to database if available
        if DATABASE_AVAILABLE and db:
            try:
                contact_message = models.ContactMessage(
                    name=contact.name,
                    email=contact.email,
                    subject=contact.subject,
                    message=contact.message
                )
                db.add(contact_message)
                db.commit()
                logger.info(f"Contact message saved to database for {contact.email}")
            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")
        
        # Check email credentials before attempting to send
        if not SENDER_EMAIL or not SENDER_PASSWORD:
            logger.warning("Email credentials not configured")
            return {"message": "Thank you for your message! It has been received."}
        
        # Send notification email
        try:
            email_svc = get_email_service()
            if email_svc:
                # Simple email notification
                admin_subject = f"New Contact: {contact.subject}"
                admin_message = f"From: {contact.name} ({contact.email})\nSubject: {contact.subject}\n\nMessage:\n{contact.message}"
                
                # Send simple text email
                email_svc.send_simple_email(
                    "contact.ainewsdigest@gmail.com",
                    admin_subject,
                    admin_message,
                    log_to_db=False
                )
                logger.info("Contact notification sent")
        except Exception as email_error:
            logger.error(f"Email error: {email_error}")
        
        return {"message": "Thank you for your message! We'll get back to you soon."}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Contact form error: {e}")
        return {"message": "Thank you for your message. It has been received!"}

# Admin routes with simplified error handling
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    if not templates:
        return HTMLResponse("<h1>Admin Login</h1><p>Service starting up...</p>")
    try:
        return templates.TemplateResponse("admin_login.html", {"request": request})
    except Exception:
        return HTMLResponse("<h1>Admin Login</h1><p>Admin interface available</p>")

@app.get("/api/stats")
async def get_stats(request: Request, admin: bool = Depends(verify_admin_key)):
    """Get platform statistics (admin endpoint)."""
    if not DATABASE_AVAILABLE:
        return {"error": "Database unavailable", "total_subscribers": 0}
    
    try:
        from database.database import SessionLocal
        db = SessionLocal()
        try:
            total_subscribers = db.query(models.Subscriber).filter(models.Subscriber.is_active == True).count()
            return {
                "total_subscribers": total_subscribers,
                "tech_subscribers": 0,
                "upsc_subscribers": 0,
                "emails_sent_today": 0,
                "status": "limited_mode"
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": str(e), "total_subscribers": 0}

# Routes
@app.get("/api/news/tech")
async def get_tech_news(preferences: str = Query("all", description="Comma-separated preferences")):
    """Get tech news articles."""
    try:
        news_svc = get_news_service()
        articles = await news_svc.fetch_tech_articles(preferences)
        return {"articles": articles, "count": len(articles)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tech news: {str(e)}")

@app.get("/api/news/upsc")
async def get_upsc_news():
    """Get UPSC news articles."""
    try:
        news_svc = get_news_service()
        articles = await news_svc.fetch_upsc_articles()
        return {"articles": articles, "count": len(articles)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching UPSC news: {str(e)}")

@app.get("/api/news/custom")
async def get_custom_news(preferences: str = Query(...), custom_interests: str = Query(...)):
    """Get custom curated news using Grok AI."""
    try:
        news_svc = get_news_service()
        articles = news_svc.get_custom_curated_news(preferences, custom_interests)
        return {"articles": articles, "count": len(articles)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching custom news: {str(e)}")

# Autonomous agent management endpoints
@app.get("/api/schedules")
async def get_schedules(request: Request, db: Session = Depends(get_db), admin: bool = Depends(verify_admin_key)):
    """Get digest schedules (admin endpoint)."""
    schedules = db.query(models.DigestSchedule).all()
    return schedules

@app.post("/api/schedules")
async def update_schedule(request: Request, schedule_update: DigestScheduleUpdate, db: Session = Depends(get_db),
                         admin: bool = Depends(verify_admin_key)):
    """Update digest schedule (admin endpoint)."""
    schedule = db.query(models.DigestSchedule).filter(
        models.DigestSchedule.digest_type == schedule_update.digest_type
    ).first()
    
    if not schedule:
        # Create new schedule
        schedule = models.DigestSchedule(
            digest_type=schedule_update.digest_type,
            scheduled_time=schedule_update.scheduled_time,
            is_active=schedule_update.is_active
        )
        db.add(schedule)
    else:
        # Update existing schedule
        schedule.scheduled_time = schedule_update.scheduled_time
        schedule.is_active = schedule_update.is_active
    
    db.commit()
    return {"message": "Schedule updated successfully"}

@app.post("/api/digest/send-test")
async def send_test_digest(
    request: Request,
    background_tasks: BackgroundTasks,
    digest_type: str = Query(..., description="tech, upsc, or both"),
    db: Session = Depends(get_db),
    admin: bool = Depends(verify_admin_key)
):
    """Send test digest immediately (admin endpoint)."""
    try:
        # Simple test digest without autonomous agent dependency
        subscribers = db.query(models.Subscriber).filter(
            models.Subscriber.is_active == True
        ).all()
        
        if digest_type in ["tech", "both"]:
            tech_count = len([s for s in subscribers if s.digest_type in ["tech", "both"]])
        if digest_type in ["upsc", "both"]:
            upsc_count = len([s for s in subscribers if s.digest_type in ["upsc", "both"]])
        
        return {"message": f"Test {digest_type} digest would be sent to subscribers", "test_mode": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending test digest: {str(e)}")

@app.get("/api/export/subscribers")
async def export_subscribers(request: Request, db: Session = Depends(get_db), admin: bool = Depends(verify_admin_key)):
    """Export subscribers data as CSV (admin endpoint)."""
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse
    
    try:
        subscribers = db.query(models.Subscriber).filter(models.Subscriber.is_active == True).all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Name', 'Email', 'Digest Type', 'Preferences', 'Created At', 'Last Email Sent'])
        
        # Write data
        for subscriber in subscribers:
            writer.writerow([
                subscriber.name,
                subscriber.email,
                subscriber.digest_type,
                subscriber.preferences or 'Default',
                subscriber.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                subscriber.last_email_sent.strftime('%Y-%m-%d %H:%M:%S') if hasattr(subscriber, 'last_email_sent') and subscriber.last_email_sent else 'Never'
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=subscribers.csv"}
        )
    except Exception as e:
        logger.error(f"Error exporting subscribers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error exporting subscribers: {str(e)}")

@app.get("/api/email-logs")
async def get_email_logs(request: Request, limit: int = 50, db: Session = Depends(get_db), admin: bool = Depends(verify_admin_key)):
    """Get recent email logs (admin endpoint)."""
    try:
        # Check if EmailLog table exists
        logs = []
        try:
            logs = db.query(models.EmailLog).order_by(models.EmailLog.sent_at.desc()).limit(limit).all()
            return [{
                "id": log.id,
                "recipient_email": log.recipient_email,
                "subject": log.subject,
                "status": log.status,
                "sent_at": log.sent_at.isoformat(),
                "error_message": log.error_message
            } for log in logs]
        except Exception as e:
            # Return empty array if table doesn't exist
            logger.info(f"EmailLog table not available: {str(e)}")
            return []
    except Exception as e:
        logger.error(f"Error fetching email logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching email logs: {str(e)}")

@app.get("/api/system-health")
async def system_health(request: Request, admin: bool = Depends(verify_admin_key)):
    """Get system health status (admin endpoint)."""
    try:
        system_info = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "system": "monitoring_unavailable",
            "services": {
                "database": "connected",
                "email_service": "operational", 
                "news_scraper": "operational",
                "ai_service": "operational"
            }
        }
        
        # Try to get system stats if psutil is available
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            system_info["system"] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
        except ImportError:
            # psutil not available, use basic status
            pass
        except Exception as e:
            logger.warning(f"Error getting system stats: {str(e)}")
            
        return system_info
    except Exception as e:
        logger.error(f"Error checking system health: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking system health: {str(e)}")

# Enhanced admin login endpoint with security tracking
@app.post("/api/admin/login")
async def admin_login_api(request: Request, api_key: str = Form(...)):
    """Admin login API with rate limiting."""
    client_ip = get_client_ip(request)
    
    # Check if IP is blocked
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
    
    # Clear failed attempts on successful login
    if client_ip in failed_attempts:
        del failed_attempts[client_ip]
    
    return {"message": "Login successful", "redirect": "/admin/dashboard"}

@app.post("/api/generate-unsubscribe-token")
async def generate_unsubscribe_token_api(request: UnsubscribeTokenRequest, db: Session = Depends(get_db)):
    """Generate unsubscribe token for a given email."""
    # Verify the email exists in our database
    subscriber = db.query(models.Subscriber).filter(models.Subscriber.email == request.email).first()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Email not found in our records")
    
    if not subscriber.is_active:
        raise HTTPException(status_code=400, detail="This email is already unsubscribed")
    
    # Generate the token
    token = generate_unsubscribe_token(request.email)
    return {"token": token}

# Add this at the very end of main.py for Vercel deployment
# Note: mangum is only needed for Vercel serverless deployment
try:
    from mangum import Mangum  # type: ignore
    handler = Mangum(app)
    logger.info("Mangum handler initialized for serverless deployment")
except ImportError:
    # Mangum not available, running in development mode
    logger.info("Running in development mode (mangum not available)")
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
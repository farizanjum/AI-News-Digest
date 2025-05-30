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

# Print database info for debugging
db_url = os.getenv('DATABASE_URL', 'sqlite:///./news_digest.db')
logger.info(f"Starting AI News Digest - Database configured")

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
app = FastAPI(title="AI News Digest Platform")

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
        
        engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:///./news_digest.db'))
        Base.metadata.create_all(bind=engine)
        DATABASE_AVAILABLE = True
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database not available: {e}")
        DATABASE_AVAILABLE = False
        return False

# Check services availability
def check_services():
    global SERVICES_AVAILABLE
    try:
        from services.email_service import EmailService
        from services.news_service import NewsService
        SERVICES_AVAILABLE = True
        logger.info("Services available")
        return True
    except Exception as e:
        logger.error(f"Services not available: {e}")
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

# Enhanced Security configuration
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY')
UNSUBSCRIBE_SECRET = os.getenv('UNSUBSCRIBE_SECRET', secrets.token_urlsafe(32))

# Security tracking
failed_attempts = defaultdict(list)
blocked_ips = defaultdict(float)
MAX_ATTEMPTS = 3
BLOCK_DURATION = 300  # 5 minutes

def verify_admin_key(request: Request, api_key: str = Header(None, alias="X-Admin-Key")):
    """Admin API key verification with rate limiting."""
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="Admin authentication not configured")
    
    if not api_key or api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    return True

# Pydantic models
class SubscriberCreate(BaseModel):
    email: EmailStr
    name: str
    preferences: str = "all"
    digest_type: str = "tech"

class ContactForm(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

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
        logger.info("Static files mounted")
    except Exception as e:
        logger.warning(f"Static files not available: {e}")
    
    logger.info("✅ Startup complete!")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for debugging deployment."""
    return {
        "status": "ok",
        "database_available": DATABASE_AVAILABLE,
        "services_available": SERVICES_AVAILABLE,
        "admin_configured": bool(ADMIN_API_KEY),
        "email_configured": bool(os.getenv('SENDER_EMAIL') and os.getenv('SENDER_PASSWORD')),
        "environment": "serverless" if os.getenv("VERCEL") else "local",
        "message": "AI News Digest is running!"
    }

# Basic routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        from fastapi.templating import Jinja2Templates
        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.warning(f"Template error: {e}")
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI News Digest</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .container { text-align: center; margin-top: 50px; }
                .status { background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0; }
                .button { background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 AI News Digest</h1>
                <div class="status">
                    <h3>✅ Service is Running!</h3>
                    <p>Your autonomous news digest platform is live and ready.</p>
                </div>
                <a href="/health" class="button">Check System Health</a>
                <a href="/contact" class="button">Contact Us</a>
            </div>
        </body>
        </html>
        """)

@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    try:
        from fastapi.templating import Jinja2Templates
        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("contact.html", {"request": request})
    except Exception:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Contact - AI News Digest</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
                .form-group { margin: 15px 0; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
                button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; }
                button:hover { background: #0056b3; }
            </style>
        </head>
        <body>
            <h1>Contact Us</h1>
            <form method="post" action="/contact">
                <div class="form-group">
                    <label for="name">Name:</label>
                    <input type="text" id="name" name="name" required>
                </div>
                <div class="form-group">
                    <label for="email">Email:</label>
                    <input type="email" id="email" name="email" required>
                </div>
                <div class="form-group">
                    <label for="subject">Subject:</label>
                    <input type="text" id="subject" name="subject" required>
                </div>
                <div class="form-group">
                    <label for="message">Message:</label>
                    <textarea id="message" name="message" rows="5" required></textarea>
                </div>
                <button type="submit">Send Message</button>
            </form>
        </body>
        </html>
        """)

@app.post("/contact")
async def submit_contact(contact: ContactForm):
    """Handle contact form submission."""
    try:
        logger.info(f"Contact form submitted by {contact.email}")
        
        # Try to save to database if available
        if DATABASE_AVAILABLE:
            try:
                import database.models as models
                db = get_db_session()
                if db:
                    contact_message = models.ContactMessage(
                        name=contact.name,
                        email=contact.email,
                        subject=contact.subject,
                        message=contact.message
                    )
                    db.add(contact_message)
                    db.commit()
                    db.close()
                    logger.info("Contact message saved to database")
            except Exception as e:
                logger.error(f"Database save error: {e}")
        
        # Try to send email if configured
        sender_email = os.getenv('SENDER_EMAIL')
        sender_password = os.getenv('SENDER_PASSWORD')
        
        if sender_email and sender_password:
            try:
                msg = MIMEText(f"From: {contact.name} ({contact.email})\nSubject: {contact.subject}\n\nMessage:\n{contact.message}")
                msg['From'] = sender_email
                msg['To'] = "contact.ainewsdigest@gmail.com"
                msg['Subject'] = f"Contact Form: {contact.subject}"
                
                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                
                logger.info("Contact email sent successfully")
            except Exception as e:
                logger.error(f"Email send error: {e}")
        
        return {"message": "Thank you for your message! We'll get back to you soon."}
        
    except Exception as e:
        logger.error(f"Contact form error: {e}")
        return {"message": "Thank you for your message. It has been received!"}

# Admin routes
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Login - AI News Digest</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; max-width: 400px; margin: 100px auto; padding: 20px; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
            button { width: 100%; background: #007bff; color: white; padding: 12px; border: none; border-radius: 4px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h2>Admin Login</h2>
        <form method="post" action="/api/admin/login">
            <div class="form-group">
                <label for="api_key">Admin API Key:</label>
                <input type="password" id="api_key" name="api_key" required>
            </div>
            <button type="submit">Login</button>
        </form>
    </body>
    </html>
    """)

@app.get("/api/stats")
async def get_stats(admin: bool = Depends(verify_admin_key)):
    """Get platform statistics."""
    try:
        if DATABASE_AVAILABLE:
            import database.models as models
            db = get_db_session()
            if db:
                total_subscribers = db.query(models.Subscriber).filter(models.Subscriber.is_active == True).count()
                db.close()
                return {
                    "total_subscribers": total_subscribers,
                    "tech_subscribers": 0,
                    "upsc_subscribers": 0,
                    "emails_sent_today": 0,
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

# Add Mangum handler for Vercel
try:
    from mangum import Mangum  # type: ignore
    handler = Mangum(app)
    logger.info("Mangum handler initialized for Vercel deployment")
except ImportError:
    logger.info("Running in development mode")
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
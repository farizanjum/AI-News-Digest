import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import urllib.parse
import hashlib
import hmac
import secrets
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        
        # For digest emails (subscribe.ainewsdigest@gmail.com)
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        
        # For contact form notifications (contact.ainewsdigest@gmail.com)
        self.contact_email = "contact.ainewsdigest@gmail.com"
        
        self.unsubscribe_secret = os.getenv('UNSUBSCRIBE_SECRET', secrets.token_urlsafe(32))
        
        if not self.sender_email or not self.sender_password:
            raise ValueError("Email credentials not found in environment variables")
    
    def generate_unsubscribe_token(self, email: str) -> str:
        """Generate secure unsubscribe token."""
        message = f"{email}:unsubscribe"
        return hmac.new(self.unsubscribe_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    
    def send_email(self, to_email: str, subject: str, html_content: str, 
                   log_to_db: bool = True, digest_type: str = "general") -> bool:
        """Send an email and optionally log to database."""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            
            # Log to database if requested
            if log_to_db:
                self._log_email(to_email, subject, digest_type, "sent")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            if log_to_db:
                self._log_email(to_email, subject, digest_type, "failed", str(e))
            return False
    
    def _log_email(self, email: str, subject: str, digest_type: str, 
                   status: str, error_message: str = None):
        """Log email sending to database."""
        try:
            from database.database import SessionLocal
            from database.models import EmailLog
            
            db = SessionLocal()
            try:
                email_log = EmailLog(
                    recipient_email=email,
                    digest_type=digest_type,
                    subject=subject,
                    status=status,
                    error_message=error_message
                )
                db.add(email_log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error logging email: {str(e)}")
    
    def send_welcome_email(self, email: str, name: str, preferences: str, 
                          digest_type: str = "tech") -> bool:
        """Send welcome email to new subscribers."""
        try:
            with open('templates/welcome_email.html', 'r', encoding='utf-8') as f:
                template = f.read()

            # Format preferences for display
            display_preferences = preferences
            if '|custom:' in preferences:
                base_prefs, custom_prefs = preferences.split('|custom:')
                display_preferences = f"{base_prefs} (Custom: {custom_prefs})"

            # Create secure URLs with tokens
            base_url = os.getenv('BASE_URL', 'http://localhost:8000')
            unsubscribe_token = self.generate_unsubscribe_token(email)
            unsubscribe_url = f"{base_url}/unsubscribe/{urllib.parse.quote(email)}?token={unsubscribe_token}"
            preferences_url = f"{base_url}/preferences?email={urllib.parse.quote(email)}"

            # Replace placeholders
            template = template.replace('{{name}}', name)
            template = template.replace('{{preferences}}', display_preferences)
            template = template.replace('{{digest_type}}', digest_type.title())
            template = template.replace('{{unsubscribe_url}}', unsubscribe_url)
            template = template.replace('{{preferences_url}}', preferences_url)

            # Always use "AI News Digest" in subject regardless of digest type
            subject = "Welcome to AI News Digest!"
            return self.send_email(email, subject, template, True, "welcome")
            
        except Exception as e:
            logger.error(f"Error sending welcome email to {email}: {str(e)}")
            return False
    
    def send_unsubscribe_email(self, email: str, name: str) -> bool:
        """Send unsubscribe confirmation email."""
        try:
            with open('templates/unsubscribe_mail.html', 'r', encoding='utf-8') as f:
                template = f.read()

            # Create URLs
            base_url = os.getenv('BASE_URL', 'http://localhost:8000')
            resubscribe_url = f"{base_url}/"
            preferences_url = f"{base_url}/preferences?email={urllib.parse.quote(email)}"

            # Replace placeholders
            template = template.replace('{{name}}', name)
            template = template.replace('{{resubscribe_url}}', resubscribe_url)
            template = template.replace('{{preferences_url}}', preferences_url)

            # Updated subject with emoji as requested
            subject = "We're sorry to see you go! 😢"
            return self.send_email(email, subject, template, True, "unsubscribe")
            
        except Exception as e:
            logger.error(f"Error sending unsubscribe email to {email}: {str(e)}")
            return False
    
    def send_tech_digest(self, email: str, name: str, articles: List[Dict], 
                        preferences: List[str]) -> bool:
        """Send tech news digest email."""
        try:
            from services.news_service import NewsService
            news_service = NewsService()
            
            digest_html = news_service.format_tech_digest(articles, name, preferences, email)
            subject = f"Your Daily Tech News Digest - {datetime.now().strftime('%B %d, %Y')}"
            
            return self.send_email(email, subject, digest_html, True, "tech")
            
        except Exception as e:
            logger.error(f"Error sending tech digest to {email}: {str(e)}")
            return False
    
    def send_upsc_digest(self, email: str, name: str, digest_html: str) -> bool:
        """Send UPSC digest email."""
        try:
            subject = f"Your Daily UPSC Digest - {datetime.now().strftime('%B %d, %Y')}"
            return self.send_email(email, subject, digest_html, True, "upsc")
            
        except Exception as e:
            logger.error(f"Error sending UPSC digest to {email}: {str(e)}")
            return False
    
    def send_contact_response(self, email: str, name: str, original_message: str, 
                             response: str) -> bool:
        """Send response to contact form submission."""
        try:
            template = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #00f2fe;">Thank you for contacting us, {name}!</h2>
                
                <p>We have received your message and appreciate you taking the time to reach out to us.</p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Your Original Message:</h3>
                    <p>{original_message}</p>
                </div>
                
                <div style="background-color: #e8f8ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Our Response:</h3>
                    <p>{response}</p>
                </div>
                
                <p>If you have any further questions, please don't hesitate to contact us.</p>
                
                <p>Best regards,<br>The News Digest Team</p>
            </body>
            </html>
            """
            
            subject = "Response to Your Contact Form Submission"
            return self.send_email(email, subject, template, True, "contact_response")
            
        except Exception as e:
            logger.error(f"Error sending contact response to {email}: {str(e)}")
            return False
    
    def send_simple_email(self, to_email: str, subject: str, message: str, 
                         log_to_db: bool = True, digest_type: str = "general") -> bool:
        """Send a simple plain text email (used for contact form notifications)."""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Convert plain text to simple HTML
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; line-height: 1.6;">
                <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{message}</pre>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Simple email sent successfully to {to_email}")
            
            # Log to database if requested
            if log_to_db:
                self._log_email(to_email, subject, digest_type, "sent")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending simple email to {to_email}: {str(e)}")
            if log_to_db:
                self._log_email(to_email, subject, digest_type, "failed", str(e))
            return False
    
    def send_preference_update_email(self, email: str, name: str, old_preferences: str, 
                                   new_preferences: str, digest_type: str = "tech") -> bool:
        """Send preference update confirmation email."""
        try:
            # Format preferences for display
            def format_preferences(prefs):
                if '|custom:' in prefs:
                    base_prefs, custom_prefs = prefs.split('|custom:')
                    return f"{base_prefs} (Custom: {custom_prefs})"
                return prefs
            
            old_display = format_preferences(old_preferences)
            new_display = format_preferences(new_preferences)
            
            # Create secure URLs
            base_url = os.getenv('BASE_URL', 'http://localhost:8000')
            unsubscribe_token = self.generate_unsubscribe_token(email)
            unsubscribe_url = f"{base_url}/unsubscribe/{urllib.parse.quote(email)}?token={unsubscribe_token}"
            preferences_url = f"{base_url}/preferences?email={urllib.parse.quote(email)}"

            template = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; line-height: 1.6; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .preference-box {{ background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 15px 0; }}
                    .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
                    .btn {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📧 Preferences Updated Successfully!</h1>
                </div>
                
                <div class="content">
                    <p>Hi <strong>{name}</strong>,</p>
                    
                    <p>Your AI News Digest preferences have been successfully updated. Here's what changed:</p>
                    
                    <div class="preference-box">
                        <h3>📰 Your Current Preferences:</h3>
                        <p><strong>Digest Type:</strong> {digest_type.title()}</p>
                        <p><strong>Categories:</strong> {new_display}</p>
                    </div>
                    
                    <p>You'll start receiving news based on these updated preferences with your next digest delivery.</p>
                    
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{preferences_url}" class="btn">Update Preferences Again</a>
                    </p>
                    
                    <p>Thank you for staying with AI News Digest! 🚀</p>
                </div>
                
                <div class="footer">
                    <p>© 2024 AI News Digest. All rights reserved.</p>
                    <p><a href="{unsubscribe_url}">Unsubscribe</a> | <a href="{preferences_url}">Update Preferences</a></p>
                </div>
            </body>
            </html>
            """

            subject = "AI News Digest - Preferences Updated Successfully"
            return self.send_email(email, subject, template, True, "preference_update")
            
        except Exception as e:
            logger.error(f"Error sending preference update email to {email}: {str(e)}")
            return False 
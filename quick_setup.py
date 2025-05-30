#!/usr/bin/env python3
"""
Quick Setup for AI News Digest
Generates secure keys for production deployment
"""

import secrets
import os
from datetime import datetime

def generate_admin_key():
    """Generate a secure admin API key."""
    return f"admin_secure_2024_{secrets.token_urlsafe(24)}"

def generate_unsubscribe_secret():
    """Generate a secure unsubscribe secret."""
    return secrets.token_urlsafe(32)

def display_environment_variables():
    """Display the environment variables needed for deployment."""
    admin_key = generate_admin_key()
    unsubscribe_secret = generate_unsubscribe_secret()
    
    print("🔧 AI News Digest - Environment Variables")
    print("=" * 60)
    print()
    print("📋 Add these to your .env file (for local development):")
    print("=" * 60)
    print(f"ADMIN_API_KEY={admin_key}")
    print(f"UNSUBSCRIBE_SECRET={unsubscribe_secret}")
    print("SENDER_EMAIL=subscribe.ainewsdigest@gmail.com")
    print("SENDER_PASSWORD=your_gmail_app_password_here")
    print("DATABASE_TYPE=sqlite")
    print("DATABASE_URL=sqlite:///./news_digest.db")
    print()
    print("🚀 For Vercel deployment, add these in your dashboard:")
    print("=" * 60)
    print(f"ADMIN_API_KEY={admin_key}")
    print(f"UNSUBSCRIBE_SECRET={unsubscribe_secret}")
    print("SENDER_EMAIL=subscribe.ainewsdigest@gmail.com")
    print("SENDER_PASSWORD=your_gmail_app_password_here")
    print("DATABASE_TYPE=postgresql")
    print("DATABASE_URL=your_postgres_connection_string")
    print()
    print("🤖 For GitHub Actions, add these as repository secrets:")
    print("=" * 60)
    print("VERCEL_TOKEN=your_vercel_token")
    print("VERCEL_ORG_ID=your_org_id")
    print("VERCEL_PROJECT_ID=your_project_id")
    print("VERCEL_DEPLOYMENT_URL=https://your-app.vercel.app")
    print(f"ADMIN_API_KEY={admin_key}")
    print()
    print("📧 Gmail App Password Setup:")
    print("=" * 60)
    print("1. Enable 2-Factor Authentication on Gmail")
    print("2. Go to Google Account Settings")
    print("3. Search 'App passwords'") 
    print("4. Generate password for 'Mail'")
    print("5. Use this as SENDER_PASSWORD")
    print()
    print("✅ Your platform is ready for deployment!")
    print("🚀 Next: Deploy to Vercel at https://vercel.com/new")

if __name__ == "__main__":
    display_environment_variables() 
#!/usr/bin/env python3
"""
Supabase Environment Variables Generator
Run this script to generate secure keys for your deployment
"""
import secrets
import urllib.parse

def generate_env_vars():
    print("🚀 AI News Digest - Environment Variables Setup")
    print("=" * 50)
    
    # URL encode the password
    original_password = "1Don'tknow@"
    encoded_password = urllib.parse.quote(original_password)
    
    print(f"\n📁 DATABASE CONFIGURATION:")
    print(f"Original password: {original_password}")
    print(f"URL-encoded password: {encoded_password}")
    
    database_url = f"postgresql://postgres:{encoded_password}@db.wlkzjcgdkqrvgvwdvvec.supabase.co:5432/postgres"
    
    # Generate secure keys
    admin_key = secrets.token_urlsafe(32)
    unsubscribe_secret = secrets.token_urlsafe(32)
    
    print(f"\n🔐 ENVIRONMENT VARIABLES FOR VERCEL:")
    print("-" * 50)
    print(f"DATABASE_URL={database_url}")
    print(f"ADMIN_API_KEY={admin_key}")
    print(f"UNSUBSCRIBE_SECRET={unsubscribe_secret}")
    print(f"SENDER_EMAIL=subscribe.ainewsdigest@gmail.com")
    print(f"SENDER_PASSWORD=your_gmail_app_password_here")
    print(f"BASE_URL=https://autonomous-ai-news-digest.vercel.app")
    
    print(f"\n📋 NEXT STEPS:")
    print("1. Copy the environment variables above")
    print("2. Go to https://vercel.com/dashboard")
    print("3. Find your 'autonomous-ai-news-digest' project")
    print("4. Click Settings → Environment Variables")
    print("5. Add each variable (one by one)")
    print("6. Set up Gmail App Password (see SUPABASE_SETUP.md)")
    print("7. Click 'Redeploy' in Vercel")
    
    print(f"\n✅ VERIFICATION:")
    print("After deployment, visit:")
    print("https://autonomous-ai-news-digest.vercel.app/health")
    print("Should show: database_available: true")

if __name__ == "__main__":
    generate_env_vars() 
#!/usr/bin/env python3
"""
Production Cleanup Script for AI News Digest Platform
=====================================================

This script:
1. Removes all temporary, testing, and demo files
2. Cleans up development artifacts
3. Organizes the codebase for production
4. Creates production-ready structure
5. Validates essential files are present

Run this before deploying to production!
"""

import os
import shutil
import glob
from pathlib import Path

# Files and directories to remove for production
CLEANUP_ITEMS = [
    # Documentation files for development
    "MOBILE_OPTIMIZATION_COMPLETE.md",
    "PRODUCTION_STATUS.md", 
    "PRODUCTION_READY.md",
    "QUICK_START.md",
    
    # Test and demo files
    "add_test_user.py",
    "test_*.py",
    "demo_*.py",
    "trial_*.py",
    "*_test.py",
    "*_demo.py",
    
    # Temporary files
    "temp_*",
    "tmp_*",
    "*.tmp",
    "*.temp",
    
    # Development cache and artifacts
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".pytest_cache/",
    ".coverage",
    "htmlcov/",
    
    # IDE and editor files
    ".vscode/",
    ".idea/",
    "*.swp",
    "*.swo",
    "*~",
    ".DS_Store",
    
    # Log files (keep structure but clear contents)
    "*.log",
    
    # Development database (will be recreated)
    "news_digest.db",
    "*.db-shm",
    "*.db-wal",
    
    # Temporary scraped data
    "news_digest.json",
    
    # This cleanup script itself (optional)
    "cleanup_for_production.py"
]

# Essential files that must be present
ESSENTIAL_FILES = [
    "main.py",
    "autonomous_agent.py",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "setup_env.py",
    ".env.example",
    "README.md",
    "SECURITY.md",
    "database/models.py",
    "database/database.py",
    "services/email_service.py",
    "services/news_service.py",
    "scrapers/ai_news.py",
    "templates/index.html",
    "templates/base.html",
    "templates/admin_login.html",
    "templates/admin_dashboard.html",
    "static/css/styles.css"
]

# Production directories structure
PRODUCTION_DIRS = [
    "database",
    "services", 
    "scrapers",
    "templates",
    "static/css",
    "static/js",
    "static/images",
    "upsc_digest",
    "logs"
]

def clean_file_or_dir(item_path):
    """Remove a file or directory safely."""
    try:
        if os.path.isfile(item_path):
            os.remove(item_path)
            print(f"✅ Removed file: {item_path}")
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
            print(f"✅ Removed directory: {item_path}")
    except Exception as e:
        print(f"⚠️  Could not remove {item_path}: {e}")

def cleanup_temporary_files():
    """Remove all temporary and testing files."""
    print("🧹 Cleaning up temporary files...")
    
    removed_count = 0
    
    for pattern in CLEANUP_ITEMS:
        # Handle glob patterns
        if '*' in pattern or '?' in pattern:
            matches = glob.glob(pattern, recursive=True)
            for match in matches:
                clean_file_or_dir(match)
                removed_count += 1
        else:
            # Handle direct file/directory names
            if os.path.exists(pattern):
                clean_file_or_dir(pattern)
                removed_count += 1
    
    print(f"🗑️  Removed {removed_count} temporary items")

def validate_essential_files():
    """Check that all essential files are present."""
    print("\n🔍 Validating essential files...")
    
    missing_files = []
    for file_path in ESSENTIAL_FILES:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
            print(f"❌ Missing: {file_path}")
        else:
            print(f"✅ Present: {file_path}")
    
    if missing_files:
        print(f"\n⚠️  WARNING: {len(missing_files)} essential files are missing!")
        print("Please ensure these files are present before deployment.")
        return False
    else:
        print("\n✅ All essential files are present!")
        return True

def create_production_structure():
    """Ensure production directory structure exists."""
    print("\n📁 Creating production directory structure...")
    
    for dir_path in PRODUCTION_DIRS:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✅ Directory: {dir_path}")
    
    # Create logs directory with .gitkeep
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    gitkeep_path = os.path.join(logs_dir, ".gitkeep")
    if not os.path.exists(gitkeep_path):
        with open(gitkeep_path, 'w') as f:
            f.write("# Keep this directory for logs\n")

def create_production_readme():
    """Create a production-focused README."""
    print("\n📝 Creating production README...")
    
    readme_content = """# 🤖 AI News Digest Platform - Production

## 🚀 Production Deployment

This is the production-ready version of the AI News Digest Platform.

### Quick Start

1. **Environment Setup**:
   ```bash
   python setup_env.py
   # Edit .env with your credentials
   ```

2. **Docker Deployment**:
   ```bash
   docker-compose up -d
   ```

3. **Access Admin Dashboard**:
   - Visit: `https://yourdomain.com/admin/login`
   - Use your admin API key from `.env` file

### Admin Access

Your admin API key is in the `.env` file:
```bash
grep ADMIN_API_KEY .env
```

### Key Features

- ✅ Secure admin dashboard with authentication
- ✅ Automated daily digest delivery at 8:00 PM
- ✅ Tech and UPSC news curation with AI
- ✅ Subscriber management and analytics
- ✅ Email tracking and system monitoring
- ✅ Production-ready security measures

### System Requirements

- Python 3.8+
- Docker & Docker Compose
- Valid API keys (NewsAPI, Grok AI)
- Gmail account with app password

### Production Checklist

- [ ] Update `BASE_URL` in `.env` to your domain
- [ ] Configure SSL certificates
- [ ] Set up reverse proxy (Nginx)
- [ ] Configure email credentials
- [ ] Add your API keys
- [ ] Test admin dashboard access
- [ ] Verify automated scheduling

### Monitoring

- **Admin Dashboard**: `/admin/dashboard`
- **System Health**: API endpoint for monitoring
- **Email Logs**: Track delivery status
- **Subscriber Analytics**: Growth and engagement metrics

### Support

For production issues:
1. Check application logs in `logs/` directory
2. Verify `.env` configuration
3. Test API connectivity
4. Review system health endpoint

---

**🔐 Security**: This is a production system. Keep your admin API key secure!
"""
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("✅ Production README created")

def update_requirements():
    """Update requirements.txt for production."""
    print("\n📦 Updating requirements for production...")
    
    production_requirements = [
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "sqlalchemy>=2.0.0",
        "python-multipart>=0.0.6",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "aiofiles>=23.0.0",
        "jinja2>=3.1.2",
        "pydantic>=2.5.0",
        "pydantic[email]>=2.5.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "schedule>=1.2.0",
        "psutil>=5.9.0",  # For system monitoring
        "gunicorn>=21.2.0"  # For production WSGI
    ]
    
    with open("requirements.txt", "w") as f:
        for req in production_requirements:
            f.write(f"{req}\n")
    
    print("✅ Requirements updated for production")

def create_production_env_example():
    """Create production .env.example file."""
    print("\n🔧 Creating production .env.example...")
    
    env_example = """# ========================================
# AI News Digest Platform - Production
# ========================================

# ========================================
# REQUIRED EMAIL CONFIGURATION
# ========================================
SENDER_EMAIL=your_production_email@company.com
SENDER_PASSWORD=your_app_password

# ========================================
# REQUIRED API KEYS
# ========================================
NEWS_API_KEY=your_newsapi_key_here
GROK_API_KEY=your_grok_api_key_here

# ========================================
# PRODUCTION DATABASE
# ========================================
DATABASE_URL=postgresql://username:password@localhost:5432/news_digest
# For development: sqlite:///./news_digest.db

# ========================================
# PRODUCTION SERVER
# ========================================
BASE_URL=https://yourdomain.com
ADMIN_API_KEY=your_secure_admin_key_here
UNSUBSCRIBE_SECRET=your_secure_unsubscribe_secret

# ========================================
# SMTP CONFIGURATION
# ========================================
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# ========================================
# PRODUCTION SETTINGS
# ========================================
LOG_LEVEL=INFO
PRODUCTION=true
DOCKER_ENV=true
"""
    
    with open(".env.example", "w") as f:
        f.write(env_example)
    
    print("✅ Production .env.example created")

def finalize_production():
    """Final production preparation steps."""
    print("\n🎯 Finalizing production setup...")
    
    # Create .gitignore if it doesn't exist
    gitignore_content = """# Production
.env
*.db
*.log
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
logs/*.log
!logs/.gitkeep

# Temporary
temp/
tmp/
*.tmp
"""
    
    with open(".gitignore", "w") as f:
        f.write(gitignore_content)
    
    print("✅ .gitignore updated")
    print("✅ Production setup complete!")

def main():
    """Main cleanup function."""
    print("🚀 AI News Digest Platform - Production Cleanup")
    print("=" * 50)
    
    # Confirm cleanup
    response = input("\n⚠️  This will remove all temporary files. Continue? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("❌ Cleanup cancelled.")
        return
    
    try:
        # Step 1: Cleanup temporary files
        cleanup_temporary_files()
        
        # Step 2: Create production structure
        create_production_structure()
        
        # Step 3: Update production files
        update_requirements()
        create_production_env_example()
        create_production_readme()
        
        # Step 4: Validate essential files
        all_good = validate_essential_files()
        
        # Step 5: Finalize
        finalize_production()
        
        print("\n" + "=" * 50)
        if all_good:
            print("🎉 PRODUCTION CLEANUP COMPLETE!")
            print("\n📋 Next Steps:")
            print("1. Run: python setup_env.py")
            print("2. Edit .env with your production credentials")
            print("3. Deploy with: docker-compose up -d")
            print("4. Access admin at: /admin/login")
            print("\n🔐 Your admin API key will be in the .env file")
        else:
            print("⚠️  CLEANUP COMPLETE WITH WARNINGS")
            print("Please resolve missing files before deployment.")
            
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        print("Please check the error and try again.")

if __name__ == "__main__":
    main() 
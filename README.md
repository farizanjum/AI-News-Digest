# 🚀 AI News Digest Platform

A modern, responsive news digest platform built with FastAPI and Supabase. Features user subscriptions, admin dashboard, contact system, and automated email notifications.

## ✨ Features

- **Beautiful Landing Page** - Modern, responsive design with gradient backgrounds
- **User Subscriptions** - Email collection with preferences and digest type selection  
- **Admin Dashboard** - Real-time analytics and subscriber management
- **Contact System** - Form submissions saved to database with email notifications
- **Email Integration** - Welcome emails and contact form notifications
- **Security** - Rate limiting, IP blocking, and secure authentication
- **Mobile Responsive** - Optimized for all devices

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **Frontend**: Jinja2 templates with modern CSS
- **Deployment**: Vercel
- **Email**: SMTP with HTML templates

## 🚀 Quick Start

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd ai-news-digest
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up Supabase**
   - Create tables using `database/supabase_setup.sql`
   - Update database connection in `database/supabase_client.py`

4. **Configure environment variables**
   - `ADMIN_API_KEY` - Admin dashboard access
   - `SENDER_EMAIL` & `SENDER_PASSWORD` - Email configuration
   - `UNSUBSCRIBE_SECRET` - Token generation

5. **Run locally**
```bash
python -m uvicorn main:app --reload
```

## 📱 API Endpoints

- `/` - Landing page
- `/subscribe` - User subscription 
- `/contact` - Contact form
- `/admin/login` - Admin authentication
- `/admin/dashboard` - Admin panel
- `/health` - System status
- `/unsubscribe` - Unsubscribe functionality

## 🗄️ Database Schema

- **subscribers** - User email subscriptions
- **contact_messages** - Contact form submissions  
- **email_logs** - Email activity tracking
- **digest_schedules** - Automated digest timing

## 🔧 Production Deployment

The platform is configured for Vercel deployment with:
- Serverless function setup
- Environment variable configuration
- Static file serving
- Database connection pooling

## 📄 License

MIT License - feel free to use this project for your own news digest platform!

---

**Live Demo**: [Your Vercel URL]  
**Admin Access**: Use your configured API key 
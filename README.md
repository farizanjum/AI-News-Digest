# 🤖 **AI News Digest - Autonomous Newsletter Platform**

> **An intelligent, fully automated news aggregation and delivery system powered by AI**

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/ai-news-digest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## 🌟 **Features**

### 🚀 **Core Functionality**
- ✅ **Autonomous News Scraping** - Automatically aggregates from multiple sources
- ✅ **AI-Powered Curation** - Smart content filtering and summarization  
- ✅ **Personalized Digests** - Tech news, UPSC prep, or both
- ✅ **Email Automation** - Beautiful HTML newsletters delivered daily
- ✅ **Admin Dashboard** - Real-time analytics and subscriber management
- ✅ **Mobile-Responsive** - Perfect experience on all devices

### 🎯 **User Experience**
- 📧 **Smart Subscriptions** - Easy signup with preference management
- 🔄 **Flexible Updates** - Change preferences anytime
- 🚫 **One-Click Unsubscribe** - Hassle-free opt-out
- 📱 **Mobile-First Design** - Touch-friendly interfaces
- 🎨 **Beautiful UI** - Modern glassmorphism design

### 🛡️ **Enterprise Features**
- 🔒 **Security-First** - Rate limiting, admin authentication
- 📊 **Analytics Dashboard** - Subscriber insights and metrics
- 🗄️ **Scalable Database** - SQLite (dev) + PostgreSQL (prod)
- ☁️ **Cloud-Ready** - Optimized for Vercel, AWS, and more
- 📈 **Performance Monitoring** - Built-in health checks

---

## 🚀 **Quick Start (5 Minutes to Live!)**

### **Local Development**
```bash
# Clone repository
git clone https://github.com/yourusername/ai-news-digest.git
cd ai-news-digest

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your email credentials

# Run the application
python main.py
```

### **Production Deployment**
```bash
# Deploy to Vercel (recommended)
vercel --prod

# Or use the one-click deploy button above ☝️
```

**📖 Full deployment guide: [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md)**

---

## 🏗️ **Architecture**

```
AI News Digest Platform
├── 🌐 FastAPI Backend
├── 🎨 Modern Web Interface  
├── 🗄️ Database Layer (SQLite/PostgreSQL)
├── 📧 Email Service (SMTP/SendGrid)
├── 🤖 News Scraping Engine
├── 📊 Admin Dashboard
└── ☁️ Cloud Deployment (Vercel)
```

### **Tech Stack**
- **Backend**: FastAPI, Python 3.11+
- **Frontend**: HTML5, TailwindCSS, JavaScript
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Email**: SMTP, SendGrid, Mailgun support
- **Deployment**: Vercel, Docker, traditional hosting
- **Monitoring**: Built-in analytics and health checks

---

## 📧 **Email Configuration**

### **Gmail Setup (Recommended)**
1. Enable 2-Factor Authentication
2. Generate App Password
3. Add credentials to environment:
```env
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
```

### **Alternative Providers**
- **SendGrid**: 100 emails/day free
- **Mailgun**: 5,000 emails/month free  
- **AWS SES**: Pay-as-you-go pricing

---

## 🗄️ **Database Setup**

### **Development (SQLite)**
```env
DATABASE_TYPE=sqlite
DB_PATH=news_digest.db
```

### **Production (PostgreSQL)**
```env
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:pass@host:port/db
```

**Supported Providers:**
- Vercel Postgres
- Neon (free tier)
- Supabase
- Railway
- AWS RDS

---

## 🎮 **Admin Dashboard**

Access the powerful admin interface:
```
https://your-domain.com/admin/login
```

**Features:**
- 📊 Real-time subscriber analytics
- 📈 Interactive charts and metrics
- 👥 Subscriber management
- 📧 Email log monitoring
- 🧪 Test digest sending
- 📱 Mobile-responsive design
- 🔄 Auto-refresh capabilities

---

## 🔒 **Security Features**

- ✅ **Rate Limiting** - Prevents abuse and spam
- ✅ **Admin Authentication** - Secure admin access
- ✅ **Input Validation** - Pydantic models for safety
- ✅ **CSRF Protection** - Secure form handling
- ✅ **Environment Variables** - Sensitive data protection
- ✅ **HTTPS Enforcement** - Encrypted connections

---

## 📊 **Monitoring & Analytics**

### **Built-in Metrics**
- Subscriber growth tracking
- Email delivery rates
- System performance monitoring
- Error logging and alerts

### **Vercel Integration**
- Automatic performance monitoring
- Function execution analytics
- Real-time error tracking
- Custom alerts and notifications

---

## 🔧 **Customization**

### **Add News Sources**
Edit `scrapers/` to add new RSS feeds:
```python
# Add to scrapers/news_scraper.py
RSS_SOURCES = [
    {"name": "Your Source", "url": "https://example.com/rss"}
]
```

### **Email Templates**
Customize HTML templates in `templates/`:
- `email_template.html` - Newsletter layout
- `welcome_email.html` - Welcome message
- `unsubscribe_email.html` - Goodbye message

### **Styling**
- Modern TailwindCSS framework
- Glassmorphism design system
- Mobile-first responsive layouts
- Dark theme optimized

---

## 🚀 **Deployment Options**

### **☁️ Vercel (Recommended)**
- One-click deployment
- Automatic HTTPS
- Global CDN
- Serverless functions
- Free tier available

### **🐳 Docker**
```bash
docker build -t ai-news-digest .
docker run -p 8000:8000 ai-news-digest
```

### **🌐 Traditional Hosting**
- VPS with Python 3.11+
- Nginx reverse proxy
- PM2 process management
- SSL certificate

---

## 📈 **Performance**

### **Optimizations**
- ⚡ Async/await throughout
- 🗜️ Gzip compression
- 📱 Mobile-optimized assets
- 🔄 Efficient caching
- 📊 Database query optimization

### **Scalability**
- Serverless-ready architecture
- Database connection pooling
- Horizontal scaling support
- CDN integration

---

## 🤝 **Contributing**

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### **Development Setup**
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black .
isort .
```

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🆘 **Support**

- 📧 **Email**: contact.ainewsdigest@gmail.com
- 📚 **Documentation**: [Full docs](https://your-docs-site.com)
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/ai-news-digest/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/ai-news-digest/discussions)

---

## 🎯 **Roadmap**

### **Coming Soon**
- [ ] 🤖 Advanced AI summarization
- [ ] 📱 Mobile app (React Native)
- [ ] 🔗 Social media integration
- [ ] 📊 Advanced analytics dashboard
- [ ] 🌍 Multi-language support
- [ ] 🎨 Theme customization
- [ ] 🔔 Real-time notifications
- [ ] 📈 A/B testing framework

---

## ⭐ **Star This Project**

If you find this project useful, please consider giving it a star on GitHub! It helps others discover the project and motivates continued development.

[![GitHub stars](https://img.shields.io/github/stars/yourusername/ai-news-digest.svg?style=social&label=Star)](https://github.com/yourusername/ai-news-digest)

---

**Built with ❤️ by the AI News Digest team**

*Ready to revolutionize news delivery? Deploy your instance today! 🚀* 
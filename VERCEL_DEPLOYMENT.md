# 🚀 **AI News Digest - Vercel Deployment Guide**

## 🎯 **Quick Start (5 Minutes to Live!)**

### **Prerequisites**
- GitHub account
- Vercel account (free)
- Email account for sending newsletters

---

## 📋 **Step 1: Prepare Your Repository**

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "🚀 Ready for production deployment!"
   git push origin main
   ```

---

## 🗄️ **Step 2: Database Setup (Choose One)**

### **Option A: Vercel Postgres (Recommended)**
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "Storage" → "Create Database" → "Postgres"
3. Follow setup instructions
4. Copy the `DATABASE_URL`

### **Option B: External PostgreSQL**
- **Neon**: Free PostgreSQL (recommended)
- **Supabase**: Free tier available
- **Railway**: Simple setup
- **ElephantSQL**: Free 20MB

---

## ⚙️ **Step 3: Environment Variables**

Set these in Vercel dashboard (`Settings` → `Environment Variables`):

### **Required Variables**
```env
# Database
DATABASE_TYPE=postgresql
DATABASE_URL=your_postgres_connection_string

# Email Configuration
SENDER_EMAIL=subscribe.ainewsdigest@gmail.com
SENDER_PASSWORD=your_app_password

# Security
ADMIN_API_KEY=your_secure_admin_key_here

# Optional: News API
NEWS_API_KEY=your_news_api_key
```

---

## 🌐 **Step 4: Deploy to Vercel**

### **Method 1: Vercel Dashboard (Easiest)**
1. Go to [Vercel Dashboard](https://vercel.com/new)
2. Click "Import Git Repository"
3. Select your GitHub repository
4. Configure:
   - **Framework Preset**: Other
   - **Root Directory**: `./`
   - **Build Command**: (leave empty)
   - **Output Directory**: (leave empty)
5. Add environment variables
6. Click "Deploy" 🚀

### **Method 2: Vercel CLI**
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Follow prompts and set environment variables
```

---

## 🔧 **Step 5: Post-Deployment Setup**

### **A. Verify Deployment**
1. Visit your Vercel URL
2. Test subscription: `https://your-app.vercel.app`
3. Test admin access: `https://your-app.vercel.app/admin/login`

### **B. Configure Custom Domain (Optional)**
1. In Vercel dashboard → `Settings` → `Domains`
2. Add your custom domain
3. Update DNS records as instructed

### **C. Set Up Monitoring**
- Vercel provides automatic monitoring
- Check `Functions` tab for performance metrics
- Set up alerts in Vercel dashboard

---

## 📧 **Step 6: Email Setup**

### **Gmail App Password Setup**
1. Enable 2FA on Gmail
2. Go to Google Account settings
3. Search "App passwords"
4. Generate password for "Mail"
5. Use this as `SENDER_PASSWORD`

### **Alternative Email Providers**
- **SendGrid**: Free tier (100 emails/day)
- **Mailgun**: Free tier (5,000 emails/month)
- **AWS SES**: Pay-as-you-go

---

## 🤖 **Step 7: Automated Digest Sending**

Since Vercel is serverless, we need external scheduling:

### **Option A: GitHub Actions (Recommended)**
```yaml
# .github/workflows/send-digest.yml
name: Send Daily Digest
on:
  schedule:
    - cron: '0 9 * * *'  # 9 AM UTC daily
jobs:
  send-digest:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Digest
        run: |
          curl -X POST "https://your-app.vercel.app/api/digest/send-all" \
            -H "X-Admin-Key: ${{ secrets.ADMIN_API_KEY }}"
```

### **Option B: Vercel Cron (Pro Plan)**
```json
{
  "crons": [
    {
      "path": "/api/digest/send-all",
      "schedule": "0 9 * * *"
    }
  ]
}
```

### **Option C: External Services**
- **Cron-job.org**: Free cron service
- **EasyCron**: Free tier available
- **Zapier**: Advanced automation

---

## 🔒 **Step 8: Security Checklist**

✅ **Environment Variables Set**
✅ **Admin Key Generated (32+ characters)**
✅ **Email Credentials Secured**
✅ **Database Connection Encrypted**
✅ **HTTPS Enabled (automatic on Vercel)**

---

## 🚨 **Common Issues & Solutions**

### **Build Errors**
```bash
# If you get dependency errors
pip install -r requirements.txt
vercel --prod
```

### **Database Connection Issues**
- Ensure `DATABASE_URL` is correctly formatted
- Check PostgreSQL connection limits
- Verify SSL requirements

### **Email Sending Issues**
- Test Gmail app password locally
- Check SMTP settings
- Verify email domain reputation

---

## 📊 **Step 9: Monitor Your Deployment**

### **Vercel Analytics**
- Automatic traffic monitoring
- Performance insights
- Error tracking

### **Application Monitoring**
- Check `/admin/dashboard` for system health
- Monitor email delivery logs
- Track subscriber growth

---

## 🎉 **Congratulations! You're Live!**

Your AI News Digest is now running on Vercel:

- **Website**: `https://your-app.vercel.app`
- **Admin Panel**: `https://your-app.vercel.app/admin/login`
- **API**: `https://your-app.vercel.app/api/`

### **Next Steps**
1. 📈 **Monitor Performance**: Check Vercel dashboard
2. 📧 **Test Email Delivery**: Send test digests
3. 🎨 **Customize**: Update branding and content
4. 📱 **Share**: Promote your news digest service
5. 💰 **Scale**: Upgrade plans as you grow

---

## 🆘 **Need Help?**

- **Vercel Docs**: https://vercel.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **PostgreSQL**: Check your provider's documentation

**Your AI News Digest is now LIVE and ready to serve users! 🚀** 
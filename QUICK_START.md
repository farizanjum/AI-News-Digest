# 🚀 QUICK START GUIDE

## 1. Generate Secure Environment File

```bash
# Generate .env file with secure keys
python setup_env.py
```

This will create a `.env` file with:
- ✅ Auto-generated secure admin keys
- ✅ No hardcoded API keys
- ✅ Configurable email settings

## 2. Configure Your API Keys

Edit the `.env` file and update:

```bash
# Your Gmail credentials
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_gmail_app_password

# Get your own API keys (REQUIRED)
NEWS_API_KEY=your_newsapi_key_here
GROK_API_KEY=your_grok_api_key_here

# Your test email (optional)
TEST_USER_EMAIL=your_email@gmail.com
RECIPIENT_EMAIL=your_email@gmail.com
```

### 🔑 Where to Get API Keys:

1. **NewsAPI.org**: https://newsapi.org/register
2. **Grok AI**: https://console.x.ai/

### 📧 Gmail App Password:

1. Enable 2FA on your Gmail account
2. Go to Google Account Settings → Security → App passwords
3. Generate an app password for "Mail"

## 3. Add Test User (Optional)

```bash
# Add yourself as a test user
python add_test_user.py
```

## 4. Start the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python main.py
```

## 5. Test the Platform

Visit: http://localhost:8000

### 🔧 Admin Endpoints (Use your admin key):

```bash
# Get your admin key from .env file
ADMIN_KEY=$(grep ADMIN_API_KEY .env | cut -d'=' -f2)

# Test admin endpoints
curl -H "X-Admin-Key: $ADMIN_KEY" http://localhost:8000/subscribers
curl -H "X-Admin-Key: $ADMIN_KEY" http://localhost:8000/api/stats
```

## 6. Send Test Digest

```bash
# Send test tech digest
curl -X POST -H "X-Admin-Key: $ADMIN_KEY" \
  "http://localhost:8000/api/digest/send-test?digest_type=tech"

# Send test UPSC digest
curl -X POST -H "X-Admin-Key: $ADMIN_KEY" \
  "http://localhost:8000/api/digest/send-test?digest_type=upsc"
```

## 🔒 Security Features

- ✅ No hardcoded API keys
- ✅ Admin endpoints protected with API key
- ✅ Secure unsubscribe tokens
- ✅ Input validation and sanitization
- ✅ Environment-based configuration

## 🐳 Docker Deployment

```bash
# Build and run with Docker
docker-compose up -d
```

## 📞 Need Help?

1. Check the logs: `tail -f *.log`
2. Verify your .env file has all required values
3. Test your Gmail app password
4. Ensure your API keys are valid

## 🎯 Next Steps

1. Set up automated scheduling with cron
2. Configure your domain for production
3. Add more subscribers via the web interface
4. Monitor with the admin dashboard

---

**🔐 Security Note**: Never commit your `.env` file to version control! 
# UPSC Daily Digest

This module fetches, classifies, and emails a daily digest of UPSC-relevant news, grouped by category for aspirants.

## Features
- Fetches news from top Indian sources
- Classifies news into Polity, Governance, Environment, Economy, Science, Scheme, Editorial, International Relations, Indian Society, and General UPSC
- Sends a neat, categorized HTML email
- Easy to customize topics and sources

## Usage
1. Set up your `.env` file with NewsAPI and email credentials.
2. Run:
   ```bash
   python upsc_digest.py
   ```
3. Check your email for the digest!

## Customization
- Edit `upsc_digest.py` to change categories, keywords, or sources.
- Edit `templates/digest_email.html` for email appearance.

## Folder Structure
- `upsc_digest.py` — main script
- `templates/digest_email.html` — email template

---
For any issues or suggestions, open an issue or contact the maintainer. 
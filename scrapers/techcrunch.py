import requests
import xml.etree.ElementTree as ET
import datetime
import re


class TechCrunchScraper:
    """TechCrunch RSS feed scraper."""
    
    def __init__(self):
        self.base_url = "https://techcrunch.com/feed/"
    
    def clean_html(self, raw_html):
        """Remove HTML tags from text."""
        clean_re = re.compile('<.*?>')
        return re.sub(clean_re, '', raw_html)
    
    def trim_description(self, text, max_words=30):
        """Trim description to specified number of words."""
        words = text.split()
        if len(words) <= max_words:
            return text
        desc = " ".join(words[:max_words])
        if not desc.endswith(('.', '!', '?')):
            desc += '...'
        return desc
    
    def scrape_articles(self, limit=10):
        """Scrape articles from TechCrunch RSS feed."""
        articles = []
        
        try:
            response = requests.get(self.base_url, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            
            today = datetime.datetime.now().date()
            count = 0
            
            for item in items:
                if count >= limit:
                    break
                    
                title = item.findtext('title', 'No Title').strip()
                link = item.findtext('link', 'No Link').strip()
                raw_desc = item.findtext('description', 'No Description')
                description = self.clean_html(raw_desc).strip()
                description = self.trim_description(description)
                
                # Try to parse publication date
                pub_date_text = item.findtext('pubDate')
                is_recent = True
                if pub_date_text:
                    try:
                        pub_date = datetime.datetime.strptime(pub_date_text[:16], '%a, %d %b %Y').date()
                        # Allow articles from last 7 days
                        week_ago = today - datetime.timedelta(days=7)
                        is_recent = pub_date >= week_ago
                    except:
                        pass  # Keep article if date parsing fails
                
                if is_recent:
                    articles.append({
                        "title": title,
                        "description": description,
                        "link": link,
                        "source": "TechCrunch"
                    })
                    count += 1
                    
        except Exception as e:
            print(f"Error scraping TechCrunch: {str(e)}")
            
        return articles 
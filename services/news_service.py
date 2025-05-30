import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from dotenv import load_dotenv
import json

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.newsapi_key = os.getenv('NEWS_API_KEY')
        self.grok_api_key = os.getenv('GROK_API_KEY')
    
    async def fetch_tech_articles(self, preferences: str = "all") -> List[Dict]:
        """Fetch tech news from news_digest.json and other sources."""
        all_articles = []
        
        # First try to load from news_digest.json (primary source)
        try:
            logger.info("Loading articles from news_digest.json")
            with open('news_digest.json', 'r', encoding='utf-8') as f:
                articles = json.load(f)
                
            # Process articles to ensure proper format
            for article in articles:
                # Ensure all required fields are present
                processed_article = {
                    'title': article.get('title', 'No Title'),
                    'description': article.get('description', 'No description available'),
                    'url': article.get('link', article.get('url', '#')),
                    'source': {'name': 'Tech News'},
                    'publishedAt': datetime.now().isoformat(),
                    'urlToImage': None
                }
                all_articles.append(processed_article)
                
            logger.info(f"Loaded {len(all_articles)} articles from news_digest.json")
            
        except Exception as e:
            logger.error(f"Error loading from news_digest.json: {e}")
            
            # Fallback to other sources if news_digest.json is not available
            try:
                # Fetch from NewsAPI
                if self.newsapi_key:
                    newsapi_articles = await self._fetch_newsapi_articles(preferences)
                    all_articles.extend(newsapi_articles)
                
                # Fetch from scrapers
                try:
                    # AI News scraper
                    from scrapers.ai_news import AINewsScraper
                    ai_scraper = AINewsScraper()
                    ai_articles = await ai_scraper.fetch_articles()
                    all_articles.extend(ai_articles)
                except Exception as e:
                    logger.error(f"Error fetching AI news: {e}")
                
                try:
                    # Computer Use scraper (RSS feeds)
                    computer_articles = await self._fetch_computer_use_articles()
                    all_articles.extend(computer_articles)
                except Exception as e:
                    logger.error(f"Error fetching computer use articles: {e}")
            
            except Exception as e:
                logger.error(f"Error fetching from APIs: {e}")
            
            # If still no articles, try tech_news_with_content.json as last resort
            if len(all_articles) < 5:
                logger.info("Limited articles from APIs, loading from tech_news_with_content.json")
                try:
                    with open('tech_news_with_content.json', 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # Get articles from the 'all_articles' key
                    local_articles = data.get('all_articles', [])
                    
                    # Process and improve the articles
                    processed_articles = []
                    for article in local_articles:
                        # Improve description if empty
                        description = article.get('description', '').strip()
                        if not description or description == "":
                            # Use content snippet if available
                            content = article.get('content', '')
                            if content and len(content) > 50:
                                # Take first sentence or first 150 chars
                                sentences = content.split('. ')
                                if len(sentences) > 0:
                                    description = sentences[0].strip()
                                    if not description.endswith('.'):
                                        description += '.'
                                else:
                                    description = content[:150].strip() + '...'
                            else:
                                # Generate description from title and category
                                category = article.get('category_hint', 'Technology')
                                title = article.get('title', 'News Article')
                                description = f"Latest {category.lower()} news: {title[:100]}..."
                        
                        # Ensure we have a proper description
                        if len(description) < 20:
                            description = f"Breaking news in {article.get('category_hint', 'technology').lower()}. Read more for details."
                        
                        article['description'] = description
                        processed_articles.append(article)
                    
                    all_articles.extend(processed_articles)
                    logger.info(f"Loaded {len(processed_articles)} articles from local file")
                    
                except Exception as e:
                    logger.error(f"Error loading from tech_news_with_content.json: {e}")
        
        # Remove duplicates based on URL
        unique_articles = {}
        for article in all_articles:
            url = article.get('url', article.get('link', ''))
            if url and url not in unique_articles:
                unique_articles[url] = article
        
        result = list(unique_articles.values())
        logger.info(f"Total unique articles: {len(result)}")
        return result[:15]  # Limit to 15 articles
    
    async def _fetch_newsapi_articles(self, preferences: str) -> List[Dict]:
        """Fetch articles from NewsAPI."""
        try:
            from_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Prepare query based on preferences
            if preferences == "all" or not preferences:
                query = '"artificial intelligence" OR ai OR cloud OR cybersecurity OR startup OR technology'
            else:
                prefs = [p.strip().lower() for p in preferences.split(",")]
                keyword_map = {
                    'ai': ['"artificial intelligence"', 'ai', 'machine learning'],
                    'cloud': ['cloud', '"cloud computing"', 'aws', 'azure'],
                    'cybersecurity': ['cybersecurity', 'security', 'hacking'],
                    'startup': ['startup', 'entrepreneur', 'venture'],
                }
                keywords = []
                for cat in prefs:
                    keywords.extend(keyword_map.get(cat, [cat]))
                query = ' OR '.join(list(dict.fromkeys(keywords)))
            
            params = {
                'apiKey': self.newsapi_key,
                'q': query,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 20,
                'from': from_date
            }
            
            response = requests.get('https://newsapi.org/v2/everything', params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('articles', [])
            
        except Exception as e:
            logger.error(f"Error fetching NewsAPI articles: {e}")
            return []
    
    async def _fetch_computer_use_articles(self) -> List[Dict]:
        """Fetch articles using the computer-use scraper."""
        try:
            # Import and run the computer use scraper
            import sys
            import subprocess
            import json
            
            # Run the scraper
            result = subprocess.run([
                sys.executable, 'scrapers/computer-use-scraper.py'
            ], capture_output=True, text=True, cwd='.')
            
            if result.returncode == 0:
                # Load the generated JSON file
                try:
                    with open('news_digest.json', 'r', encoding='utf-8') as f:
                        articles = json.load(f)
                    return articles
                except FileNotFoundError:
                    logger.warning("news_digest.json not found after running scraper")
                    return []
            else:
                logger.error(f"Computer use scraper failed: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"Error running computer use scraper: {e}")
            return []
    
    def categorize_articles(self, articles: List[Dict], preferences: List[str]) -> Dict[str, List[Dict]]:
        """Categorize articles based on preferences."""
        if isinstance(preferences, str):
            preferences = [p.strip() for p in preferences.split(',')]
        
        # Expand "all" to main categories
        if 'all' in [p.lower() for p in preferences]:
            preferences = ['AI', 'Cloud', 'Cybersecurity', 'Startup']
        
        # Keyword mapping for categorization
        keyword_map = {
            'ai': ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 
                   'neural network', 'gpt', 'openai', 'llm', 'chatgpt', 'claude'],
            'cloud': ['cloud', 'aws', 'azure', 'gcp', 'google cloud', 'serverless', 'saas'],
            'cybersecurity': ['cybersecurity', 'security', 'hacking', 'malware', 'phishing', 
                             'ransomware', 'data breach', 'encryption'],
            'startup': ['startup', 'entrepreneur', 'venture', 'funding', 'unicorn', 
                       'incubator', 'accelerator']
        }
        
        categories = {}
        for pref in preferences:
            categories[pref.title()] = []
        categories['Other'] = []
        
        for article in articles:
            matched = False
            text = (
                article.get('title', '') + ' ' + 
                article.get('description', '') + ' ' +
                article.get('category', '')
            ).lower()
            
            for pref in preferences:
                pref_lower = pref.lower()
                if pref_lower in keyword_map:
                    for keyword in keyword_map[pref_lower]:
                        if keyword in text:
                            categories[pref.title()].append(article)
                            matched = True
                            break
                if matched:
                    break
            
            if not matched:
                categories['Other'].append(article)
        
        return categories
    
    def format_tech_digest(self, articles: List[Dict], subscriber_name: str, 
                          preferences: List[str], subscriber_email: str = "") -> str:
        """Format tech news articles into modern HTML digest."""
        try:
            with open('email_template.html', 'r', encoding='utf-8') as f:
                template = f.read()
            
            # Build modern article blocks
            articles_html = ""
            
            # Limit to top 10 articles for better performance
            for article in articles[:10]:
                title = article.get('title', 'No title')
                source = article.get('source', {})
                if isinstance(source, dict):
                    source_name = source.get('name', 'Tech News')
                else:
                    source_name = str(source) if source else 'Tech News'
                
                # Try to get more specific source names from URLs or content
                url = article.get('url', article.get('link', '#'))
                if 'techcrunch.com' in url:
                    source_name = 'TechCrunch'
                elif 'technologyreview.com' in url:
                    source_name = 'MIT Technology Review'
                elif 'theverge.com' in url:
                    source_name = 'The Verge'
                elif 'thehackernews.com' in url:
                    source_name = 'The Hacker News'
                elif 'rss.app' in url:
                    source_name = 'AI News RSS'
                
                description = article.get('description', 'No description available')
                
                # Clean up description and ensure good length
                import re
                description = re.sub('<.*?>', '', description)
                description = description.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                description = description.replace('&#8217;', "'").replace('&#8220;', '"').replace('&#8221;', '"')
                
                # Ensure description is substantial
                if len(description.strip()) < 50:
                    description = f"Breaking news in technology: {title}. Click to read more about this important development in the tech industry."
                elif len(description) > 250:
                    description = description[:250].strip() + '...'
                
                published_at = article.get('publishedAt', '')
                
                if published_at:
                    try:
                        from datetime import datetime
                        pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        formatted_date = pub_date.strftime('%B %d, %Y')
                    except:
                        formatted_date = 'Today'
                else:
                    formatted_date = 'Today'
                
                # Create modern article with individual source label
                articles_html += f'''
                <div class="article">
                    <div class="article-title">
                        <a href="{url}" style="color: #ffffff; text-decoration: none;">{title}</a>
                    </div>
                    <div class="article-source">
                        Source: {source_name}
                    </div>
                    <div class="article-description">
                        {description}
                    </div>
                    <a href="{url}" class="read-more" style="color: #ffffff !important; text-decoration: none;">Read Full Article →</a>
                </div>
                '''
            
            # Replace template placeholders
            current_date = datetime.now().strftime('%B %d, %Y')
            
            # Create URLs with proper email encoding
            import urllib.parse
            base_url = os.getenv('BASE_URL', 'http://localhost:8000')
            encoded_email = urllib.parse.quote(subscriber_email) if subscriber_email else "subscriber"
            unsubscribe_url = f"{base_url}/unsubscribe/{encoded_email}"
            preferences_url = f"{base_url}/preferences?email={encoded_email}"
            
            template = template.replace('{{subscriber_name}}', subscriber_name)
            template = template.replace('{{current_date}}', current_date)
            template = template.replace('{{CATEGORY_BLOCKS}}', articles_html)
            template = template.replace('{{total_articles}}', str(len(articles)))
            template = template.replace('{{unsubscribe_url}}', unsubscribe_url)
            template = template.replace('{{preferences_url}}', preferences_url)
            
            return template
            
        except Exception as e:
            logger.error(f"Error formatting tech digest: {e}")
            return self._get_error_template(subscriber_name)
    
    def _get_error_template(self, subscriber_name: str) -> str:
        """Return a basic error template if main template fails."""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #00f2fe;">Daily News Digest</h1>
            <p>Dear {subscriber_name},</p>
            <p>We encountered an issue generating your digest today. Please try again later.</p>
            <p>Best regards,<br>The News Digest Team</p>
        </body>
        </html>
        """
    
    async def fetch_upsc_articles(self) -> List[Dict]:
        """Fetch UPSC-related articles."""
        try:
            from upsc_digest.upsc_digest import UPSCDigest
            upsc_service = UPSCDigest()
            return upsc_service.fetch_news()
        except Exception as e:
            logger.error(f"Error fetching UPSC articles: {e}")
            return []
    
    def get_custom_curated_news(self, preferences: str, custom_interests: str) -> List[Dict]:
        """Get curated news from Grok based on custom interests."""
        try:
            if not self.grok_api_key:
                logger.warning("Grok API key not found")
                return []
            
            prompt = f"""
            Please curate the latest technology news based on these preferences: {preferences}
            With specific focus on: {custom_interests}
            
            Provide a JSON list of articles with the following format:
            [
                {{
                    "title": "Article title",
                    "description": "Brief description",
                    "url": "https://example.com",
                    "source": "Source name",
                    "category": "Category"
                }}
            ]
            """
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.grok_api_key}"
            }
            
            data = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a technology news curator. Provide curated news articles in the requested JSON format."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "model": "grok-3-latest",
                "stream": False,
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Try to extract JSON from the response
                import json
                import re
                
                # Look for JSON array in the response
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    try:
                        articles = json.loads(json_match.group())
                        return articles
                    except json.JSONDecodeError:
                        pass
                
                logger.warning("Could not parse Grok response as JSON")
                return []
            else:
                logger.error(f"Grok API error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting custom curated news: {e}")
            return [] 
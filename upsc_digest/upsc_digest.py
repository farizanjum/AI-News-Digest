import os
from datetime import datetime, timedelta
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from dotenv import load_dotenv
import logging
import re
from typing import Dict, List, Tuple
import time
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upsc_digest.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

class UPSCDigest:
    def __init__(self):
        # API keys from environment only - no fallbacks for security
        self.newsapi_key = os.getenv('NEWS_API_KEY')
        # NewsAPI.ai key for enhanced UPSC coverage
        self.newsapi_ai_key = os.getenv('NEWSAPI_AI_KEY')
        # WorldNews API key
        self.worldnews_key = os.getenv('WORLDNEWS_API_KEY')
        # NYT API keys
        self.nyt_key = os.getenv('NYT_API_KEY')
        self.nyt_secret = os.getenv('NYT_API_SECRET')
        
        # Validate required API keys
        if not self.newsapi_key:
            raise ValueError("NEWS_API_KEY is required but not found in environment variables")
        
        # NewsAPI.org sources
        self.newsapi_sources = [
            'the-hindu',
            'the-times-of-india'
        ]
        # NewsAPI.ai sources
        self.newsapi_ai_sources = [
            'the-indian-express',
            'the-wire', 
            'scroll.in',
            'the-quint',
            'ndtv',
            'news18'
        ]
        self.newsapi_ai_source_uris = {
            'the-indian-express': 'indianexpress.com',
            'ndtv': 'ndtv.com',
            'news18': 'news18.com'
        }
        self.topics = [
            'UPSC',
            'polity',
            'governance',
            'environment',
            'economy',
            'science',
            'scheme',
            'editorial',
            'international relations',
            'Indian society'
        ]
        # Define category keywords with weights
        self.category_keywords = {
            'Polity': {
                'primary': ['polity', 'constitution', 'parliament', 'legislation', 'supreme court', 'judiciary'],
                'secondary': ['bill', 'law', 'amendment', 'governor', 'president', 'cabinet', 'election commission'],
                'tertiary': ['fundamental rights', 'directive principles', 'constitutional', 'democracy']
            },
            'Governance': {
                'primary': ['governance', 'policy', 'administration', 'bureaucracy'],
                'secondary': ['transparency', 'accountability', 'good governance', 'public service'],
                'tertiary': ['civil service', 'e-governance', 'governance reforms', 'digital india', 'right to information']
            },
            'Environment': {
                'primary': ['environment', 'climate', 'biodiversity', 'wildlife', 'forest'],
                'secondary': ['pollution', 'conservation', 'sustainable', 'ecology'],
                'tertiary': ['global warming', 'carbon', 'greenhouse', 'environmental', 'species', 'ecosystem', 'natural resources']
            },
            'Economy': {
                'primary': ['economy', 'gdp', 'inflation', 'fiscal', 'monetary'],
                'secondary': ['budget', 'tax', 'bank', 'finance', 'economic', 'trade'],
                'tertiary': ['industry', 'investment', 'stock market', 'employment', 'unemployment', 'agriculture', 'msme', 'niti aayog', 'economic survey']
            },
            'Science': {
                'primary': ['science', 'technology', 'research', 'innovation', 'isro', 'space'],
                'secondary': ['nasa', 'scientist', 'discovery', 'invention', 'scientific'],
                'tertiary': ['satellite', 'quantum', 'nobel', 'biotech', 'genome', 'dna', 'physics', 'chemistry', 'biology']
            },
            'Scheme': {
                'primary': ['scheme', 'yojana', 'mission', 'initiative', 'programme'],
                'secondary': ['government scheme', 'flagship', 'campaign', 'pradhan mantri'],
                'tertiary': ['ujjwala', 'jan dhan', 'ayushman', 'swachh bharat', 'beti bachao', 'mudra', 'startup india', 'digital india']
            },
            'Editorial': {
                'primary': ['editorial', 'opinion', 'analysis', 'column'],
                'secondary': ['perspective', 'viewpoint', 'commentary', 'leader'],
                'tertiary': ['edit', 'op-ed', 'thought', 'insight']
            },
            'International Relations': {
                'primary': ['international', 'foreign', 'diplomacy', 'bilateral', 'multilateral'],
                'secondary': ['united nations', 'un', 'world bank', 'imf', 'global'],
                'tertiary': ['geopolitics', 'india-china', 'india-us', 'india-pakistan', 'summit', 'treaty', 'agreement', 'border', 'trade deal', 'foreign policy']
            },
            'Indian Society': {
                'primary': ['society', 'social', 'culture', 'demography', 'population'],
                'secondary': ['gender', 'women', 'child', 'education', 'health'],
                'tertiary': ['poverty', 'inequality', 'tribal', 'caste', 'minority', 'diversity', 'urban', 'rural', 'migration', 'social justice']
            }
        }

    def fetch_from_newsapi(self) -> List[Dict]:
        """Fetch news from NewsAPI.org only with its key."""
        articles = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        search_terms = ['UPSC', 'government policy', 'india economy', 'supreme court']
        for term in search_terms:
            try:
                url = 'https://newsapi.org/v2/everything'
                params = {
                    'q': term,
                    'from': start_date_str,
                    'to': end_date_str,
                    'language': 'en',
                    'sortBy': 'relevancy',
                    'pageSize': 20,
                    'apiKey': self.newsapi_key
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 401:
                    logging.error(f"NewsAPI.org: 401 Unauthorized for key {self.newsapi_key[:6]}... Check your API key.")
                    continue
                if response.status_code == 200:
                    data = response.json()
                    if data['status'] == 'ok' and data['articles']:
                        filtered_articles = []
                        for article in data['articles']:
                            source_name = article.get('source', {}).get('name', '').lower()
                            if any(src in source_name for src in ['hindu', 'times', 'indian', 'express']):
                                filtered_articles.append(article)
                        articles.extend(filtered_articles)
                        logging.info(f"NewsAPI.org: Found {len(filtered_articles)} relevant articles for '{term}'")
                else:
                    logging.warning(f"NewsAPI.org: Error {response.status_code} for term '{term}': {response.text}")
                time.sleep(1)
            except Exception as e:
                logging.error(f"NewsAPI.org: Error fetching term '{term}': {str(e)}")
                continue
        return articles

    def fetch_from_newsapi_ai(self) -> List[Dict]:
        """Fetch news from NewsAPI.ai."""
        articles = []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            
            # NewsAPI.ai uses different date format
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # UPSC-related keywords for NewsAPI.ai
            keywords = [
                'UPSC OR "civil service"',
                'government policy india',
                'supreme court india',
                'economy india',
                'environment policy india'
            ]
            
            for keyword in keywords:
                try:
                    url = 'https://newsapi.ai/api/v1/article/getArticles'
                    
                    # NewsAPI.ai request body
                    body = {
                        "action": "getArticles",
                        "keyword": keyword,
                        "articlesPage": 1,
                        "articlesCount": 50,
                        "articlesSortBy": "date",
                        "dataType": ["news"],
                        "forceMaxDataTimeWindow": 31,
                        "resultType": "articles",
                        "dateStart": start_date_str,
                        "dateEnd": end_date_str,
                        "lang": ["eng"],
                        "locationUri": "http://en.wikipedia.org/wiki/India",  # Focus on India
                        "apiKey": self.newsapi_ai_key
                    }
                    
                    logging.info(f"NewsAPI.ai: Searching for '{keyword}'")
                    response = requests.post(url, json=body, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if 'articles' in data and 'results' in data['articles']:
                            raw_articles = data['articles']['results']
                            
                            # Convert NewsAPI.ai format to standard format
                            for article in raw_articles:
                                try:
                                    formatted_article = {
                                        'title': article.get('title', ''),
                                        'description': article.get('body', '')[:300] + '...' if article.get('body') else '',
                                        'url': article.get('url', ''),
                                        'publishedAt': article.get('dateTime', ''),
                                        'source': {
                                            'name': article.get('source', {}).get('title', 'NewsAPI.ai Source')
                                        },
                                        'content': article.get('body', '')
                                    }
                                    
                                    # Only add if we have essential fields
                                    if formatted_article['title'] and formatted_article['url']:
                                        articles.append(formatted_article)
                                        
                                except Exception as e:
                                    logging.warning(f"NewsAPI.ai: Error formatting article: {str(e)}")
                                    continue
                            
                            logging.info(f"NewsAPI.ai: Found {len(raw_articles)} articles for '{keyword}'")
                    else:
                        logging.warning(f"NewsAPI.ai: Error {response.status_code} for '{keyword}': {response.text}")
                    
                    # Add delay between requests
                    time.sleep(2)
                    
                except Exception as e:
                    logging.error(f"NewsAPI.ai: Error fetching keyword '{keyword}': {str(e)}")
                    continue
                    
        except Exception as e:
            logging.error(f"NewsAPI.ai: Fatal error: {str(e)}")
        
        return articles

    def fetch_from_worldnews(self) -> List[Dict]:
        """Fetch international news from World News API for International Relations category."""
        articles = []
        try:
            url = 'https://api.worldnewsapi.com/search-news'
            params = {
                'api-key': self.worldnews_key,
                'text': 'India OR International Relations',
                'language': 'en',
                'number': 30,
                'sort': 'publish-time'
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 401:
                logging.error(f"World News API: 401 Unauthorized for key {self.worldnews_key[:6]}... Check your API key.")
                return []
            if response.status_code == 200:
                data = response.json()
                for item in data.get('news', []):
                    articles.append({
                        'title': item.get('title', ''),
                        'description': item.get('text', ''),
                        'url': item.get('url', ''),
                        'publishedAt': item.get('publish_date', ''),
                        'source': {'name': item.get('source', '')},
                        'content': item.get('text', '')
                    })
                logging.info(f"World News API: Found {len(articles)} international articles.")
            else:
                logging.warning(f"World News API: Error {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"World News API: {str(e)}")
        return articles

    def fetch_from_nyt_timeswire(self) -> List[Dict]:
        """Fetch international news from NYT TimesWire API for International Relations category."""
        articles = []
        try:
            url = f'https://api.nytimes.com/svc/news/v3/content/all/world.json?api-key={self.nyt_key}'
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('results', []):
                    # Only include international/UPSC relevant
                    if any(kw in item.get('title', '').lower() for kw in ['india', 'international', 'diplomacy', 'foreign', 'parliament', 'modi', 'delhi', 'supreme court']):
                        articles.append({
                            'title': item.get('title', ''),
                            'description': item.get('abstract', ''),
                            'url': item.get('url', ''),
                            'publishedAt': item.get('published_date', ''),
                            'source': {'name': 'NYT TimesWire'},
                            'content': item.get('abstract', '')
                        })
            else:
                logging.warning(f"NYT TimesWire: Error {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"NYT TimesWire: {str(e)}")
        return articles

    def fetch_from_nyt_topstories(self) -> List[Dict]:
        """Fetch international news from NYT Top Stories API for International Relations category."""
        articles = []
        try:
            url = f'https://api.nytimes.com/svc/topstories/v2/world.json?api-key={self.nyt_key}'
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('results', []):
                    # Only include international/UPSC relevant
                    if any(kw in item.get('title', '').lower() for kw in ['india', 'international', 'diplomacy', 'foreign', 'parliament', 'modi', 'delhi', 'supreme court']):
                        articles.append({
                            'title': item.get('title', ''),
                            'description': item.get('abstract', ''),
                            'url': item.get('url', ''),
                            'publishedAt': item.get('published_date', ''),
                            'source': {'name': 'NYT Top Stories'},
                            'content': item.get('abstract', '')
                        })
            else:
                logging.warning(f"NYT Top Stories: Error {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"NYT Top Stories: {str(e)}")
        return articles

    def calculate_category_score(self, text: str, category: str) -> float:
        """Calculate a score for how well an article matches a category."""
        score = 0.0
        text = text.lower()
        
        # Check each keyword level with different weights
        for keyword in self.category_keywords[category]['primary']:
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, text):
                score += 3.0  # Primary keywords have highest weight
                
        for keyword in self.category_keywords[category]['secondary']:
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, text):
                score += 2.0  # Secondary keywords have medium weight
                
        for keyword in self.category_keywords[category]['tertiary']:
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, text):
                score += 1.0  # Tertiary keywords have lowest weight
        
        return score

    def has_primary_keyword(self, text, category_keywords):
        text = text.lower()
        return any(kw in text for kw in category_keywords['primary'])

    def truncate_description(self, desc, max_words=40):
        desc = re.sub(r'\s+', ' ', desc).strip()
        words = desc.split()
        if len(words) > max_words:
            return ' '.join(words[:max_words]) + '...'
        return desc

    def group_articles_by_category(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        grouped = {cat: [] for cat in self.category_keywords}
        grouped['General UPSC'] = []  # Will only be used for articles with primary keyword in General UPSC (if you want)
        for article in articles:
            title = article.get('title', '')
            description = article.get('description', '')
            content = article.get('content', '')
            # Only consider categories where a primary keyword is present in title or description
            eligible_categories = [
                cat for cat, kws in self.category_keywords.items()
                if self.has_primary_keyword(title, kws) or self.has_primary_keyword(description, kws)
            ]
            if eligible_categories:
                full_text = f"{title} {description} {content}"
                scores = {cat: self.calculate_category_score(full_text, cat) for cat in eligible_categories}
                best_category = max(scores.items(), key=lambda x: x[1])
                grouped[best_category[0]].append(article)
            # else: drop the article entirely (do not add to General UPSC)
        return grouped

    def render_digest(self, grouped):
        max_articles_per_category = 4
        category_blocks = ""
        for category, category_articles in grouped.items():
            if category_articles:
                articles_to_show = category_articles[:max_articles_per_category]
                category_blocks += f'<div class="category-block"><div class="section-title">{category} ({len(articles_to_show)})</div>'
                for article in articles_to_show:
                    title = article.get('title', 'No Title')
                    description = article.get('description', '')
                    url = article.get('url', '#')
                    source = article.get('source', {}).get('name', 'Unknown Source')
                    published_at = article.get('publishedAt', '')
                    # Format date
                    try:
                        date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        formatted_date = date.strftime('%B %d, %Y at %I:%M %p')
                    except Exception:
                        formatted_date = published_at
                    # Clean and truncate description
                    if not description or len(description) < 30:
                        content = article.get('content', '')
                        if content and len(content) > 30:
                            description = content
                        else:
                            description = "Click to read the full article."
                    description = self.truncate_description(description)
                    category_blocks += f"""
                    <div class=\"article-block\">
                        <div class=\"article-title\">
                            <a href=\"{url}\" target=\"_blank\">{title}</a>
                        </div>
                        <div class=\"article-meta\">
                            <span class=\"source\">{source}</span>
                            <span class=\"date\">{formatted_date}</span>
                        </div>
                        <div class=\"article-description\">{description}</div>
                        <a href=\"{url}\" class=\"article-link\" target=\"_blank\">Read More →</a>
                    </div>
                    """
                remaining = len(category_articles) - max_articles_per_category
                if remaining > 0:
                    category_blocks += f'<div style="text-align: center; margin: 15px 0; color: #666; font-style: italic;">... and {remaining} more articles in this category</div>'
                category_blocks += "</div>"
        return category_blocks

    def filter_articles_today(self, articles):
        today = datetime.now().date()
        filtered = []
        for article in articles:
            published_at = article.get('publishedAt', '')
            try:
                # Try parsing ISO format, fallback to just date
                if 'T' in published_at:
                    date_obj = datetime.fromisoformat(published_at.replace('Z', '+00:00')).date()
                else:
                    date_obj = datetime.strptime(published_at[:10], '%Y-%m-%d').date()
                if date_obj == today:
                    filtered.append(article)
            except Exception:
                # If date can't be parsed, skip the article
                continue
        return filtered

    def fetch_news(self) -> List[Dict]:
        """Fetch news from all APIs and combine results. Use NYT and World News API only for international/international relations."""
        all_articles = []
        logging.info("Starting news fetch from multiple APIs...")
        # Fetch from NewsAPI.org
        try:
            newsapi_articles = self.fetch_from_newsapi()
            all_articles.extend(newsapi_articles)
            logging.info(f"NewsAPI.org contributed {len(newsapi_articles)} articles")
        except Exception as e:
            logging.error(f"Error fetching from NewsAPI.org: {str(e)}")
        # Fetch from NewsAPI.ai
        try:
            newsapi_ai_articles = self.fetch_from_newsapi_ai()
            all_articles.extend(newsapi_ai_articles)
            logging.info(f"NewsAPI.ai contributed {len(newsapi_ai_articles)} articles")
        except Exception as e:
            logging.error(f"Error fetching from NewsAPI.ai: {str(e)}")
        # Fetch from World News API (international only)
        try:
            worldnews_articles = self.fetch_from_worldnews()
            # Tag these as international
            for a in worldnews_articles:
                a['category_hint'] = 'International Relations'
            all_articles.extend(worldnews_articles)
            logging.info(f"World News API contributed {len(worldnews_articles)} articles")
        except Exception as e:
            logging.error(f"Error fetching from World News API: {str(e)}")
        # Fetch from NYT TimesWire (international only)
        try:
            nyt_timeswire_articles = self.fetch_from_nyt_timeswire()
            for a in nyt_timeswire_articles:
                a['category_hint'] = 'International Relations'
            all_articles.extend(nyt_timeswire_articles)
            logging.info(f"NYT TimesWire contributed {len(nyt_timeswire_articles)} articles")
        except Exception as e:
            logging.error(f"Error fetching from NYT TimesWire: {str(e)}")
        # Fetch from NYT Top Stories (international only)
        try:
            nyt_topstories_articles = self.fetch_from_nyt_topstories()
            for a in nyt_topstories_articles:
                a['category_hint'] = 'International Relations'
            all_articles.extend(nyt_topstories_articles)
            logging.info(f"NYT Top Stories contributed {len(nyt_topstories_articles)} articles")
        except Exception as e:
            logging.error(f"Error fetching from NYT Top Stories: {str(e)}")
        # Remove duplicates based on title similarity and URL
        unique_articles = self.remove_duplicates(all_articles)
        # Only keep articles from today
        unique_articles = self.filter_articles_today(unique_articles)
        # Sort by published date
        unique_articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
        logging.info(f"Total unique articles after deduplication and date filter: {len(unique_articles)}")
        return unique_articles

    def remove_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on title similarity and URL."""
        import difflib
        
        unique_articles = []
        seen_urls = set()
        seen_titles = []
        
        for article in articles:
            url = article.get('url', '')
            title = article.get('title', '').strip()
            
            # Skip if no URL or title
            if not url or not title:
                continue
                
            # Skip if exact URL already seen
            if url in seen_urls:
                continue
                
            # Check for similar titles (85% similarity threshold)
            is_duplicate = False
            for existing_title in seen_titles:
                similarity = difflib.SequenceMatcher(None, title.lower(), existing_title.lower()).ratio()
                if similarity > 0.85:  # 85% similarity threshold
                    logging.info(f"Skipping duplicate article: '{title}' (similar to: '{existing_title}')")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_articles.append(article)
                seen_urls.add(url)
                seen_titles.append(title)
                
        logging.info(f"Removed {len(articles) - len(unique_articles)} duplicate articles")
        return unique_articles

    def format_article(self, article: Dict) -> str:
        """Format a single article with improved styling and content handling."""
        title = article.get('title', 'No Title')
        description = article.get('description', '')
        url = article.get('url', '#')
        source = article.get('source', {}).get('name', 'Unknown Source')
        published_at = article.get('publishedAt', '')
        
        # Format date if available
        try:
            if 'T' in published_at:
                date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            else:
                date = datetime.fromisoformat(published_at)
            formatted_date = date.strftime('%B %d, %Y')
        except (ValueError, AttributeError):
            formatted_date = published_at
        
        # Handle truncated descriptions
        if not description or len(description) < 50:
            content = article.get('content', '')
            if content:
                # Take first 200 characters of content as fallback
                description = content[:200] + '...'
            else:
                description = "No description available. Click to read more."
        
        # Clean and format the description
        description = description.replace('\n', ' ').strip()
        
        return f"""
        <div class="article">
            <h3 class="article-title">
                <a href="{url}" target="_blank">{title}</a>
            </h3>
            <div class="article-meta">
                <span class="source">{source}</span>
                <span class="date">{formatted_date}</span>
            </div>
            <p class="article-description">{description}</p>
            <a href="{url}" class="read-more" target="_blank">Read More →</a>
        </div>
        """

    def generate_empty_digest(self) -> str:
        """Generate an empty digest when no articles are found."""
        return f"""
        <html>
        <head>
            <title>UPSC Daily Digest - {datetime.now().strftime('%Y-%m-%d')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .message {{ text-align: center; color: #666; font-size: 18px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>UPSC Daily Digest</h1>
                <p>Date: {datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            <div class="message">
                <p>No relevant articles found for today. Please check back tomorrow!</p>
            </div>
        </body>
        </html>
        """

    def generate_digest(self, articles: List[Dict]) -> str:
        """Generate the complete HTML digest."""
        if not articles:
            return self.generate_empty_digest()

        grouped = self.group_articles_by_category(articles)

        # Try to read template, fallback to basic HTML if not found
        try:
            with open('upsc_digest/templates/upsc_digest_email.html', 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            logging.warning("Template file not found, using basic HTML template")
            template = self.get_basic_template()

        # Generate category blocks
        category_blocks = self.render_digest(grouped)

        # Replace template placeholders
        digest = template.replace("{{CATEGORY_BLOCKS}}", category_blocks)

        # Create URLs for unsubscribe and preferences
        base_url = "http://localhost:8000"
        unsubscribe_url = f"{base_url}/unsubscribe"
        preferences_url = f"{base_url}/preferences"

        digest = digest.replace("{{UNSUBSCRIBE_LINK}}", unsubscribe_url)
        digest = digest.replace("{{PREFERENCES_LINK}}", preferences_url)
        
        logging.info(f"Generated digest with {len([a for a in articles if a.get('category_hint') != 'International Relations'])} articles across {len([c for c in grouped.values() if c])} categories")

        return digest

    def get_basic_template(self) -> str:
        """Basic HTML template fallback."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>UPSC Daily Digest</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background-color: #f8f9fa; 
                    line-height: 1.6;
                }}
                .container {{ 
                    max-width: 800px; 
                    margin: 0 auto; 
                    background-color: white; 
                    padding: 30px; 
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{ 
                    text-align: center; 
                    margin-bottom: 40px; 
                    border-bottom: 3px solid #2c3e50; 
                    padding-bottom: 20px; 
                }}
                .header h1 {{
                    color: #2c3e50;
                    margin: 0;
                    font-size: 2.5em;
                }}
                .header p {{
                    color: #666;
                    margin: 10px 0 0 0;
                    font-size: 1.1em;
                }}
                .section-title {{ 
                    font-size: 1.8em; 
                    font-weight: bold; 
                    color: #2c3e50; 
                    margin: 40px 0 25px 0; 
                    border-left: 5px solid #3498db; 
                    padding-left: 15px; 
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                }}
                .category-block {{
                    margin-bottom: 40px;
                }}
                .article-block {{ 
                    margin-bottom: 30px; 
                    padding: 20px; 
                    border: 1px solid #e9ecef; 
                    border-radius: 8px; 
                    background-color: #ffffff;
                    transition: box-shadow 0.3s ease;
                }}
                .article-block:hover {{
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }}
                .article-title a {{ 
                    color: #2c3e50; 
                    text-decoration: none; 
                    font-weight: bold; 
                    font-size: 1.2em; 
                    display: block;
                    margin-bottom: 10px;
                }}
                .article-title a:hover {{ 
                    color: #3498db; 
                }}
                .article-meta {{ 
                    color: #666; 
                    font-size: 0.9em; 
                    margin: 10px 0; 
                    display: flex;
                    gap: 15px;
                }}
                .article-meta .source {{
                    font-weight: bold;
                    color: #3498db;
                }}
                .article-description {{ 
                    margin: 15px 0; 
                    line-height: 1.7; 
                    color: #444;
                }}
                .article-link {{ 
                    color: #3498db; 
                    text-decoration: none; 
                    font-weight: bold; 
                    display: inline-block;
                    margin-top: 10px;
                    padding: 8px 16px;
                    border: 2px solid #3498db;
                    border-radius: 5px;
                    transition: all 0.3s ease;
                }}
                .article-link:hover {{ 
                    background-color: #3498db;
                    color: white;
                }}
                .footer {{
                    text-align: center; 
                    margin-top: 50px; 
                    padding-top: 30px;
                    border-top: 2px solid #e9ecef;
                    font-size: 0.9em; 
                    color: #666;
                }}
                .footer p {{
                    margin: 10px 0;
                }}
                .footer a {{
                    color: #3498db;
                    text-decoration: none;
                    font-weight: bold;
                    padding: 5px 10px;
                    margin: 0 5px;
                    border-radius: 3px;
                    transition: background-color 0.3s ease;
                }}
                .footer a:hover {{
                    background-color: #f8f9fa;
                }}
                .disclaimer {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    border-left: 4px solid #3498db;
                    margin: 20px 0;
                    font-size: 0.9em;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📚 UPSC Daily Digest</h1>
                    <p>{datetime.now().strftime('%B %d, %Y')}</p>
                </div>
                
                <div class="disclaimer">
                    <p><strong>📋 About This Digest:</strong> This digest is automatically generated and contains news articles relevant to UPSC preparation. Articles are categorized by topic to help you focus on specific areas of study.</p>
                </div>
                
                {{{{CATEGORY_BLOCKS}}}}
                
                <div class="footer">
                    <p><strong>📬 Manage Your Subscription</strong></p>
                    <p>
                        <a href="{{{{UNSUBSCRIBE_LINK}}}}">✉️ Unsubscribe</a> | 
                        <a href="{{{{PREFERENCES_LINK}}}}">⚙️ Manage Preferences</a>
                    </p>
                    <p>© 2025 UPSC Daily Digest - Powered by AI</p>
                </div>
            </div>
        </body>
        </html>
        """

    def save_digest(self, digest):
        """Save the digest to an HTML file."""
        try:
            filename = f"daily_upsc_digest_{datetime.now().strftime('%Y%m%d')}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(digest)
            logging.info(f"Digest saved to {filename}")
            return True
        except Exception as e:
            logging.error(f"Error saving digest: {str(e)}")
            return False

    def send_email(self, digest):
        """Send the digest via email."""
        try:
            sender_email = os.getenv('SENDER_EMAIL')
            sender_password = os.getenv('SENDER_PASSWORD')
            recipient_email = os.getenv('RECIPIENT_EMAIL')
            
            if not all([sender_email, sender_password, recipient_email]):
                logging.error("Email configuration is incomplete")
                return False

            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"UPSC Daily Digest - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Attach HTML content
            msg.attach(MIMEText(digest, 'html'))
            
            # Send email
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
                
            logging.info("Email sent successfully!")
            return True
            
        except Exception as e:
            logging.error(f"Error sending email: {str(e)}")
            return False

def main():
    """Main function to run the UPSC digest process."""
    try:
        digest = UPSCDigest()
        
        # Fetch news
        articles = digest.fetch_news()
        if not articles:
            logging.warning("No articles found, generating empty digest")
            html_digest = digest.generate_empty_digest()
        else:
            # Generate digest
            html_digest = digest.generate_digest(articles)
        
        if not html_digest:
            logging.error("Failed to generate digest")
            return
        
        # Save digest
        digest.save_digest(html_digest)
        
        # Send email
        digest.send_email(html_digest)
        
    except Exception as e:
        logging.error(f"Unexpected error in main: {str(e)}")

if __name__ == "__main__":
    main()
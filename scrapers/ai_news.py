import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class AINewsScraper:
    def __init__(self):
        self.base_url = "https://www.artificialintelligence-news.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def fetch_articles(self, category: str = None) -> List[Dict[str, Any]]:
        """Fetch articles from AI News."""
        try:
            # Construct URL based on category
            url = f"{self.base_url}/category/{category}" if category else self.base_url
            
            # Fetch page content
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find article elements
            articles = []
            article_elements = soup.find_all('article', class_='post')
            
            for element in article_elements:
                try:
                    # Extract article data
                    title_element = element.find('h2', class_='entry-title')
                    if not title_element:
                        continue
                        
                    title = title_element.get_text(strip=True)
                    link = title_element.find('a')['href']
                    
                    # Get article content
                    article_data = await self.fetch_article_content(link)
                    if article_data:
                        articles.append(article_data)
                        
                except Exception as e:
                    logger.error(f"Error processing article: {str(e)}")
                    continue
            
            return articles
        except Exception as e:
            logger.error(f"Error fetching articles: {str(e)}")
            return []

    async def fetch_article_content(self, url: str) -> Dict[str, Any]:
        """Fetch and parse individual article content."""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract article data
            title = soup.find('h1', class_='entry-title').get_text(strip=True)
            
            # Get article description
            description_element = soup.find('div', class_='entry-content')
            if description_element:
                # Get first paragraph as description
                first_para = description_element.find('p')
                description = first_para.get_text(strip=True) if first_para else ""
            else:
                description = ""
            
            # Get publication date
            date_element = soup.find('time', class_='entry-date')
            published_at = datetime.strptime(date_element['datetime'], "%Y-%m-%dT%H:%M:%S%z") if date_element else datetime.now()
            
            # Get article category
            category_element = soup.find('a', rel='category tag')
            category = category_element.get_text(strip=True) if category_element else "Artificial Intelligence"
            
            return {
                "title": title,
                "description": description,
                "url": url,
                "source": "Artificial Intelligence News",
                "category": category,
                "published_at": published_at
            }
        except Exception as e:
            logger.error(f"Error fetching article content: {str(e)}")
            return None

    async def get_categories(self) -> List[str]:
        """Get available categories from AI News."""
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find category links
            category_elements = soup.find_all('a', href=re.compile(r'/category/'))
            
            # Extract category names
            categories = []
            for element in category_elements:
                category = element.get_text(strip=True)
                if category and category not in categories:
                    categories.append(category)
            
            return categories
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return []
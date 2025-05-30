import requests
import xml.etree.ElementTree as ET
import datetime
import re
import json

# Updated RSS Feed Sources (removed The Verge)
RSS_SOURCES = [
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/"
    },
    {
        "name": "MIT Technology Review - AI",
        "url": "https://www.technologyreview.com/feed/"
    },
    {
        "name": "AI News - RSS.app",
        "url": "https://rss.app/feeds/SprrskTWAoLpsK01.xml"
    },
    {
        "name": "Cybersecurity - Hacker News",
        "url": "https://feeds.feedburner.com/TheHackersNews"
    }
]

def clean_html(raw_html):
    clean_re = re.compile('<.*?>')
    return re.sub(clean_re, '', raw_html)

def trim_description(text):
    words = text.split()
    if len(words) <= 30:
        return text
    desc = " ".join(words[:30])
    if not desc.endswith(('.', '!', '?')):
        desc += '...'
    return desc

def fetch_rss_articles(source, seen_titles):
    print(f"\n[INFO] Fetching RSS for {source['name']}...")
    collected = []
    try:
        response = requests.get(source['url'])
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = root.findall('.//item')

        today = datetime.datetime.now().date()
        print(f"[NEWS] Articles for {source['name']} - {today}:")

        count = 0
        for item in items:
            title = item.findtext('title', 'No Title').strip()
            link = item.findtext('link', 'No Link').strip()
            raw_desc = item.findtext('description', 'No Description')
            description = clean_html(raw_desc).strip()
            description = trim_description(description)

            if title in seen_titles:
                continue

            pub_date_text = item.findtext('pubDate')
            if pub_date_text:
                try:
                    pub_date = datetime.datetime.strptime(pub_date_text[:16], '%a, %d %b %Y').date()
                    if pub_date != today:
                        continue
                except:
                    pass  # skip date filtering if format is unknown

            print(f"\n[TITLE] {title}\n[DESC] {description}\n[LINK] {link}")
            collected.append({"title": title, "description": description, "link": link})
            seen_titles.add(title)
            count += 1
            if count >= 5:
                break

        if count == 0:
            print("[INFO] No recent articles found for today.")

    except Exception as e:
        print(f"[ERROR] Failed to fetch RSS for {source['name']} - {str(e)}")
    return collected

if __name__ == "__main__":
    all_articles = []
    seen_titles = set()

    for source in RSS_SOURCES:
        articles = fetch_rss_articles(source, seen_titles)
        all_articles.extend(articles)

    # Save to JSON
    with open("news_digest.json", "w", encoding='utf-8') as f:
        json.dump(all_articles, f, indent=4, ensure_ascii=False)

    print(f"\n[SUCCESS] All feeds processed and saved to 'news_digest.json'. Found {len(all_articles)} articles.")

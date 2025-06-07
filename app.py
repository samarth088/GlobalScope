from flask import Flask, render_template
from apscheduler.schedulers.background import BackgroundScheduler
import feedparser
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# SQLite Database Setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source TEXT,
                  title TEXT UNIQUE,
                  link TEXT,
                  pub_date TEXT)''')
    conn.commit()
    conn.close()

# 15+ News Sources with RSS Feeds
NEWS_SOURCES = {
    'The Hindu': 'https://www.thehindu.com/news/national/feeder/default.rss',
    'BBC': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'The Tribune': 'https://www.tribuneindia.com/rss/feed.aspx?cat=2',
    'CNN': 'http://rss.cnn.com/rss/cnn_world.rss',
    'WION': 'https://www.wionews.com/rss/world.xml',
    'Reuters': 'http://feeds.reuters.com/reuters/topNews',
    'NDTV': 'https://feeds.feedburner.com/ndtvnews-latest',
    'Indian Express': 'https://indianexpress.com/section/india/feed/',
    'Times of India': 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
    'The Guardian': 'https://www.theguardian.com/world/rss',
    'New York Times': 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
    'Washington Post': 'http://feeds.washingtonpost.com/rss/world',
    'Al Jazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
    'DW News': 'https://rss.dw.com/xml/rss_en_top',
    'RT News': 'https://www.rt.com/rss/news/',
    'News18': 'https://www.news18.com/rss/india.xml',
    'India Today': 'https://www.indiatoday.in/rss/home'
}

# Fetch and Store Articles
def fetch_articles():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    for source, rss_url in NEWS_SOURCES.items():
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                title = entry.get('title', 'No Title')
                link = entry.get('link', '#')
                pub_date = entry.get('published', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                # Insert article into database (ignore duplicates)
                try:
                    c.execute("INSERT INTO articles (source, title, link, pub_date) VALUES (?, ?, ?, ?)",
                              (source, title, link, pub_date))
                    conn.commit()
                    print(f"Added article from {source}: {title}")
                except sqlite3.IntegrityError:
                    # Skip if article already exists (unique title constraint)
                    continue
        except Exception as e:
            print(f"Error fetching from {source}: {e}")
    
    conn.close()

# Background Scheduler to Fetch Articles Every 5 Minutes
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_articles, 'interval', minutes=5)
scheduler.start()

# Initialize Database and Fetch Articles on Startup
init_db()
fetch_articles()

# Flask Routes
@app.route('/')
def home():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Get latest 50 articles, ordered by pub_date
    c.execute("SELECT source, title, link, pub_date FROM articles ORDER BY pub_date DESC LIMIT 50")
    articles = c.fetchall()
    conn.close()
    return render_template('index.html', articles=articles)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)



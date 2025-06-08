from flask import Flask, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler
import feedparser
import sqlite3
from datetime import datetime
import logging
import os

app = Flask(__name__)

# Logging Setup
log_dir = 'logs'
log_file = os.path.join(log_dir, 'app.log')

try:
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
except Exception as e:
    print(f"Could not create log directory: {e}")

handlers = [logging.StreamHandler()]
try:
    handlers.append(logging.FileHandler(log_file))
except Exception as e:
    print(f"Could not set up file logging: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

# SQLite Database Setup (In-Memory)
def init_db():
    logger.info("Initializing in-memory database")
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    c.execute('''CREATE TABLE articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source TEXT,
                  title TEXT UNIQUE,
                  link TEXT,
                  pub_date TEXT)''')
    conn.commit()
    logger.info("Database initialized successfully")
    return conn

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
    'India Today': 'https://www.indiatoday.in/rss/home',
    'Hindustan Times': 'https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml',
    'Sky News': 'https://feeds.skynews.com/feeds/rss/world.xml',
    'Bloomberg': 'https://www.bloomberg.com/feed.xml'
}

# Initialize database globally
try:
    db_conn = init_db()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    raise

# Fetch and Store Articles
def fetch_articles():
    logger.info("Starting article fetch process")
    c = db_conn.cursor()
    
    for source, rss_url in NEWS_SOURCES.items():
        try:
            logger.info(f"Fetching articles from {source} at {rss_url}")
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                logger.warning(f"No entries found for {source}")
                continue
                
            logger.info(f"Found {len(feed.entries)} entries for {source}")
            for entry in feed.entries:
                title = entry.get('title', 'No Title')
                link = entry.get('link', '#')
                pub_date = entry.get('published', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                try:
                    c.execute("INSERT INTO articles (source, title, link, pub_date) VALUES (?, ?, ?, ?)",
                              (source, title, link, pub_date))
                    db_conn.commit()
                    logger.info(f"Added article from {source}: {title}")
                except sqlite3.IntegrityError:
                    logger.debug(f"Article already exists: {title}")
                    continue
                except Exception as e:
                    logger.error(f"Error inserting article from {source}: {e}")
                    db_conn.rollback()
            
        except Exception as e:
            logger.error(f"Error fetching from {source}: {e}")
    
    c.close()
    logger.info("Article fetch process completed")

# Background Scheduler to Fetch Articles Every 5 Minutes
logger.info("Starting APScheduler")
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_articles, 'interval', minutes=5)
scheduler.start()
logger.info("APScheduler started successfully")

# Fetch Articles on Startup
fetch_articles()

# Flask Routes
@app.route('/')
def home():
    logger.info("Handling request for homepage")
    c = db_conn.cursor()
    search_query = request.args.get('search', '')
    source_filter = request.args.get('source', '')
    
    query = "SELECT source, title, link, pub_date FROM articles WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND title LIKE ?"
        params.append(f"%{search_query}%")
    if source_filter:
        query += " AND source = ?"
        params.append(source_filter)
    
    query += " ORDER BY pub_date DESC LIMIT 50"
    c.execute(query, params)
    articles = c.fetchall()
    c.close()
    logger.info(f"Returning {len(articles)} articles")
    
    sources = sorted(NEWS_SOURCES.keys())
    return render_template('index.html', articles=articles, sources=sources, search_query=search_query, source_filter=source_filter)

# Manual Fetch Endpoint
@app.route('/fetch-articles')
def manual_fetch():
    logger.info("Manual fetch triggered")
    fetch_articles()
    return "Articles fetch task started!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# Close database connection on app shutdown
@app.teardown_appcontext
def close_db(error):
    if db_conn is not None:
        db_conn.close()

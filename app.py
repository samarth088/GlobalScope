from flask import Flask, render_template, request
from celery import Celery
import feedparser
import psycopg2
from datetime import datetime, timedelta
import logging
import os
from urllib.parse import urlparse
from time import sleep

app = Flask(__name__)

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Celery Configuration (Using Redis as Broker)
app.config['CELERY_BROKER_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
app.config['CELERY_RESULT_BACKEND'] = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# PostgreSQL Database Setup
def init_db():
    db_url = os.environ.get('DATABASE_URL')  # Render PostgreSQL URL
    if not db_url:
        raise ValueError("DATABASE_URL not set in environment variables")
    
    # Parse DATABASE_URL
    parsed_url = urlparse(db_url)
    conn = psycopg2.connect(
        database=parsed_url.path[1:],
        user=parsed_url.username,
        password=parsed_url.password,
        host=parsed_url.hostname,
        port=parsed_url.port
    )
    
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS articles
                 (id SERIAL PRIMARY KEY,
                  source TEXT,
                  title TEXT UNIQUE,
                  link TEXT,
                  pub_date TIMESTAMP)''')
    conn.commit()
    return conn

# 15+ News Sources with RSS Feeds (Extended List)
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

# Celery Task to Fetch Articles
@celery.task
def fetch_articles():
    c = db_conn.cursor()
    
    for source, rss_url in NEWS_SOURCES.items():
        try:
            logger.info(f"Fetching articles from {source}")
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                logger.warning(f"No entries found for {source}")
                continue
                
            for entry in feed.entries:
                title = entry.get('title', 'No Title')
                link = entry.get('link', '#')
                pub_date_str = entry.get('published', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                try:
                    pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
                except ValueError:
                    pub_date = datetime.now()
                
                try:
                    c.execute("INSERT INTO articles (source, title, link, pub_date) VALUES (%s, %s, %s, %s)",
                              (source, title, link, pub_date))
                    db_conn.commit()
                    logger.info(f"Added article from {source}: {title}")
                except psycopg2.IntegrityError:
                    continue
                except Exception as e:
                    logger.error(f"Error inserting article from {source}: {e}")
                    db_conn.rollback()
            
            # Rate limiting: Sleep to avoid overloading RSS servers
            sleep(1)
        except Exception as e:
            logger.error(f"Error fetching from {source}: {e}")
    
    c.close()

# Schedule Fetch Task Every 5 Minutes
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(300.0, fetch_articles.s(), name='fetch-articles-every-5-minutes')

# Fetch Articles on Startup
fetch_articles.delay()

# Flask Routes
@app.route('/')
def home():
    c = db_conn.cursor()
    search_query = request.args.get('search', '')
    source_filter = request.args.get('source', '')
    
    query = "SELECT source, title, link, pub_date FROM articles WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND title ILIKE %s"
        params.append(f"%{search_query}%")
    if source_filter:
        query += " AND source = %s"
        params.append(source_filter)
    
    query += " ORDER BY pub_date DESC LIMIT 50"
    c.execute(query, params)
    articles = c.fetchall()
    c.close()
    
    sources = sorted(NEWS_SOURCES.keys())
    return render_template('index.html', articles=articles, sources=sources, search_query=search_query, source_filter=source_filter)

# Manual Fetch Endpoint
@app.route('/fetch-articles')
def manual_fetch():
    fetch_articles.delay()
    return "Articles fetch task started!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# Close database connection on app shutdown
@app.teardown_appcontext
def close_db(error):
    if db_conn is not None:
        db_conn.close()

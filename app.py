from flask import Flask, render_template  
import requests  
from bs4 import BeautifulSoup  
from flask_caching import Cache  
  
app = Flask(__name__)  
  
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 300})  
  
NEWS_SOURCES = {  
    'BBC': 'https://www.bbc.com/news',  
    'CNN': 'https://edition.cnn.com/world',  
    'The Hindu': 'https://www.thehindu.com/news/',  
}  
  
def fetch_news_from_source(url):  
    try:  
        r = requests.get(url, timeout=5)  
        soup = BeautifulSoup(r.text, 'html.parser')  
        headlines = []  
  
        if 'bbc' in url:  
            for h3 in soup.find_all('h3', class_='gs-c-promo-heading__title'):  
                text = h3.get_text(strip=True)  
                if text and text not in headlines:  
                    headlines.append(text)  
  
        elif 'cnn' in url:  
            for h3 in soup.find_all('h3', class_='cd__headline'):  
                text = h3.get_text(strip=True)  
                if text and text not in headlines:  
                    headlines.append(text)  
  
        elif 'thehindu' in url:  
            for div in soup.find_all('div', class_='story-card'):  
                a = div.find('a')  
                if a:  
                    text = a.get_text(strip=True)  
                    if text and text not in headlines:  
                        headlines.append(text)  
  
        return headlines[:10]  
    except Exception as e:  
        print(f"Error fetching news from {url}: {e}")  
        return []  
  
@cache.cached(timeout=300)  
def get_all_news():  
    news = {}  
    for source, url in NEWS_SOURCES.items():  
        news[source] = fetch_news_from_source(url)  
    return news  
  
@app.route('/')  
def home():  
    news = get_all_news()  
    return render_template('index.html', news=news)  
  
if __name__ == '__main__':  
    app.run(host='0.0.0.0', port=5000, debug=True)

from flask import Flask, render_template import requests from bs4 import BeautifulSoup from flask_caching import Cache

app = Flask(name) cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 600})

NEWS_SOURCES = { 'BBC': 'https://www.bbc.com/news', 'CNN': 'https://edition.cnn.com/world', 'The Hindu': 'https://www.thehindu.com/news/', 'The Times of India': 'https://timesofindia.indiatimes.com/briefs', 'Reuters': 'https://www.reuters.com/news/world', 'NDTV': 'https://www.ndtv.com/latest', 'Indian Express': 'https://indianexpress.com/section/india/', 'The Tribune': 'https://www.tribuneindia.com/news/nation/', 'WION': 'https://www.wionews.com/world', 'RT News': 'https://www.rt.com/news/', 'The Guardian': 'https://www.theguardian.com/world', 'New York Times': 'https://www.nytimes.com/section/world', 'Washington Post': 'https://www.washingtonpost.com/world/', 'Al Jazeera': 'https://www.aljazeera.com/news/', 'DW News': 'https://www.dw.com/en/top-stories/s-9097' }

def fetch_news_from_source(name, url): try: r = requests.get(url, timeout=10) soup = BeautifulSoup(r.text, 'html.parser') headlines = []

if 'bbc' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('h3.gs-c-promo-heading__title')]

    elif 'cnn' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('h3.cd__headline')]

    elif 'thehindu' in url:
        for div in soup.find_all('div', class_='story-card-news'):  
            text = div.get_text(strip=True)
            if text:
                headlines.append(text)

    elif 'timesofindia' in url:
        headlines = [li.get_text(strip=True) for li in soup.select('li.brief_box')]

    elif 'reuters' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('a.story-title') or h.select('h3.story-title')]

    elif 'ndtv' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('h2.newsHdng')]

    elif 'indianexpress' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('h2.title')]

    elif 'tribuneindia' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('div.news-title')]

    elif 'wionews' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('h3.title')]

    elif 'rt.com' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('div.card__heading')]

    elif 'guardian' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('a.js-headline-text')]

    elif 'nytimes' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('h2.css-1j9dxys')]

    elif 'washingtonpost' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('div.card')]

    elif 'aljazeera' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('h3.gc__title')]

    elif 'dw.com' in url:
        headlines = [h.get_text(strip=True) for h in soup.select('a.teaser-title')]

    return list(filter(None, headlines))[:10]
except Exception as e:
    print(f"Error fetching from {name}: {e}")
    return []

@cache.cached() def get_all_news(): news = {} for name, url in NEWS_SOURCES.items(): news[name] = fetch_news_from_source(name, url) return news

@app.route('/') def home(): news = get_all_news() return render_template('index.html', news=news)

if name == 'main': app.run(host='0.0.0.0', port=5000, debug=True)



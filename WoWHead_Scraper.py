import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime

# ---------------------------
# DATE NORMALIZATION UTILITY
# ---------------------------
def normalize_date(date_str):
    now = datetime.now()
    try:
        date_str = date_str.lower().replace("posted", "").strip()

        if "min ago" in date_str or "hr" in date_str or "day" in date_str:
            time_ago = date_str.replace("ago", "").strip()
            tokens = time_ago.split()
            delta = {}
            i = 0
            while i < len(tokens):
                if tokens[i] in ["hr", "hrs", "hour", "hours"]:
                    delta["hours"] = int(tokens[i - 1])
                elif tokens[i] in ["min", "mins", "minute", "minutes"]:
                    delta["minutes"] = int(tokens[i - 1])
                elif tokens[i] in ["day", "days"]:
                    delta["days"] = int(tokens[i - 1])
                i += 1
            offset = pd.Timedelta(**delta)
            return (now - offset).strftime("%Y-%m-%d")
        else:
            dt = pd.to_datetime(date_str, errors='coerce')
            if pd.isna(dt):
                return None
            return dt.strftime("%Y-%m-%d")
    except Exception:
        return None

# ---------------------------
# SETUP SELENIUM
# ---------------------------
options = Options()
options.add_argument("--headless=new")
service = Service()
driver = webdriver.Chrome(service=service, options=options)

# ---------------------------
# GET LINKS + DATES
# ---------------------------

def get_article_links_from_page(page_num):
    url = f"https://www.wowhead.com/news?page={page_num}"
    print(f"🔄 Scraping page {page_num}: {url}")
    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    anchors = soup.find_all("a", class_="news-card-simple-thumbnail")

    links = []
    for a in anchors:
        href = a.get("href", "")
        if href.startswith("/news/"):
            full_url = "https://www.wowhead.com" + href

            # Attempt to find corresponding date
            article_card = a.find_parent("a", class_="news-card-simple")
            posted_span = article_card.find("span", class_="news-card-simple-text-byline-posted") if article_card else None
            raw_date = posted_span.get("title") if posted_span else None

            try:
                norm_date = datetime.strptime(raw_date, "%Y/%m/%d at %I:%M %p") if raw_date else None
            except:
                norm_date = None

            links.append({
                "url": full_url,
                "raw_date": raw_date,
                "normalized_date": norm_date.strftime("%Y-%m-%d %H:%M") if norm_date else None
            })

    if not links:
        print("⚠️ No news cards found on page", page_num)
    return links

# ---------------------------
# SCRAPE CONTENT
# ---------------------------
def extract_article_text(article_url):
    print(f"📰 Extracting: {article_url}")
    driver.get(article_url)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "news-post-content"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        content_div = soup.find("div", class_="news-post-content")
        return content_div.get_text(separator="\n").strip()
    except:
        print(f"❌ Failed to extract: {article_url}")
        return ""

# ---------------------------
# MAIN LOGIC
# ---------------------------
all_articles = []
for page in range(1, 10):  # Adjust range as needed
    articles = get_article_links_from_page(page)
    for article in articles:
        content = extract_article_text(article["url"])
        if content:
            all_articles.append({
                "url": article["url"],
                "date": article["normalized_date"],
                "content": content
            })

# ---------------------------
# SAVE OUTPUT
# ---------------------------
df = pd.DataFrame(all_articles)
df.to_excel("wowhead_articles_with_dates.xlsx", index=False)
print(f"\n✅ Saved {len(df)} articles to wowhead_articles_with_dates.xlsx")

driver.quit()

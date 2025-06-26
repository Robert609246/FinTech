from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import json
import gzip
import io

# -----------------------------
# 🔧 SETTINGS
# -----------------------------
item_urls = [
    "https://wowpricehub.com/eu/burning-legion/item/Profaned%20Tinderbox-221758",
    "https://wowpricehub.com/eu/burning-legion/item/Bismuth-210930",
    "https://wowpricehub.com/eu/burning-legion/item/Leystone%20Ore-123918",
    "https://wowpricehub.com/eu/burning-legion/item/Shal'dorei%20Silk-124437",
    "https://wowpricehub.com/eu/burning-legion/item/Lightless%20Silk-173204",
    "https://wowpricehub.com/eu/burning-legion/item/Vibrant%20Wildercloth%20Bolt-193931",
    "https://wowpricehub.com/eu/burning-legion/item/Resilient%20Leather-193211",
    "https://wowpricehub.com/eu/burning-legion/item/Glowing%20Titan%20Orb-201406",
    "https://wowpricehub.com/eu/burning-legion/item/Ironclaw%20Ore-210938",
    "https://wowpricehub.com/eu/burning-legion/item/Orbinid-210804"
]

all_data = []

# -----------------------------
# 🚀 Scraper loop
# -----------------------------
for url in item_urls:
    print(f"\n🔍 Processing: {url}")
    try:
        # Start a new browser session for every item
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        driver = webdriver.Chrome(options=options)

        driver.get(url)
        wait = WebDriverWait(driver, 15)

        # Click the "Monthly" button
        monthly_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[text()="Monthly"]')))
        driver.execute_script("arguments[0].scrollIntoView(true);", monthly_button)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", monthly_button)

        time.sleep(5)

        # Intercept the XHR request
        target_request = None
        for request in driver.requests:
            if request.response and "monthly" in request.url and "item" in request.url:
                target_request = request
                break

        if not target_request:
            print("❌ No data found for:", url)
            driver.quit()
            continue

        print(f"📡 Intercepted request: {target_request.url}")

        # Decompress response
        compressed = io.BytesIO(target_request.response.body)
        with gzip.GzipFile(fileobj=compressed) as f:
            raw_data = f.read().decode('utf-8')

        json_data = json.loads(raw_data)

        # Parse item name and auction data
        item_name = json_data["item"]["itemName"]
        df = pd.DataFrame(json_data["auctions"])
        df["timestamp"] = pd.to_datetime(df["dateTime"])
        df.rename(columns={"price": "market_value", "minBuyout": "min_buyout"}, inplace=True)
        df.drop(columns=["dateTime"], inplace=True)
        df["item_name"] = item_name

        all_data.append(df)
        print(f"✅ {item_name} scraped with {len(df)} entries.")

        driver.quit()  # ✅ Fully kill browser for next item

    except Exception as e:
        print(f"⚠️ Error scraping {url}:", e)
        driver.quit()

# -----------------------------
# 💾 Save aggregated data
# -----------------------------
if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df.to_csv("aggregated_wow_ah_monthly.csv", index=False)
    print("\n✅ Saved aggregated data to 'aggregated_wow_ah_monthly.csv'")
    print(combined_df.head())
else:
    print("\n❌ No data collected.")

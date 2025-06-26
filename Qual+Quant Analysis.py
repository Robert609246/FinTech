import pandas as pd
import json
from openai import OpenAI
from tqdm import tqdm

# === Setup ===
client = OpenAI(api_key="REDACTED")

input_path = "wowhead_articles_with_dates.xlsx"
df = pd.read_excel(input_path)

# Define portfolio items
portfolio_items = [
    "Profaned Tinderbox",
    "Bismuth",
    "Leystone Ore",
    "Shal'dorei Silk",
    "Lightless Silk",
    "Vibrant Wildercloth Bolt",
    "Resilient Leather",
    "Glowing Titan Orb",
    "Ironclaw Ore",
    "Orbinid"
]

# === Prompt builder ===
def build_item_impact_prompt(article_text, date, url, portfolio_items):
    item_list = "\n".join(f"- {item}" for item in portfolio_items)
    return f"""
You are a seasoned World of Warcraft economy analyst. You only care about RETAIL WoW and must ignore Classic entirely.

Below is a list of specific items currently being tracked in our investment portfolio:
{item_list}

Your task is to read the following news article and determine if ANY of the portfolio items above may be economically affected in terms of supply, demand, or price. You should also take a more holistic interpretation of the news, reasoning deeply about things such as players returning and how that might affect supply and demand.

For each relevant portfolio item, return:
- "affected_item": the item affected
- "interpretation": a short explanation of the economic impact (e.g., higher demand due to crafting)
- "impact_score": a number from -5 (very negative price effect) to +5 (very positive price effect)

If an item has no direct implication in the article, do NOT include it.

Article date: {date}
URL: {url}

Article:
\"\"\"
{article_text}
\"\"\"

Return your answer as a JSON array of objects. Format:
[
  {{ "affected_item": "Leystone Ore", "interpretation": "...", "impact_score": 2 }},
  {{ "affected_item": "Glowing Titan Orb", "interpretation": "...", "impact_score": 3 }}
]
"""

# === GPT call with fallback JSON parse ===
def get_item_impacts(prompt, model="gpt-4o-mini"):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print("⚠️ JSON decode failed, using fallback...")
            cleaned = content.strip().strip("```json").strip("```").strip()
            return json.loads(cleaned)
    except Exception as e:
        print(f"⚠️ API error: {e}")
        return []

# === Main loop ===
rows = []
for _, row in tqdm(df.iterrows(), total=len(df)):
    article = row["content"]
    date = row["date"]
    url = row["url"]
    prompt = build_item_impact_prompt(article, date, url, portfolio_items)
    impacts = get_item_impacts(prompt)

    for item in impacts:
        rows.append({
            "date": date,
            "url": url,
            "affected_item": item.get("affected_item"),
            "interpretation": item.get("interpretation"),
            "impact_score": item.get("impact_score")
        })

# === Save output ===
out_df = pd.DataFrame(rows)
out_df.to_excel("wowhead_interpreted_item_impacts.xlsx", index=False)
print("✅ Saved to wowhead_interpreted_item_impacts.xlsx")

# WoW Auction House Trading Bot – Insight-Augmented Simulation

## Overview

This project simulates automated trading on the World of Warcraft Auction House (AH). It integrates:

**Quantitative strategies**: based on moving averages and market price deviations.
**Qualitative insights**: derived from WoWHead news articles using GPT.
**Backtesting**: on scraped auction house data.
**Comparison**: of trading performance with and without qualitative news-based insights.

---

## File Descriptions

### Trading & Simulation
| File | Description |
|------|-------------|
| `Simulator.py` | Baseline trading bot using quantitative logic (price deviations, MA7, reset times). |
| `Simulator w Insights.py` | Enhanced trader using news-based `impact_score`s for each item to bias trading. |
| `Simulator_V2 (Half-Half).py` | Simplified MA strategy using historical vs. current split (no full sim logic). |
| `simulator_comparison.py` | Batch runs both models, compares final performance across N simulations. |

### Scraping & News Analysis
| File | Description |
|------|-------------|
| `WoWHead_Scraper.py` | Scrapes news articles from WoWHead (URL, date, content). |
| `Qual+Quant Analysis.py` | Sends articles to ChatGPT to extract affected items + impact scores. |
| `AH_Scraper.py` | Collects raw auction house data. Outputs `aggregated_wow_ah_monthly.csv` used by all simulators. ✅ Part of the pipeline. |

---

## Python Libraries Used

### Web Automation & Scraping
- `selenium`, `selenium-wire`
- `BeautifulSoup`
- `time`, `datetime`

### Data Analysis & Processing
- `pandas`
- `numpy`
- `collections.defaultdict`
- `json`, `gzip`, `io`

### Visualization
- `matplotlib.pyplot`

### AI Integration
- `openai` (ChatGPT API)
- `tqdm` (progress bars)

### I/O and OS Handling
- `os`, `xlsxwriter`

---

## Python Environment

### Version: **Python 3.10**

**Why?**  
- Fully compatible with all used libraries (Selenium, OpenAI, Pandas).
- Improved error handling and syntax diagnostics.
- Long-Term Support (LTS) stability.

---

## How the Trader Works

### Setup
- Starts with **100,000 gold**
- Tracks item quantities + cost basis using a defaultdict inventory

### Buy Logic
- When market value is **>10% below** 7-period moving average
- During **early reset hours** (3–6 AM on reset days)
- Budget: **10%** of current gold

### Sell Logic
- When market value is **>10% above** MA7
- During **post-reset hours** (Tuesday/Wednesday 15–17h)
- Can only sell **up to 1%** of total market quantity (liquidity constraint)

### Insight-Based Enhancements
- `Simulator w Insights.py` includes impact scores (from GPT via `Qual+Quant Analysis.py`)
- These influence **buying preference** toward positively scored items

---

## Performance Evaluation

Run `simulator_comparison.py` to:
- Simulate **30 runs per model**
- Add **market quantity noise** for realism
- Compare means and standard deviations of:
  - Final Gold
  - Portfolio Value
  - Total Value

**Output Files:**
- `simulator_comparison_results.csv`
- `simulator_model_comparison.png`

---

## Output Summary

| File | Purpose |
|------|---------|
| `wowhead_articles_with_dates.xlsx` | Raw article data |
| `wowhead_interpreted_item_impacts.xlsx` | Extracted affected items + impact scores |
| `aggregated_wow_ah_monthly.csv` | Auction house data from `AH_Scraper.py` |
| `reinvesting_trade_log.xlsx` | Per-trade log with timestamps, quantities, and reasons |
| `plots/` | Holdings over time (PNG files) |
| `simulator_model_comparison.png` | Visual comparison of final metrics |

---

## Pipeline Overview

```
flowchart TD
    A[AH_Scraper.py] --> B[aggregated_wow_ah_monthly.csv]
    C[WoWHead_Scraper.py] --> D[wowhead_articles_with_dates.xlsx]
    D --> E[Qual+Quant Analysis.py]
    E --> F[wowhead_interpreted_item_impacts.xlsx]
    B --> G[Simulator.py]
    B --> H[Simulator w Insights.py]
    F --> H
    G --> I[simulator_comparison.py]
    H --> I
    I --> J[Results: CSV + Plots]
```

---

## Suggested Improvements

- Include **stop-loss logic** for loss control
- Add **impact score decay** over time
- Implement **order book modeling** for true market fill simulation
- Expand insight integration to handle **cross-item dependencies** (e.g., crafted items)

---

## Questions?
Open an issue or reach out with questions about the simulation architecture, scraping logic, or insight modeling.

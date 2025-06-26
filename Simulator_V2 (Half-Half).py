import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# CONFIG
# -----------------------------
INITIAL_GOLD = 100000

# -----------------------------
# LOAD DATA
# -----------------------------
df = pd.read_csv("aggregated_wow_ah_monthly.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df.sort_values("timestamp", inplace=True)

# Split dataset into historical (train) and live (test)
split_point = df["timestamp"].quantile(0.5)
train_df = df[df["timestamp"] <= split_point].copy()
test_df = df[df["timestamp"] > split_point].copy()

# -----------------------------
# STRATEGY (simple moving average example)
# -----------------------------
def generate_signals(train, test, window=5):
    signals = []
    for item in test["item_name"].unique():
        item_hist = train[train["item_name"] == item].copy()
        item_test = test[test["item_name"] == item].copy()

        if len(item_hist) < window:
            continue

        ma = item_hist["market_value"].rolling(window).mean().iloc[-1]

        for _, row in item_test.iterrows():
            signal = {
                "timestamp": row["timestamp"],
                "item": item,
                "market_value": row["market_value"],
                "min_buyout": row["min_buyout"],
                "action": None,
                "price": row["market_value"],
                "qty": 0
            }

            if row["market_value"] < 0.9 * ma:
                signal["action"] = "BUY"
                signal["qty"] = int(INITIAL_GOLD / len(test["item_name"].unique()) / row["market_value"])
            elif row["market_value"] > 1.1 * ma:
                signal["action"] = "SELL"
                signal["qty"] = -1  # Placeholder: sell all

            if signal["action"]:
                signals.append(signal)
    return signals

# -----------------------------
# SIMULATION
# -----------------------------
def simulate(signals):
    gold = INITIAL_GOLD
    holdings = {}
    log = []
    portfolio = []

    for signal in sorted(signals, key=lambda x: x["timestamp"]):
        item = signal["item"]
        qty = signal["qty"]
        price = signal["price"]
        ts = signal["timestamp"]

        if signal["action"] == "BUY" and qty > 0:
            cost = qty * price
            if gold >= cost:
                gold -= cost
                holdings[item] = holdings.get(item, 0) + qty
                log.append((ts, item, "BUY", qty, price, gold))
        elif signal["action"] == "SELL":
            if item in holdings and holdings[item] > 0:
                qty = holdings[item]
                revenue = qty * price
                gold += revenue
                log.append((ts, item, "SELL", qty, price, gold))
                holdings[item] = 0

        # Portfolio snapshot
        snapshot = {"timestamp": ts, "gold": gold}
        for h_item, h_qty in holdings.items():
            recent_prices = test_df[
                (test_df["item_name"] == h_item) & (test_df["timestamp"] <= ts)
            ]
            if not recent_prices.empty:
                current_price = recent_prices.iloc[-1]["market_value"]
                snapshot[f"asset_{h_item}"] = h_qty * current_price
        portfolio.append(snapshot)

    trade_log = pd.DataFrame(log, columns=["timestamp", "item", "action", "qty", "price", "gold"])
    portfolio_df = pd.DataFrame(portfolio).fillna(0)
    portfolio_df["total_value"] = portfolio_df.drop(columns=["timestamp"]).sum(axis=1)

    return trade_log, portfolio_df

# -----------------------------
# RUN
# -----------------------------
signals = generate_signals(train_df, test_df)
results_df, portfolio_df = simulate(signals)

# Save results
results_df.to_excel("simulated_trades_V2.xlsx", index=False)

# -----------------------------
# VISUALIZE HOLDINGS
# -----------------------------
for item in results_df["item"].unique():
    sub = results_df[results_df["item"] == item]
    sub = sub.sort_values("timestamp")
    sub["cumulative_qty"] = sub.apply(
        lambda row: row["qty"] if row["action"] == "BUY" else -row["qty"], axis=1
    ).cumsum()

    plt.figure(figsize=(10, 4))
    plt.plot(sub["timestamp"], sub["cumulative_qty"], drawstyle="steps-post")
    plt.title(f"Holdings Over Time: {item}")
    plt.xlabel("Timestamp")
    plt.ylabel("Qty Held")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"holdings_{item.replace(' ', '_')}.png")
    plt.close()

# -----------------------------
# GOLD + ASSET VALUE OVER LAST 2 WEEKS
# -----------------------------
two_weeks_ago = portfolio_df["timestamp"].max() - pd.Timedelta(days=14)
recent_portfolio = portfolio_df[portfolio_df["timestamp"] >= two_weeks_ago]

plt.figure(figsize=(10, 5))
plt.plot(recent_portfolio["timestamp"], recent_portfolio["total_value"], color='darkgreen')
plt.title("Total Portfolio Value Over Last 2 Weeks")
plt.xlabel("Timestamp")
plt.ylabel("Gold + Asset Value")
plt.grid(True)
plt.tight_layout()
plt.savefig("portfolio_value_last_2_weeks.png")
plt.close()

print("✅ Simulation complete. Trades saved to Excel. Holdings plots and portfolio value plot generated.")

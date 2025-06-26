import pandas as pd
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
import os

# === Parameters ===
STARTING_GOLD = 100000
MAX_SELL_FRACTION = 0.01  # max 1% of server quantity per SELL
BUY_BUDGET_FRACTION = 0.10  # max 10% of available gold per BUY

# === Load data ===
df = pd.read_csv("aggregated_wow_ah_monthly.csv")
impact_df = pd.read_excel("wowhead_interpreted_item_impacts.xlsx")

# === Compute average impact score per item ===
impact_scores = (
    impact_df.groupby("affected_item")["impact_score"]
    .mean()
    .round(2)
    .to_dict()
)

# === Trader class ===
class WoWAHTraderReinvesting:
    def __init__(self, data, impact_scores):
        self.data = data.copy()
        self.gold = STARTING_GOLD
        self.impact_scores = impact_scores
        self.inventory = defaultdict(lambda: {"qty": 0, "avg_cost": 0})
        self.trade_log = []

    def prepare_data(self):
        df = self.data.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.sort_values(["timestamp", "item_name"], inplace=True)
        df["hour"] = df["timestamp"].dt.hour
        df["dow"] = df["timestamp"].dt.dayofweek
        df["weekly_reset"] = ((df["dow"] == 2) & df["hour"].between(8, 12)).astype(int)
        df["ma7"] = (
            df.groupby("item_name")["market_value"]
            .transform(lambda x: x.rolling(7, min_periods=1).mean().shift(1))
        )
        df["deviation"] = (df["market_value"] - df["ma7"]) / df["ma7"]
        df["impact_score"] = df["item_name"].map(self.impact_scores).fillna(0)
        self.data = df

    def simulate(self):
        self.prepare_data()
        for timestamp, group in self.data.groupby("timestamp"):
            # SELL
            for _, row in group.iterrows():
                item = row["item_name"]
                price = row["market_value"]
                deviation = row["deviation"]
                server_qty = row["quantity"]
                hour = row["hour"]
                dow = row["dow"]

                if deviation > 0.10 or (dow in [2, 3] and hour in [15, 16, 17]):
                    inv = self.inventory[item]
                    if inv["qty"] > 0:
                        sell_qty = min(inv["qty"], int(server_qty * MAX_SELL_FRACTION))
                        if sell_qty <= 0:
                            continue
                        revenue = sell_qty * price
                        inv["qty"] -= sell_qty
                        if inv["qty"] == 0:
                            inv["avg_cost"] = 0
                        self.gold += revenue
                        self.trade_log.append({
                            "timestamp": timestamp,
                            "item": item,
                            "action": "SELL",
                            "price": price,
                            "qty": sell_qty,
                            "gold": self.gold,
                            "reason": "MA spike or post-reset"
                        })

            # BUY
            for _, row in group.iterrows():
                item = row["item_name"]
                price = row["market_value"]
                deviation = row["deviation"]
                impact = row["impact_score"]
                hour = row["hour"]
                qty_available = row["quantity"]
                reset = row["weekly_reset"]

                if deviation < -0.10 and (hour in [3, 4, 5, 6] or reset):
                    multiplier = 1 + (impact / 10)  # bias towards high-impact items
                    budget = BUY_BUDGET_FRACTION * self.gold * multiplier
                    qty = min(qty_available, int(budget // price))
                    cost = qty * price
                    if qty <= 0 or cost > self.gold:
                        continue
                    inv = self.inventory[item]
                    new_qty = inv["qty"] + qty
                    inv["avg_cost"] = (inv["avg_cost"] * inv["qty"] + cost) / new_qty
                    inv["qty"] = new_qty
                    self.gold -= cost
                    self.trade_log.append({
                        "timestamp": timestamp,
                        "item": item,
                        "action": "BUY",
                        "price": price,
                        "qty": qty,
                        "gold": self.gold,
                        "reason": f"MA dip + impact score {round(impact * 10)}"
                    })

    def results(self):
        return pd.DataFrame(self.trade_log)

    def portfolio_value(self, current_prices):
        total = self.gold
        for item, inv in self.inventory.items():
            if inv["qty"] > 0:
                price = current_prices.get(item, inv["avg_cost"])
                total += inv["qty"] * price
        return total

# === Run simulation ===
bot = WoWAHTraderReinvesting(df, impact_scores)
bot.simulate()
log = bot.results()
log.to_csv("reinvesting_trade_log.csv", index=False)

# Excel output
with pd.ExcelWriter("reinvesting_trade_log.xlsx", engine='xlsxwriter') as writer:
    log.to_excel(writer, index=False, sheet_name='Trade Log')
    worksheet = writer.sheets['Trade Log']
    for i, col in enumerate(log.columns):
        width = max(log[col].astype(str).map(len).max(), len(col))
        worksheet.set_column(i, i, width + 2)

# Final values
last_prices = df.groupby("item_name")["market_value"].last().to_dict()
print(f"\n💰 Final Gold: {bot.gold:,.2f}")
print(f"📦 Portfolio Value: {bot.portfolio_value(last_prices):,.2f} gold")

# === Plot holdings ===
os.makedirs("plots", exist_ok=True)
log["timestamp"] = pd.to_datetime(log["timestamp"])
log["qty_change"] = log.apply(lambda x: x["qty"] if x["action"] == "BUY" else -x["qty"], axis=1)
for item in log["item"].unique():
    item_log = log[log["item"] == item].copy()
    item_log["position"] = item_log["qty_change"].cumsum()
    plt.figure(figsize=(10, 4))
    plt.plot(item_log["timestamp"], item_log["position"], drawstyle="steps-post")
    plt.title(f"Holdings Over Time: {item}")
    plt.xlabel("Timestamp")
    plt.ylabel("Quantity Held")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"plots/holdings_{item.replace(' ', '_')}.png")
    plt.close()

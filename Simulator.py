import pandas as pd
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
import os

STARTING_GOLD = 100000

class WoWAHTraderReinvesting:
    def __init__(self, data):
        self.data = data.copy()
        self.gold = STARTING_GOLD
        self.inventory = defaultdict(lambda: {"qty": 0, "avg_cost": 0})
        self.trade_log = []

    def prepare_data(self):
        df = self.data.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.sort_values(["timestamp", "item_name"], inplace=True)
        df["hour"] = df["timestamp"].dt.hour
        df["dow"] = df["timestamp"].dt.dayofweek
        df["weekly_reset"] = ((df["dow"] == 2) & df["hour"].between(8, 12)).astype(int)
        df["ma7"] = df.groupby("item_name")["market_value"].transform(lambda x: x.rolling(7, min_periods=1).mean().shift(1))
        df["deviation"] = (df["market_value"] - df["ma7"]) / df["ma7"]
        self.data = df

    def simulate(self):
        self.prepare_data()
        for timestamp, group in self.data.groupby("timestamp"):
            # SELL first
            for _, row in group.iterrows():
                item = row["item_name"]
                price = row["market_value"]
                deviation = row["deviation"]
                hour = row["hour"]
                dow = row["dow"]
                server_qty = row["quantity"]

                if deviation > 0.10 or (dow in [2, 3] and hour in [15, 16, 17]):
                    inv = self.inventory[item]
                    if inv["qty"] > 0:
                        max_sell_qty = int(0.01 * server_qty)
                        sell_qty = min(inv["qty"], max_sell_qty)
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

            # BUY next
            for _, row in group.iterrows():
                item = row["item_name"]
                price = row["market_value"]
                deviation = row["deviation"]
                hour = row["hour"]
                qty_available = row["quantity"]
                reset = row["weekly_reset"]

                if deviation < -0.10 and (hour in [3, 4, 5, 6] or reset):
                    budget = 0.10 * self.gold
                    qty = min(qty_available, int(budget // price))
                    if qty <= 0:
                        continue

                    cost = qty * price
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
                        "reason": "MA dip + low hour"
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


# --- Run Simulation Locally ---
df = pd.read_csv("aggregated_wow_ah_monthly.csv")

bot = WoWAHTraderReinvesting(df)
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

# Summary
last_prices = df.groupby("item_name")["market_value"].last().to_dict()
print(f"\n💰 Final Gold: {bot.gold:,.2f}")
print(f"📦 Portfolio Value: {bot.portfolio_value(last_prices):,.2f} gold")

# Plot holdings
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

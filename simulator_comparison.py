import pandas as pd
import numpy as np
import importlib.util
import matplotlib.pyplot as plt

# === Load simulator scripts ===
def load_simulator(path, class_name="WoWAHTraderReinvesting"):
    spec = importlib.util.spec_from_file_location("simulator_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)

# === Parameters ===
DATA_PATH = "aggregated_wow_ah_monthly.csv"
INSIGHT_PATH = "wowhead_interpreted_item_impacts.xlsx"
INSIGHTS_SIM_PATH = "C:/Users/batki/Desktop/RSM/FinTech/Simulator w Insights.py"
NO_INSIGHTS_SIM_PATH = "C:/Users/batki/Desktop/RSM/FinTech/Simulator.py"
N_RUNS = 30

# === Load data ===
df = pd.read_csv(DATA_PATH)
impact_df = pd.read_excel(INSIGHT_PATH)

# === Inject market noise into quantity ===
df["quantity"] = df["quantity"] * np.random.uniform(0.8, 1.2, size=len(df))
df["quantity"] = df["quantity"].astype(int)

# === Preprocess insight scores ===
impact_summary = (
    impact_df.groupby("affected_item")["impact_score"]
    .mean()
    .reset_index()
)
impact_scores = dict(zip(impact_summary["affected_item"].str.lower(), impact_summary["impact_score"]))

# === Load simulator classes ===
InsightfulTrader = load_simulator(INSIGHTS_SIM_PATH)
VanillaTrader = load_simulator(NO_INSIGHTS_SIM_PATH)

# === Run multiple simulations ===
def run_batch(sim_class, label, use_insights=False):
    results = []
    for i in range(N_RUNS):
        # Randomize quantity noise each run for variability
        df["quantity"] = df["quantity"] * np.random.uniform(0.8, 1.2, size=len(df))
        df["quantity"] = df["quantity"].astype(int)

        if use_insights:
            trader = sim_class(df, impact_scores)
        else:
            trader = sim_class(df)

        trader.simulate()
        last_prices = df.groupby("item_name")["market_value"].last().to_dict()
        final_gold = trader.gold
        portfolio_val = trader.portfolio_value(last_prices)
        results.append({
            "model": label,
            "run": i+1,
            "final_gold": final_gold,
            "portfolio_value": portfolio_val,
            "total_value": final_gold + portfolio_val
        })
    return pd.DataFrame(results)

# === Collect results ===
print("\u23F3 Running simulations without insights...")
vanilla_df = run_batch(VanillaTrader, "No Insights", use_insights=False)

print("\u23F3 Running simulations with insights...")
insight_df = run_batch(InsightfulTrader, "With Insights", use_insights=True)

# === Combine and export ===
combined = pd.concat([vanilla_df, insight_df], ignore_index=True)
combined.to_csv("simulator_comparison_results.csv", index=False)

# === Summary stats ===
summary = combined.groupby("model")[["final_gold", "portfolio_value", "total_value"]].agg(["mean", "std"])
print("\n\U0001F4CA Simulation Comparison Summary:")
print(summary)

# === Plot ===
plt.figure(figsize=(8, 5))
metrics = ["final_gold", "portfolio_value", "total_value"]
x = np.arange(len(metrics))
bar_width = 0.35

grouped = combined.groupby("model")[metrics].agg(["mean", "std"])
models = grouped.index.tolist()

for i, model in enumerate(models):
    means = grouped.loc[model].xs("mean", level=1)
    stds = grouped.loc[model].xs("std", level=1)
    plt.bar(x + i * bar_width, means, bar_width, yerr=stds, capsize=5, label=model)

plt.xticks(x + bar_width / 2, ["Final Gold", "Portfolio", "Total"])
plt.ylabel("Gold Value")
plt.title("Simulator Performance Comparison (N=30)")
plt.legend()
plt.grid(True, axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("simulator_model_comparison.png")
plt.show()

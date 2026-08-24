import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# 1. Setup Financial Parameters
np.random.seed(101)
current_nest_egg = 50000        # Starting investment balance
years_to_retirement = 30         # Time horizon
simulations = 2000              # Number of "alternate realities" to test

# Annual Cash Flow
annual_contribution = 6000      # How much you save every year

# Market Expectations (e.g., S&P 500 historical averages)
expected_annual_return = 0.08   # 8% average return
market_volatility = 0.15        # 15% standard deviation (swings up and down)

# 2. Initialize Data Structure (Rows = Years, Columns = Simulation Runs)
portfolio_paths = np.zeros((years_to_retirement + 1, simulations))
portfolio_paths[0] = current_nest_egg

# 3. Run the Simulation
for year in range(1, years_to_retirement + 1):
    # Every simulation run gets a different random market return for this year
    random_market_returns = np.random.normal(expected_annual_return, market_volatility, simulations)

    # Calculate next year's balance: (Old Balance * Market Return) + New Contribution
    portfolio_paths[year] = (portfolio_paths[year - 1] * (1 + random_market_returns)) + annual_contribution

    # Debt/Floor protection: You can't have less than $0
    portfolio_paths[year] = np.maximum(portfolio_paths[year], 0)

# 4. Plot the Results
plt.figure(figsize=(10, 6))
plt.plot(portfolio_paths, lw=0.3, alpha=0.5, color='teal')
plt.title(f"Personal Finance Projection: {simulations} Paths Over {years_to_retirement} Years")
plt.xlabel("Years from Now")
plt.ylabel("Portfolio Value ($)")
plt.grid(True, linestyle="--", alpha=0.3)
plt.ticklabel_format(style='plain', axis='y') # Prevents scientific notation

SAVE_DIR: Path = Path.home() / "Pictures"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

plt.savefig(SAVE_DIR / "monte_carlo_finance.png", dpi=300, bbox_inches="tight")
plt.close()

# 5. Extract Insights
ending_balances = portfolio_paths[-1]
success_threshold = 500000     # Let's say your target goal is half a million
successful_runs = np.sum(ending_balances >= success_threshold)
success_rate = (successful_runs / simulations) * 100

print(f"Median Ending Balance: ${np.median(ending_balances):,.2f}")
print(f"Worst-Case Scenario (Bottom 5%): ${np.percentile(ending_balances, 5):,.2f}")
print(f"Best-Case Scenario (Top 5%): ${np.percentile(ending_balances, 95):,.2f}")
print(f"Probability of hitting your ${success_threshold:,} goal: {success_rate:.1f}%")

import json
import pandas as pd
import os
from datetime import datetime, timedelta
import sys

# Add the project root to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.fetch_data import fetch_price_data, fetch_benchmark_data
from scripts.portfolio import (
    simulate_portfolio, 
    calculate_returns, 
    calculate_metrics, 
    compare_to_benchmark
)

OUTPUT_DIR = "docs/data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def pd_to_json(df):
    """Convert pandas dataframes to JSON with ISO date format"""
    if isinstance(df, pd.DataFrame):
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        return json.loads(df.to_json(orient='records', date_format='iso'))
    elif isinstance(df, pd.Series):
        if isinstance(df.index, pd.DatetimeIndex):
            return {date.strftime('%Y-%m-%d'): value for date, value in df.items()}
        return df.to_dict()
    else:
        return df

def generate_data_files(tickers=["VTI", "BND"], weights={"VTI": 0.6, "BND": 0.4}, 
                       years_back=10, rebalance_period="Q", initial_cash=100000):
    """Generate static data files for the given portfolio configuration"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365 * years_back)
    
    # Get price data
    print(f"Fetching price data for {tickers} from {start_date} to {end_date}...")
    prices = fetch_price_data(tickers, start_date, end_date)
    
    # Simulate portfolio
    print(f"Simulating portfolio with {rebalance_period} rebalancing...")
    portfolio = simulate_portfolio(prices, weights, initial_cash=initial_cash, 
                                 rebalance_period=rebalance_period)
    
    # Calculate returns and metrics
    returns = calculate_returns(portfolio)
    metrics = calculate_metrics(returns)
    
    # Get benchmark data
    print("Fetching benchmark data...")
    benchmarks = fetch_benchmark_data(start_date, end_date)
    
    # Compare to benchmarks
    if "^GSPC" in benchmarks.columns:
        benchmark_returns = benchmarks["^GSPC"].pct_change().dropna()
        comparison = compare_to_benchmark(returns['daily'], benchmark_returns)
    else:
        comparison = {}
    
    # Monthly returns table
    monthly_returns = returns['monthly'] * 100
    monthly_table = pd.DataFrame({
        'Year': monthly_returns.index.year,
        'Month': monthly_returns.index.month,
        'Return': monthly_returns.values
    })
    pivot = monthly_table.pivot(index='Year', columns='Month', values='Return')
    
    # Export to JSON
    data_files = {
        "portfolio.json": pd_to_json(portfolio),
        "benchmarks.json": pd_to_json(benchmarks),
        "metrics.json": {
            "returns": {k: pd_to_json(v) for k, v in returns.items()},
            "performance": metrics,
            "comparison": comparison
        },
        "monthly_returns.json": pd_to_json(pivot),
        "config.json": {
            "tickers": tickers,
            "weights": weights,
            "rebalance_period": rebalance_period,
            "initial_investment": initial_cash,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    
    # Write files
    for filename, data in data_files.items():
        output_path = os.path.join(OUTPUT_DIR, filename)
        with open(output_path, 'w') as f:
            json.dump(data, f)
        print(f"Generated {output_path}")
    
    print("Data generation complete!")
    return data_files

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate static data files for portfolio dashboard")
    parser.add_argument("--tickers", nargs='+', default=["VTI", "BND"], 
                        help="Ticker symbols (space separated)")
    parser.add_argument("--weights", type=str, default="0.6,0.4",
                        help="Weights for each ticker (comma separated)")
    parser.add_argument("--years", type=int, default=10, 
                        help="Years of historical data to include")
    parser.add_argument("--rebalance", type=str, default="Q", choices=["M", "Q", "A", "N"],
                        help="Rebalance period (M=monthly, Q=quarterly, A=annually, N=never)")
    parser.add_argument("--initial", type=int, default=100000,
                        help="Initial investment amount")
    
    args = parser.parse_args()
    
    # Parse weights to make a dict with tickers as keys
    weight_values = [float(w) for w in args.weights.split(",")]
    if len(weight_values) != len(args.tickers):
        raise ValueError("Number of weights must match number of tickers")
    weights = {t: w for t, w in zip(args.tickers, weight_values)}
    
    # Generate data files
    generate_data_files(
        tickers=args.tickers,
        weights=weights,
        years_back=args.years,
        rebalance_period=args.rebalance,
        initial_cash=args.initial
    ) 
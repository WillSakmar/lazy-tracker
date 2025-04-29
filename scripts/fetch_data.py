import yfinance as yf
import pandas as pd
import os
from datetime import datetime

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_price_data(tickers, start, end, use_cache=True):
    """
    Fetches historical adjusted close prices for given tickers.
    Supports caching results to avoid repeated API calls.
    """
    # Try to load from cache first
    today = datetime.now().strftime("%Y-%m-%d")
    cache_file = os.path.join(DATA_DIR, f"prices_{start}_{today}.csv")
    
    if use_cache and os.path.exists(cache_file):
        try:
            cached_data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            # Check if all requested tickers are in the cached data
            if all(ticker in cached_data.columns for ticker in tickers):
                return cached_data[tickers]
        except Exception:
            # If there's any error loading cache, fetch fresh data
            pass
    
    # Fetch fresh data
    try:
        # Try the standard approach first
        data = yf.download(tickers, start=start, end=end, progress=False)
        
        # Check if 'Adj Close' exists in the data
        if 'Adj Close' in data.columns:
            price_data = data['Adj Close']
        else:
            # If not, try to use 'Close' data instead
            price_data = data['Close']
            
    except KeyError:
        # If a KeyError is raised, it's likely the data is not multi-level
        # This happens with a single ticker sometimes
        data = yf.download(tickers, start=start, end=end, progress=False)
        price_data = data['Close']  # Use 'Close' as a fallback
    
    # Handle single ticker case
    if isinstance(price_data, pd.Series):
        price_data = pd.DataFrame(price_data, columns=[tickers])
    
    # Forward fill missing values and drop rows that are still NA
    price_data = price_data.ffill().dropna()
    
    # Save to cache
    if use_cache:
        price_data.to_csv(cache_file)
    
    return price_data

def fetch_benchmark_data(start, end, benchmarks=None):
    """
    Fetches benchmark indices for comparison.
    Default benchmarks: S&P 500, Total Bond Market, 60/40 blend
    """
    if benchmarks is None:
        benchmarks = ["^GSPC", "BND"]  # S&P 500, Bond market
        
    bench_data = fetch_price_data(benchmarks, start, end)
    
    # Normalize to 100 at start
    norm_data = bench_data.div(bench_data.iloc[0]) * 100
    
    # Add 60/40 benchmark if we have both stock and bond data
    if "^GSPC" in norm_data.columns and "BND" in norm_data.columns:
        norm_data["60/40"] = 0.6 * norm_data["^GSPC"] + 0.4 * norm_data["BND"]
    
    return norm_data

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch adjusted close price data for tickers"
    )
    parser.add_argument(
        "--tickers", nargs="+", default=["VTI", "BND"],
        help="List of ticker symbols"
    )
    parser.add_argument(
        "--start", default="2015-01-01",
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end", default=None,
        help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--benchmarks", action="store_true",
        help="Also fetch benchmark data"
    )
    args = parser.parse_args()

    df = fetch_price_data(args.tickers, args.start, args.end)
    print("Price data:")
    print(df.tail())
    
    if args.benchmarks:
        bench_df = fetch_benchmark_data(args.start, args.end)
        print("\nBenchmark data:")
        print(bench_df.tail())

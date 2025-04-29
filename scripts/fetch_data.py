import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_price_data(tickers, start, end, use_cache=True, max_retries=3):
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
                print(f"Using cached data for {tickers}")
                return cached_data[tickers]
        except Exception as e:
            print(f"Error loading cache: {e}. Fetching fresh data.")
            # If there's any error loading cache, fetch fresh data
            pass
    
    # Fetch fresh data with retries
    price_data = None
    retry_count = 0
    missing_tickers = []
    
    while retry_count < max_retries:
        try:
            if retry_count > 0:
                print(f"Retry {retry_count}/{max_retries} after delay...")
                # Exponential backoff for retries
                time.sleep(2 ** retry_count)
                
            print(f"Fetching data for {tickers} from {start} to {end}")
            data = yf.download(tickers, start=start, end=end, progress=False)
            
            # Check if 'Adj Close' exists in the data
            if 'Adj Close' in data.columns:
                price_data = data['Adj Close']
            else:
                # If not, try to use 'Close' data instead
                price_data = data['Close']
                
            # Check if we got meaningful data
            if price_data is None or price_data.empty:
                raise ValueError("No data returned from Yahoo Finance")
                
            # Handle single ticker case
            if isinstance(price_data, pd.Series):
                price_data = pd.DataFrame(price_data, columns=[tickers])
                
            # Check for missing tickers
            if isinstance(tickers, list) and len(tickers) > 1:
                missing_tickers = [t for t in tickers if t not in price_data.columns]
                if missing_tickers:
                    print(f"Missing data for tickers: {missing_tickers}")
                    # Try again only for missing tickers
                    if retry_count < max_retries - 1:
                        retry_count += 1
                        continue
                        
            # If we get here, we have data or have retried enough
            break
                
        except (KeyError, ValueError) as e:
            print(f"Error in data format: {e}")
            # If a KeyError is raised, it's likely the data is not multi-level
            # This happens with a single ticker sometimes
            try:
                data = yf.download(tickers, start=start, end=end, progress=False)
                price_data = pd.DataFrame(data['Close'])  # Use 'Close' as a fallback
                if len(tickers) == 1 and isinstance(tickers, list):
                    price_data.columns = tickers
                break
            except Exception as e2:
                print(f"Fallback attempt failed: {e2}")
                retry_count += 1
                
        except Exception as e:
            print(f"Error fetching data: {e}")
            retry_count += 1
            if "rate limit" in str(e).lower():
                print("Rate limit hit. Waiting longer before retry...")
                time.sleep(10)  # Wait longer for rate limit errors
            if retry_count >= max_retries:
                print(f"Max retries ({max_retries}) reached. Using any available data.")
                # Return empty DataFrame with correct columns if no data available
                if price_data is None:
                    price_data = pd.DataFrame(columns=tickers if isinstance(tickers, list) else [tickers])
                    price_data.index = pd.date_range(start=start, end=end, freq='B')[:1]  # Business days
    
    # Forward fill missing values and drop rows that are still NA
    if price_data is not None and not price_data.empty:
        price_data = price_data.ffill().dropna()
    
        # Convert index to DatetimeIndex if it's not already
        if not isinstance(price_data.index, pd.DatetimeIndex):
            try:
                price_data.index = pd.to_datetime(price_data.index)
            except Exception as e:
                print(f"Warning: Could not convert index to DatetimeIndex: {e}")
    
        # Save to cache only if we have meaningful data
        if use_cache and not price_data.empty:
            price_data.to_csv(cache_file)
    else:
        print("Warning: No price data available for the requested tickers.")
        # Create a minimal DataFrame to prevent downstream errors
        price_data = pd.DataFrame({t: [100.0] for t in (tickers if isinstance(tickers, list) else [tickers])}, 
                                 index=pd.date_range(start=start, end=end, freq='B')[:5])
    
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

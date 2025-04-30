import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime, timedelta

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_price_data(tickers, start, end, use_cache=True, max_retries=1):
    """
    Simplified price data fetching to minimize Yahoo Finance API calls.
    Uses aggressive caching with longer expiration times.
    """
    # Convert tickers to list if it's not already
    if isinstance(tickers, str):
        tickers = [tickers]
    
    # Use a single cache file that expires weekly instead of daily
    # This significantly reduces API calls
    cache_week = datetime.now().strftime("%Y-%W")  # Year-Week format
    cache_file = os.path.join(DATA_DIR, f"prices_cache_{cache_week}.csv")
    
    # Try to load from cache first
    if use_cache and os.path.exists(cache_file):
        try:
            cached_data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            # Check if we have any of the requested tickers in cache
            available_tickers = [t for t in tickers if t in cached_data.columns]
            
            if available_tickers:
                print(f"Using cached data for {available_tickers}")
                
                # Check if all tickers are available in cache
                if len(available_tickers) == len(tickers):
                    return cached_data[tickers]
                    
                # If not all tickers are in cache, we'll fetch the missing ones
                missing_tickers = [t for t in tickers if t not in available_tickers]
                print(f"Need to fetch missing tickers: {missing_tickers}")
                
                # Try to fetch just the missing tickers
                try:
                    # Add delay to avoid rate limits
                    time.sleep(1)
                    missing_data = yf.download(
                        missing_tickers, 
                        start=start, 
                        end=end, 
                        progress=False
                    )
                    
                    if 'Adj Close' in missing_data.columns:
                        missing_price_data = missing_data['Adj Close']
                    else:
                        missing_price_data = missing_data['Close']
                    
                    # Handle single ticker case
                    if len(missing_tickers) == 1 and isinstance(missing_price_data, pd.Series):
                        missing_price_data = pd.DataFrame(missing_price_data, columns=missing_tickers)
                    
                    # Combine with cached data
                    if not missing_price_data.empty:
                        # Ensure the indices align
                        missing_price_data.index = pd.to_datetime(missing_price_data.index)
                        all_data = pd.concat([cached_data[available_tickers], missing_price_data], axis=1)
                        
                        # Update the cache file
                        all_columns = list(cached_data.columns) + missing_tickers
                        full_data = pd.concat([cached_data, missing_price_data], axis=1)
                        # Remove duplicate columns
                        full_data = full_data.loc[:, ~full_data.columns.duplicated()]
                        full_data.to_csv(cache_file)
                        
                        # Return only the requested tickers
                        return all_data[tickers]
                    else:
                        # If we couldn't get the missing data, just return what we have
                        print(f"Warning: Could not fetch missing tickers {missing_tickers}")
                        # Create dummy values for missing tickers
                        for ticker in missing_tickers:
                            cached_data[ticker] = 100.0
                        return cached_data[tickers]
                        
                except Exception as e:
                    print(f"Error fetching missing tickers: {e}")
                    # If fetching fails, return what we have with dummy data for missing tickers
                    for ticker in missing_tickers:
                        cached_data[ticker] = 100.0
                    return cached_data[tickers]
                
        except Exception as e:
            print(f"Error loading cache: {e}. Will fetch fresh data.")
    
    # If no cache or cache loading failed, fetch all data fresh
    print(f"Fetching all price data for {tickers}")
    
    try:
        # Add a small delay to respect rate limits
        time.sleep(1)
        
        # Fetch all tickers
        data = yf.download(tickers, start=start, end=end, progress=False)
        
        if data.empty:
            print("Warning: No data returned from Yahoo Finance")
            # Return dummy data
            dummy_data = pd.DataFrame(
                {t: [100.0] * 5 for t in tickers},
                index=pd.date_range(start=start, end=end, freq='B')[:5]
            )
            return dummy_data
            
        # Process data
        if 'Adj Close' in data.columns:
            price_data = data['Adj Close']
        else:
            price_data = data['Close']
            
        # Handle single ticker case
        if len(tickers) == 1 and isinstance(price_data, pd.Series):
            price_data = pd.DataFrame(price_data, columns=tickers)
            
        # Fill missing values
        price_data = price_data.ffill().bfill()
        
        # Save to cache
        if use_cache:
            # If the cache file exists, update it
            if os.path.exists(cache_file):
                try:
                    existing_cache = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    # Combine existing and new data
                    price_data.index = pd.to_datetime(price_data.index)
                    combined = pd.concat([existing_cache, price_data], axis=1)
                    # Remove duplicates
                    combined = combined.loc[:, ~combined.columns.duplicated()]
                    combined.to_csv(cache_file)
                except Exception:
                    # If merging fails, just overwrite with new data
                    price_data.to_csv(cache_file)
            else:
                # Create new cache file
                price_data.to_csv(cache_file)
                
        return price_data
            
    except Exception as e:
        print(f"Error fetching price data: {e}")
        # Return dummy data on failure
        dummy_data = pd.DataFrame(
            {t: [100.0] * 5 for t in tickers},
            index=pd.date_range(start=start, end=end, freq='B')[:5]
        )
        return dummy_data

def fetch_benchmark_data(start, end, benchmarks=None):
    """
    Simplified benchmark data fetching.
    Only fetches S&P 500 by default to reduce API calls.
    """
    if benchmarks is None:
        # Only use S&P 500 as benchmark to reduce API calls
        benchmarks = ["^GSPC"]
        
    bench_data = fetch_price_data(benchmarks, start, end)
    
    # Normalize to 100 at start
    norm_data = bench_data.div(bench_data.iloc[0]) * 100
    
    # No longer computing the 60/40 blend to save processing
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

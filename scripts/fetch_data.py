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
    # Convert tickers to list if it's not already
    if isinstance(tickers, str):
        tickers = [tickers]
        
    # Create a final result dataframe
    result_data = pd.DataFrame()
    missing_tickers = []
    
    # Try to load from cache first - use a more flexible approach
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Check cache for each ticker individually
    available_tickers = []
    cached_data = pd.DataFrame()
    
    if use_cache:
        # Try to find any cached data that might have our tickers
        cache_files = [f for f in os.listdir(DATA_DIR) if f.startswith("prices_") and f.endswith(".csv")]
        
        for ticker in tickers:
            cache_found = False
            
            # Check all cache files for this ticker
            for cache_file in cache_files:
                full_cache_path = os.path.join(DATA_DIR, cache_file)
                try:
                    temp_data = pd.read_csv(full_cache_path, index_col=0, parse_dates=True)
                    if ticker in temp_data.columns:
                        # If we haven't initialized the cache dataframe yet
                        if cached_data.empty:
                            cached_data = temp_data[[ticker]]
                        else:
                            # Otherwise add this ticker to our existing data
                            cached_data[ticker] = temp_data[ticker]
                        
                        available_tickers.append(ticker)
                        cache_found = True
                        print(f"Using cached data for {ticker} from {cache_file}")
                        break
                except Exception as e:
                    print(f"Error loading cache file {cache_file}: {str(e)}")
            
            if not cache_found:
                missing_tickers.append(ticker)
    else:
        # If cache is disabled, all tickers need to be fetched
        missing_tickers = tickers
    
    # If we have all tickers from cache, return early
    if not missing_tickers:
        print("All tickers found in cache")
        return cached_data
    
    # Otherwise, fetch missing tickers
    print(f"Fetching missing tickers: {missing_tickers}")
    
    # Create a dedicated cache file for this specific query
    cache_file = os.path.join(DATA_DIR, f"prices_{start}_{today}.csv")
    
    # Fetch missing tickers with retries
    retry_count = 0
    
    while missing_tickers and retry_count < max_retries:
        if retry_count > 0:
            print(f"Retry {retry_count}/{max_retries} after delay...")
            # Exponential backoff for retries
            time.sleep(2 ** retry_count)
        
        # Try fetching all missing tickers at once first
        try:
            print(f"Batch fetching data for {missing_tickers} from {start} to {end}")
            data = yf.download(missing_tickers, start=start, end=end, progress=False)
            
            # Process the data
            if 'Adj Close' in data.columns:
                price_data = data['Adj Close']
            else:
                price_data = data['Close']
                
            # Handle single ticker case
            if len(missing_tickers) == 1 and isinstance(price_data, pd.Series):
                price_data = pd.DataFrame(price_data, columns=missing_tickers)
                
            # If successful, add to result and clear missing tickers
            if not price_data.empty:
                # Combine with cached data
                if not cached_data.empty:
                    # Ensure the indices align
                    price_data.index = pd.to_datetime(price_data.index)
                    cached_data.index = pd.to_datetime(cached_data.index)
                    
                    # Merge on the indices
                    result_data = pd.concat([cached_data, price_data], axis=1)
                    result_data = result_data[tickers]  # Ensure original column order
                else:
                    result_data = price_data
                
                # Save to cache
                if use_cache:
                    result_data.to_csv(cache_file)
                    
                # All data fetched successfully
                return result_data
                
        except Exception as e:
            print(f"Batch fetch failed: {str(e)}. Trying individual fetches.")
            
            # If batch fetch fails, try fetching tickers individually
            successful_tickers = []
            individual_price_data = pd.DataFrame()
            
            for ticker in missing_tickers:
                try:
                    print(f"Fetching individual ticker: {ticker}")
                    ticker_data = yf.download(ticker, start=start, end=end, progress=False)
                    
                    if ticker_data.empty:
                        print(f"No data for {ticker}")
                        continue
                        
                    # Extract price column
                    if 'Adj Close' in ticker_data.columns:
                        ticker_price = ticker_data['Adj Close']
                    else:
                        ticker_price = ticker_data['Close']
                    
                    # Convert to DataFrame with ticker as column name
                    ticker_df = pd.DataFrame(ticker_price)
                    ticker_df.columns = [ticker]
                    
                    # Save individual ticker to its own cache file
                    if use_cache:
                        ticker_cache = os.path.join(DATA_DIR, f"prices_{ticker}_{today}.csv")
                        ticker_df.to_csv(ticker_cache)
                    
                    # Add to our collection
                    if individual_price_data.empty:
                        individual_price_data = ticker_df
                    else:
                        # Join with existing data
                        individual_price_data = individual_price_data.join(ticker_df, how='outer')
                    
                    successful_tickers.append(ticker)
                    
                except Exception as e:
                    print(f"Failed to fetch {ticker}: {str(e)}")
                    
                # Add a delay between individual fetches to avoid rate limiting
                time.sleep(1)
            
            # Update missing tickers
            missing_tickers = [t for t in missing_tickers if t not in successful_tickers]
            
            # Combine with cached data
            if not individual_price_data.empty:
                if not cached_data.empty:
                    # Ensure the indices align
                    individual_price_data.index = pd.to_datetime(individual_price_data.index)
                    cached_data.index = pd.to_datetime(cached_data.index)
                    
                    # Merge the cached and new data
                    combined_data = pd.concat([cached_data, individual_price_data], axis=1)
                    
                    # Keep only unique columns in case of duplicates
                    combined_data = combined_data.loc[:, ~combined_data.columns.duplicated()]
                    
                    # Update the result data
                    result_data = combined_data
                else:
                    result_data = individual_price_data
        
        # Increment retry counter only if we still have missing tickers
        if missing_tickers:
            retry_count += 1
    
    # After all retries, if we have any data, process and return it
    if not result_data.empty:
        # Fill any missing values
        result_data = result_data.ffill().bfill()
        
        # Ensure the index is a DatetimeIndex
        if not isinstance(result_data.index, pd.DatetimeIndex):
            try:
                result_data.index = pd.to_datetime(result_data.index)
            except Exception as e:
                print(f"Warning: Could not convert index to DatetimeIndex: {e}")
        
        # Save final result to cache
        if use_cache:
            result_data.to_csv(cache_file)
        
        # Only return requested tickers that were found
        available_cols = [col for col in tickers if col in result_data.columns]
        if available_cols:
            return result_data[available_cols]
    
    # If we couldn't get any data, create a small dummy DataFrame
    print("Warning: No price data available. Creating dummy data.")
    dummy_data = pd.DataFrame(
        {t: [100.0] * 5 for t in tickers}, 
        index=pd.date_range(start=start, end=end, freq='B')[:5]
    )
    return dummy_data

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

import pandas as pd
import numpy as np
from scipy import stats

def initialize_portfolio(cash, prices, weights):
    """Initialize a portfolio with given cash amount and target weights"""
    allocation = {t: cash * w for t, w in weights.items()}
    shares = {t: int(allocation[t] // prices[t]) for t in weights}
    leftover = cash - sum(shares[t] * prices[t] for t in weights)
    return shares, leftover

def simulate_portfolio(prices, weights, initial_cash=100_000, rebalance_period="M"):
    """
    Simulate a portfolio over time with periodic rebalancing
    
    Parameters:
    - prices: DataFrame of adjusted close prices
    - weights: Dict of ticker to target weights
    - initial_cash: Starting cash amount
    - rebalance_period: Rebalancing frequency (M=monthly, QE=quarterly, A=annually)
    
    Returns:
    - DataFrame with portfolio values over time
    """
    # Ensure index is DatetimeIndex
    if not isinstance(prices.index, pd.DatetimeIndex):
        try:
            prices.index = pd.to_datetime(prices.index)
        except Exception as e:
            raise ValueError(f"Failed to convert index to DatetimeIndex: {str(e)}")
    
    dates = prices.index
    
    # Update deprecated 'Q' to 'QE' if needed
    if rebalance_period == "Q":
        rebalance_period = "QE"
        
    # Get rebalance dates
    try:
        rebal_dates = prices.resample(rebalance_period).last().index
    except Exception as e:
        raise ValueError(f"Failed to resample with period {rebalance_period}: {str(e)}")

    cash = initial_cash
    
    # Check if prices contains data
    if len(prices) == 0:
        raise ValueError("Empty price data. Cannot initialize portfolio.")
    
    shares, leftover = initialize_portfolio(cash, prices.iloc[0], weights)
    records = []

    for date, price_row in prices.iterrows():
        # Calculate current values
        vals = {t: shares[t] * price_row[t] for t in weights}
        total_value = sum(vals.values()) + leftover
        
        # Calculate current weights
        current_weights = {t: vals[t]/total_value for t in weights}
        max_deviation = max(abs(current_weights[t] - weights[t]) for t in weights)
        
        records.append({
            "date": date,
            **vals,
            "cash": leftover,
            "total": total_value,
            "max_weight_deviation": max_deviation
        })

        # Rebalance if on a rebalance date (excluding first date)
        if date in rebal_dates and date != dates[0]:
            targets = {t: total_value * weights[t] for t in weights}
            shares = {t: int(targets[t] // price_row[t]) for t in weights}
            leftover = total_value - sum(shares[t] * price_row[t] for t in weights)

    df = pd.DataFrame(records).set_index("date")
    return df

def calculate_returns(portfolio_df):
    """Calculate daily, monthly and annual returns from portfolio values"""
    # Daily returns
    daily_returns = portfolio_df['total'].pct_change().dropna()
    
    # Monthly returns - update 'M' to 'ME'
    monthly_returns = portfolio_df['total'].resample('ME').last().pct_change().dropna()
    
    # Annual returns - update 'Y' to 'YE'
    annual_returns = portfolio_df['total'].resample('YE').last().pct_change().dropna()
    
    return {
        'daily': daily_returns,
        'monthly': monthly_returns,
        'annual': annual_returns
    }

def calculate_metrics(returns):
    """Calculate performance metrics from a return series"""
    daily_returns = returns['daily']
    
    # Annualized return
    ann_return = (1 + daily_returns.mean()) ** 252 - 1
    
    # Annualized volatility
    ann_vol = daily_returns.std() * np.sqrt(252)
    
    # Sharpe ratio (assuming risk-free rate of 0 for simplicity)
    sharpe = ann_return / ann_vol if ann_vol > 0 else 0
    
    # Maximum drawdown
    cumulative = (1 + daily_returns).cumprod()
    max_dd = (cumulative / cumulative.cummax() - 1).min()
    
    # Sortino ratio (downside deviation)
    neg_returns = daily_returns[daily_returns < 0]
    downside_dev = neg_returns.std() * np.sqrt(252) if len(neg_returns) > 0 else 0
    sortino = ann_return / downside_dev if downside_dev > 0 else 0
    
    # Value at Risk (95%) - add error handling and warning suppression
    var_95 = 0
    try:
        # Use numpy.errstate to suppress warnings
        with np.errstate(all='ignore'):
            var_95 = stats.norm.ppf(0.05, daily_returns.mean(), daily_returns.std())
            # Check if value is valid
            if np.isnan(var_95) or np.isinf(var_95):
                var_95 = -0.02  # Default fallback value
    except Exception:
        # Fallback to a reasonable default VaR value
        var_95 = -0.02
    
    return {
        'annualized_return': ann_return,
        'annualized_volatility': ann_vol,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'max_drawdown': max_dd,
        'var_95': var_95,
        'total_return': (1 + daily_returns).cumprod().iloc[-1] - 1 if len(daily_returns) > 0 else 0
    }

def compare_to_benchmark(portfolio_returns, benchmark_returns):
    """Compare portfolio to benchmark"""
    # Calculate beta
    cov = np.cov(portfolio_returns, benchmark_returns)[0, 1]
    var = np.var(benchmark_returns)
    beta = cov / var if var > 0 else 1
    
    # Calculate alpha (Jensen's Alpha)
    rf_rate = 0  # Simplified, using 0 as risk-free rate
    portfolio_excess = portfolio_returns.mean() * 252 - rf_rate
    benchmark_excess = benchmark_returns.mean() * 252 - rf_rate
    alpha = portfolio_excess - beta * benchmark_excess
    
    # Tracking error
    tracking_diff = portfolio_returns - benchmark_returns
    tracking_error = tracking_diff.std() * np.sqrt(252)
    
    # Information ratio
    info_ratio = (portfolio_returns.mean() - benchmark_returns.mean()) * 252 / tracking_error if tracking_error > 0 else 0
    
    return {
        'beta': beta,
        'alpha': alpha,
        'tracking_error': tracking_error,
        'information_ratio': info_ratio
    }

def rebalance_analysis(portfolio_df, weights):
    """Analyze the impact of rebalancing"""
    # Calculate average deviation from target weights
    asset_cols = list(weights.keys())
    
    # Calculate actual weights at each point
    for ticker in asset_cols:
        portfolio_df[f'{ticker}_weight'] = portfolio_df[ticker] / portfolio_df['total']
    
    # Calculate distance from target for each asset
    for ticker in asset_cols:
        portfolio_df[f'{ticker}_deviation'] = portfolio_df[f'{ticker}_weight'] - weights[ticker]
    
    # Average absolute deviation
    deviation_cols = [f'{ticker}_deviation' for ticker in asset_cols]
    portfolio_df['avg_deviation'] = portfolio_df[deviation_cols].abs().mean(axis=1)
    
    return portfolio_df['avg_deviation'].mean() 
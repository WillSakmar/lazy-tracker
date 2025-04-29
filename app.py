import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

from scripts.fetch_data import fetch_price_data, fetch_benchmark_data
from scripts.portfolio import (
    simulate_portfolio, 
    calculate_returns, 
    calculate_metrics, 
    compare_to_benchmark,
    rebalance_analysis
)

# Set page configuration
st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Default portfolio settings
DEFAULT_WEIGHTS = {"VTI": 0.6, "BND": 0.4}
DEFAULT_INITIAL_CASH = 100_000

def format_pct(val, precision=2):
    """Format a value as a percentage string"""
    return f"{val*100:.{precision}f}%"

def format_currency(val, precision=2):
    """Format a value as USD currency string"""
    return f"${val:,.{precision}f}"

def main():
    # Sidebar for settings
    with st.sidebar:
        st.title("Preferences")
        
        # Date range
        st.header("Date Range")
        today = datetime.now().date()
        start = st.date_input(
            "Start date", 
            value=datetime(2015, 1, 1).date(),
            max_value=today - timedelta(days=30)
        )
        end = st.date_input("End date", value=today)
        
        # Portfolio settings
        st.header("Portfolio Settings")
        
        # Allow user to add/remove tickers
        st.subheader("Assets")
        tickers = st.text_input(
            "Ticker symbols (comma separated)", 
            value="VTI,BND"
        ).upper().replace(" ", "").split(",")
        
        # Dynamic weight input based on tickers
        weights = {}
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Weights")
            total_weight = 0
            for i, ticker in enumerate(tickers):
                weight = st.slider(
                    f"{ticker} weight", 
                    min_value=0.0, 
                    max_value=1.0, 
                    value=DEFAULT_WEIGHTS.get(ticker, 1.0/len(tickers)),
                    step=0.05,
                    key=f"weight_{ticker}"
                )
                weights[ticker] = weight
                total_weight += weight
            
            # Warning if weights don't sum to 1
            if abs(total_weight - 1.0) > 0.001:
                st.warning(f"Weights sum to {total_weight:.2f}, not 1.0")
                
        with col2:
            st.subheader("Configuration")
            initial_cash = st.number_input(
                "Initial investment ($)", 
                min_value=1000,
                max_value=10_000_000,
                value=DEFAULT_INITIAL_CASH,
                step=10000
            )
            
            rebalance_options = {
                "M": "Monthly",
                "Q": "Quarterly",
                "A": "Annually",
                "N": "Never"
            }
            
            rebalance_period = st.selectbox(
                "Rebalance frequency",
                list(rebalance_options.keys()),
                format_func=lambda k: rebalance_options[k],
                index=1  # Default to quarterly
            )
            
            show_benchmark = st.checkbox("Show benchmarks", value=True)
        
        # Add a refresh data button
        refresh_data = st.button("Refresh Data")
        
    # Main dashboard area
    st.title("Portfolio Dashboard")
    
    # Prevent fetching if weights don't sum to approx 1
    if abs(total_weight - 1.0) > 0.05:
        st.error("Portfolio weights must sum to approximately 1.0")
        return
    
    # Get the price data
    prices = fetch_price_data(
        tickers,
        start,
        end + timedelta(days=1),
        use_cache=not refresh_data
    )
    
    # Simulate the portfolio
    if rebalance_period == "N":
        # If no rebalancing, use a very long period that won't trigger
        rebal_period = "100Y"
    else:
        rebal_period = rebalance_period
        
    perf = simulate_portfolio(
        prices, 
        weights, 
        initial_cash=initial_cash, 
        rebalance_period=rebal_period
    )
    
    # Calculate portfolio returns and metrics
    returns = calculate_returns(perf)
    metrics = calculate_metrics(returns)
    
    # Main dashboard content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Value over time chart
        st.subheader("Portfolio Value")
        fig_value = px.line(
            perf, 
            y="total", 
            labels={"total": "Portfolio Value ($)", "date": "Date"},
            title="Portfolio Value Over Time"
        )
        
        # Add benchmarks if requested
        if show_benchmark:
            bench_data = fetch_benchmark_data(start, end + timedelta(days=1))
            
            # Normalize benchmark to portfolio starting value
            initial_port_value = perf['total'].iloc[0]
            for col in bench_data.columns:
                bench_data[col] = bench_data[col] * initial_port_value / 100
                
                # Add to chart
                fig_value.add_trace(
                    go.Scatter(
                        x=bench_data.index, 
                        y=bench_data[col],
                        name=col,
                        line=dict(dash='dash')
                    )
                )
                
        st.plotly_chart(fig_value, use_container_width=True)
        
        # Weight deviation over time
        st.subheader("Portfolio Balance")
        if rebalance_period != "N":
            fig_deviation = px.line(
                perf, 
                y="max_weight_deviation",
                labels={"max_weight_deviation": "Max Weight Deviation", "date": "Date"},
                title=f"Maximum Deviation from Target Weights (Rebalanced {rebalance_options[rebalance_period]})"
            )
            st.plotly_chart(fig_deviation, use_container_width=True)
            
        # Asset allocation 
        weights_data = pd.DataFrame({
            'Asset': list(weights.keys()),
            'Target': list(weights.values()),
            'Current': [perf[t].iloc[-1] / perf['total'].iloc[-1] for t in weights]
        })
        
        fig_weights = go.Figure()
        fig_weights.add_trace(go.Bar(
            x=weights_data['Asset'],
            y=weights_data['Target'],
            name='Target',
            marker_color='lightblue'
        ))
        fig_weights.add_trace(go.Bar(
            x=weights_data['Asset'],
            y=weights_data['Current'],
            name='Current',
            marker_color='darkblue'
        ))
        fig_weights.update_layout(
            title="Asset Allocation",
            barmode='group',
            yaxis=dict(
                title='Weight',
                tickformat='.0%'
            )
        )
        st.plotly_chart(fig_weights, use_container_width=True)
    
    with col2:
        # Performance metrics
        st.subheader("Performance Metrics")
        
        metrics_df = pd.DataFrame({
            'Metric': [
                'Total Return',
                'Annual Return',
                'Annual Volatility',
                'Sharpe Ratio',
                'Max Drawdown',
                'Current Value'
            ],
            'Value': [
                format_pct(metrics['total_return']),
                format_pct(metrics['annualized_return']),
                format_pct(metrics['annualized_volatility']),
                f"{metrics['sharpe_ratio']:.2f}",
                format_pct(metrics['max_drawdown']),
                format_currency(perf['total'].iloc[-1])
            ]
        })
        
        st.dataframe(
            metrics_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Show benchmark comparison if selected
        if show_benchmark:
            st.subheader("Benchmark Comparison")
            
            # Use S&P 500 for benchmark comparison if available
            if "^GSPC" in bench_data.columns:
                bench_returns = bench_data["^GSPC"].pct_change().dropna()
                comparison = compare_to_benchmark(returns['daily'], bench_returns)
                
                comp_df = pd.DataFrame({
                    'Metric': [
                        'Beta (vs S&P 500)',
                        'Alpha (annualized)',
                        'Tracking Error',
                        'Information Ratio'
                    ],
                    'Value': [
                        f"{comparison['beta']:.2f}",
                        format_pct(comparison['alpha']),
                        format_pct(comparison['tracking_error']),
                        f"{comparison['information_ratio']:.2f}"
                    ]
                })
                
                st.dataframe(
                    comp_df,
                    use_container_width=True,
                    hide_index=True
                )
        
        # Monthly returns heatmap
        st.subheader("Monthly Returns")
        
        # Convert returns to a pivot table format
        monthly_returns = returns['monthly'] * 100  # Convert to percentage
        monthly_returns_table = pd.DataFrame({
            'Year': monthly_returns.index.year,
            'Month': monthly_returns.index.month,
            'Return': monthly_returns.values
        })
        pivot = monthly_returns_table.pivot(index='Year', columns='Month', values='Return')
        
        # Format the table data
        pivot_formatted = pivot.copy()
        for year in pivot_formatted.index:
            for month in pivot_formatted.columns:
                if not pd.isna(pivot_formatted.loc[year, month]):
                    val = pivot_formatted.loc[year, month]
                    pivot_formatted.loc[year, month] = f"{val:.2f}%"
        
        # Display as a styled table
        st.dataframe(
            pivot_formatted,
            use_container_width=True
        )
    
    # Export data section
    st.subheader("Export Data")
    col1, col2 = st.columns(2)
    
    with col1:
        # Export performance data
        csv_perf = perf.to_csv().encode("utf-8")
        st.download_button(
            label="📥 Download Portfolio Performance CSV",
            data=csv_perf,
            file_name=f"portfolio_performance_{start.strftime('%Y%m%d')}_to_{end.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Export monthly returns
        csv_returns = pivot.to_csv().encode("utf-8")
        st.download_button(
            label="📥 Download Monthly Returns CSV",
            data=csv_returns,
            file_name=f"monthly_returns_{start.strftime('%Y%m%d')}_to_{end.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # Disclaimer
    st.caption(
        "Disclaimer: This tool is for educational purposes only and does not constitute "
        "investment advice. Past performance is not indicative of future results."
    )

if __name__ == "__main__":
    main()

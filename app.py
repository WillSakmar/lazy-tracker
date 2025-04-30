import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

from scripts.fetch_data import fetch_price_data
from scripts.portfolio import (
    simulate_portfolio, 
    calculate_returns, 
    calculate_metrics
)

# Set page configuration
st.set_page_config(
    page_title="Lazy Portfolio Tracker",
    page_icon="📊",
    layout="wide"
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
    # App title and description
    st.title("Lazy Portfolio Tracker")
    st.markdown("""
    A lightweight tool to backtest simple portfolio allocations. Enter your assets, 
    set target weights, and see how your portfolio would have performed.
    """)
    
    # Sidebar for settings
    with st.sidebar:
        st.title("Portfolio Settings")
        
        # Date range
        st.header("Date Range")
        today = datetime.now().date()
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input(
                "Start date", 
                value=datetime(2018, 1, 1).date(),  # Using more recent default start date
                max_value=today - timedelta(days=30)
            )
        with col2:
            end = st.date_input("End date", value=today)
        
        # Portfolio settings
        st.header("Assets")
        
        # Allow user to add/remove tickers
        tickers = st.text_input(
            "Ticker symbols (comma separated)", 
            value="VTI,BND"
        ).upper().replace(" ", "").split(",")
        
        # Use fewer default weights to reduce complexity
        weights = {}
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
            
        # Configuration
        st.header("Configuration")
        initial_cash = st.number_input(
            "Initial investment ($)", 
            min_value=1000,
            max_value=10_000_000,
            value=DEFAULT_INITIAL_CASH,
            step=10000
        )
        
        rebalance_options = {
            "ME": "Monthly",
            "QE": "Quarterly",
            "A": "Annually",
            "N": "Never"
        }
        
        rebalance_period = st.selectbox(
            "Rebalance frequency",
            list(rebalance_options.keys()),
            format_func=lambda k: rebalance_options[k],
            index=1  # Default to quarterly
        )
        
        # Add a refresh data button
        refresh_data = st.button("Refresh Data")
    
    # Main section - check weights first
    if abs(total_weight - 1.0) > 0.05:
        st.error("Portfolio weights must sum to approximately 1.0")
        return
    
    # Get the price data
    with st.spinner("Fetching price data..."):
        try:
            prices = fetch_price_data(
                tickers,
                start,
                end + timedelta(days=1),
                use_cache=not refresh_data
            )
            
            # Check if we have enough data to proceed
            if prices.empty:
                st.error("No price data available. Please check your ticker symbols and try again.")
                return
                
            if len(prices) < 2:
                st.error("Insufficient price data. Need at least 2 dates for analysis.")
                return
                
            # Display warnings for any missing tickers
            missing_tickers = [t for t in tickers if t not in prices.columns]
            if missing_tickers:
                st.warning(f"Data for {', '.join(missing_tickers)} could not be fetched. Analysis will continue with available data.")
            
        except Exception as e:
            st.error(f"Error fetching price data: {str(e)}")
            st.info("Please try again later or use different tickers.")
            return
    
    # Simulate the portfolio
    with st.spinner("Simulating portfolio..."):
        try:
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
        except Exception as e:
            st.error(f"Error in portfolio simulation: {str(e)}")
            st.info("Please try adjusting your settings or using different tickers.")
            return
    
    # Dashboard layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Value over time chart
        st.subheader("Portfolio Value")
        
        # Create a dataframe for plotting with a nicer name for total
        plot_df = perf.copy()
        plot_df = plot_df.rename(columns={"total": "Portfolio Total"})
        
        # Define a color palette for better distinction between lines
        colors = {
            "Portfolio Total": "rgb(54, 162, 235)",  # Blue for portfolio total
            # Define distinct colors for common asset types
            "VTI": "rgb(255, 99, 132)",    # Red
            "BND": "rgb(75, 192, 192)",    # Green
            "VEA": "rgb(153, 102, 255)",   # Purple
            "VWO": "rgb(255, 159, 64)",    # Orange
            "VTEB": "rgb(201, 203, 207)",  # Grey
            "VXUS": "rgb(255, 205, 86)",   # Yellow
        }
        
        # Create a new figure
        fig_value = px.line(
            plot_df, 
            y="Portfolio Total",
            labels={"value": "Value ($)", "date": "Date", "variable": "Asset"},
            title="Portfolio Value Over Time"
        )
        
        # Customize the total portfolio line
        fig_value.update_traces(
            line=dict(width=3),  # Make portfolio line thicker
            name="Portfolio Total"
        )
        
        # Add a line for each individual holding with distinct colors
        for ticker in weights.keys():
            if ticker in plot_df.columns:
                color = colors.get(ticker, None)  # Use predefined color or auto-assign
                fig_value.add_trace(
                    px.line(plot_df, y=ticker).data[0]
                )
                # Update the trace properties separately
                fig_value.data[-1].name = ticker
                fig_value.data[-1].line.width = 1.5
                if color:
                    fig_value.data[-1].line.color = color
        
        # Improve the legend and layout
        fig_value.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis=dict(
                title="Date",
                titlefont=dict(size=12),
                showgrid=True,
                gridcolor='rgba(230, 230, 230, 0.5)'
            ),
            yaxis=dict(
                title="Value ($)",
                titlefont=dict(size=12),
                showgrid=True,
                gridcolor='rgba(230, 230, 230, 0.5)'
            ),
            plot_bgcolor='white',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_value, use_container_width=True)
        
        # Weight deviation over time (only if rebalancing is enabled)
        if rebalance_period != "N":
            st.subheader("Portfolio Balance")
            fig_deviation = px.line(
                perf, 
                y="max_weight_deviation",
                labels={"max_weight_deviation": "Max Weight Deviation", "date": "Date"},
                title=f"Maximum Deviation from Target Weights (Rebalanced {rebalance_options[rebalance_period]})"
            )
            st.plotly_chart(fig_deviation, use_container_width=True)
    
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
        
        # Current allocation
        st.subheader("Current Allocation")
        
        # Calculate current weights
        current_allocation = {}
        for ticker in weights:
            if ticker in perf.columns:
                current_allocation[ticker] = perf[ticker].iloc[-1] / perf['total'].iloc[-1]
            else:
                current_allocation[ticker] = 0
                
        # Create a dataframe for display
        allocation_df = pd.DataFrame({
            'Asset': list(weights.keys()),
            'Target': [weights[t] for t in weights.keys()],
            'Current': [current_allocation[t] for t in weights.keys()]
        })
        
        # Format as percentages
        allocation_df['Target'] = allocation_df['Target'].apply(lambda x: f"{x*100:.1f}%")
        allocation_df['Current'] = allocation_df['Current'].apply(lambda x: f"{x*100:.1f}%")
        
        st.dataframe(
            allocation_df,
            use_container_width=True,
            hide_index=True
        )
    
    # Simplified monthly returns display
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
    
    # Download data (simplify to just one button)
    st.subheader("Export Data")
    csv_perf = perf.to_csv().encode("utf-8")
    st.download_button(
        label="📥 Download Portfolio Performance CSV",
        data=csv_perf,
        file_name=f"portfolio_performance_{start.strftime('%Y%m%d')}_to_{end.strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    # Disclaimer
    st.caption(
        "Disclaimer: This tool is for educational purposes only and does not constitute "
        "investment advice. Past performance is not indicative of future results."
    )

if __name__ == "__main__":
    main()

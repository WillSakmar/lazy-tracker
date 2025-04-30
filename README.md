# Lazy Portfolio Tracker

A lightweight Streamlit application for tracking and backtesting simple portfolio allocations.

## Features

- Backtest a portfolio of assets with custom allocation weights
- Automatic rebalancing at monthly, quarterly, or annual intervals
- Performance metrics calculation (returns, volatility, Sharpe ratio, etc.)
- Interactive charts for portfolio value and allocation tracking
- Monthly returns table
- Simple data exports

## Installation

```bash
# Clone the repository
git clone https://github.com/WillSakmar/lazy-tracker.git
cd lazy-tracker

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

Run the Streamlit app locally:

```bash
streamlit run app.py
```

Or deploy to Streamlit Cloud:

1. Push your repository to GitHub
2. Log in to [Streamlit Cloud](https://streamlit.io/cloud)
3. Create a new app pointing to your repository and app.py file

## Configuration

In the app, you can configure:

- Start and end dates for the backtest
- Asset ticker symbols (e.g., VTI, BND)
- Target allocation weights for each asset
- Initial investment amount
- Rebalancing frequency

## Project Structure

- `app.py` - Main Streamlit application
- `scripts/fetch_data.py` - Functions for fetching price data from Yahoo Finance
- `scripts/portfolio.py` - Portfolio simulation and metrics calculation
- `data/` - Cache directory for financial data (created automatically)

## Data Sources

This tool uses Yahoo Finance (via the yfinance library) to fetch historical price data.

## Cache Management

The application uses cached data to minimize API calls to Yahoo Finance. The cache is stored in the `data/` directory and refreshed weekly.

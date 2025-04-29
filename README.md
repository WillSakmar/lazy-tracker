# Portfolio Dashboard

An interactive Streamlit app for monitoring and analyzing a diversified investment portfolio with customizable asset allocation and rebalancing strategies.

## Features

- **Data Fetching**: Retrieves historical price data for any stock or ETF using Yahoo Finance API
- **Portfolio Simulation**: Simulates portfolio growth with periodic rebalancing to maintain target asset weights
- **Performance Metrics**: Calculates key metrics like returns, volatility, Sharpe ratio, max drawdown, etc.
- **Benchmark Comparison**: Compares portfolio performance against major indices like S&P 500
- **Asset Allocation Visualization**: Shows current vs target allocation with weight deviation tracking
- **Monthly Returns Analysis**: Displays monthly returns in a heatmap table format
- **Data Export**: Export performance and returns data as CSV files for further analysis

## Setup

```bash
git clone https://github.com/willsakmar/lazy-tracker.git
cd lazy-tracker
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Run the app:

```bash
streamlit run app.py
```

Then open your browser to http://localhost:8501

## Portfolio Configuration

- **Assets**: Enter ticker symbols for your desired portfolio assets
- **Weights**: Adjust allocation percentages for each asset
- **Initial Investment**: Set starting cash amount
- **Rebalance Frequency**: Choose monthly, quarterly, annual, or no rebalancing
- **Date Range**: Select historical period for analysis
- **Benchmarks**: Compare your portfolio against market indices

## Data Caching

The app caches fetched price data to improve performance and reduce API calls. To use fresh data, click the "Refresh Data" button in the sidebar.

## GitHub Pages Deployment

You can deploy this dashboard to GitHub Pages in two ways:

### Option 1: Static Site (included in this repo)

Deploy a static version of the dashboard that shows pre-generated portfolio data:

1. Enable GitHub Pages in your repository settings (Settings → Pages)
2. Set the source to the `docs` folder on the `main` branch
3. Run the update script to generate fresh portfolio data:

```bash
./update_gh_pages.sh
```

This will:
- Generate portfolio data JSON files based on default settings
- Commit and push the changes to your GitHub repository
- Update your GitHub Pages site

The dashboard will be available at `https://yourusername.github.io/your-repo-name/`

### Option 2: Streamlit Cloud (Interactive)

For a fully interactive version:

1. Deploy the app to Streamlit Community Cloud (https://share.streamlit.io/)
2. Update the Streamlit URL in `docs/streamlit.html`
3. Visitors to your GitHub Pages site can click "Open Interactive Dashboard" to access the full Streamlit app

## Development

The project structure:
- `app.py` - Main Streamlit application
- `scripts/fetch_data.py` - Data retrieval module using yfinance
- `scripts/portfolio.py` - Portfolio simulation and analysis logic
- `data/` - Directory for cached price data
- `docs/` - Static website for GitHub Pages deployment

## Disclaimer

This application is for educational purposes only and does not constitute investment advice. Past performance is not indicative of future results.

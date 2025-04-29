// Dashboard.js - Loads and displays portfolio data

// Load all data files
async function loadData() {
    try {
        const [portfolio, benchmarks, metrics, monthlyReturns, config] = await Promise.all([
            fetch('./data/portfolio.json').then(res => res.json()),
            fetch('./data/benchmarks.json').then(res => res.json()),
            fetch('./data/metrics.json').then(res => res.json()),
            fetch('./data/monthly_returns.json').then(res => res.json()),
            fetch('./data/config.json').then(res => res.json())
        ]);
        
        return { portfolio, benchmarks, metrics, monthlyReturns, config };
    } catch (error) {
        console.error('Error loading data:', error);
        document.body.innerHTML = `
            <div class="container mt-5 text-center">
                <div class="alert alert-danger">
                    <h3>Error Loading Data</h3>
                    <p>Could not load portfolio data. Please try again later.</p>
                    <p>Error: ${error.message}</p>
                </div>
            </div>
        `;
        return null;
    }
}

// Format percentage values
function formatPercent(value, decimals = 2) {
    return (value * 100).toFixed(decimals) + '%';
}

// Format currency values
function formatCurrency(value, decimals = 2) {
    return '$' + value.toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

// Generate portfolio performance chart
function renderPortfolioChart(portfolio, benchmarks) {
    const ctx = document.getElementById('portfolioChart').getContext('2d');
    
    // Extract dates and values
    const dates = portfolio.map(d => d.date);
    const portfolioValues = portfolio.map(d => d.total);
    
    // Create datasets array with portfolio data
    const datasets = [{
        label: 'Portfolio',
        data: portfolioValues,
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.1
    }];
    
    // Add benchmark datasets if available
    if (benchmarks && benchmarks.length > 0) {
        // Normalize benchmark data to match portfolio starting value
        const startingValue = portfolioValues[0];
        
        if (benchmarks.some(b => b["^GSPC"])) {
            const spValues = benchmarks.map(b => b["^GSPC"] * startingValue / 100);
            datasets.push({
                label: 'S&P 500',
                data: spValues,
                borderColor: 'rgb(255, 99, 132)',
                borderWidth: 2,
                borderDash: [5, 5],
                fill: false,
                tension: 0.1
            });
        }
        
        if (benchmarks.some(b => b["BND"])) {
            const bondValues = benchmarks.map(b => b["BND"] * startingValue / 100);
            datasets.push({
                label: 'Bonds',
                data: bondValues,
                borderColor: 'rgb(75, 192, 192)',
                borderWidth: 2,
                borderDash: [5, 5],
                fill: false,
                tension: 0.1
            });
        }
        
        if (benchmarks.some(b => b["60/40"])) {
            const blendValues = benchmarks.map(b => b["60/40"] * startingValue / 100);
            datasets.push({
                label: '60/40 Blend',
                data: blendValues,
                borderColor: 'rgb(153, 102, 255)',
                borderWidth: 2,
                borderDash: [5, 5],
                fill: false,
                tension: 0.1
            });
        }
    }
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: datasets
        },
        options: {
            responsive: true,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + formatCurrency(context.raw);
                        }
                    }
                },
                legend: {
                    position: 'top',
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'month',
                        displayFormats: {
                            month: 'MMM yyyy'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Date'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Value ($)'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value, 0);
                        }
                    }
                }
            }
        }
    });
}

// Generate asset allocation chart
function renderAllocationChart(portfolio, config) {
    const ctx = document.getElementById('allocationChart').getContext('2d');
    
    // Get latest portfolio values
    const latest = portfolio[portfolio.length - 1];
    
    // Calculate current allocation
    const tickers = config.tickers;
    const currentValues = [];
    const currentPercentages = [];
    
    tickers.forEach(ticker => {
        currentValues.push(latest[ticker]);
        currentPercentages.push(latest[ticker] / latest.total);
    });
    
    // Create pie chart
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: tickers,
            datasets: [{
                data: currentPercentages.map(p => p * 100),
                backgroundColor: [
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(153, 102, 255, 0.8)',
                    'rgba(255, 159, 64, 0.8)',
                    'rgba(255, 205, 86, 0.8)',
                    'rgba(201, 203, 207, 0.8)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const ticker = context.label;
                            const percentage = context.raw.toFixed(2) + '%';
                            const value = formatCurrency(latest[ticker]);
                            return `${ticker}: ${percentage} (${value})`;
                        }
                    }
                }
            }
        }
    });
    
    // Show current allocation details
    const allocationDiv = document.getElementById('currentAllocation');
    let allocationHTML = '<table class="table table-sm">';
    allocationHTML += '<thead><tr><th>Asset</th><th>Value</th><th>Actual</th><th>Target</th></tr></thead><tbody>';
    
    tickers.forEach((ticker, i) => {
        allocationHTML += `<tr>
            <td>${ticker}</td>
            <td>${formatCurrency(latest[ticker])}</td>
            <td>${formatPercent(currentPercentages[i])}</td>
            <td>${formatPercent(config.weights[ticker])}</td>
        </tr>`;
    });
    
    allocationHTML += `<tr class="table-secondary">
        <td><strong>Total</strong></td>
        <td><strong>${formatCurrency(latest.total)}</strong></td>
        <td>100%</td>
        <td>100%</td>
    </tr>`;
    
    allocationHTML += '</tbody></table>';
    allocationDiv.innerHTML = allocationHTML;
}

// Display performance metrics
function renderMetrics(metrics) {
    const metricsTable = document.getElementById('metricsTable');
    const performance = metrics.performance;
    
    // Format metrics
    const metricRows = [
        { name: 'Total Return', value: formatPercent(performance.total_return) },
        { name: 'Annual Return', value: formatPercent(performance.annualized_return) },
        { name: 'Annual Volatility', value: formatPercent(performance.annualized_volatility) },
        { name: 'Sharpe Ratio', value: performance.sharpe_ratio.toFixed(2) },
        { name: 'Sortino Ratio', value: performance.sortino_ratio.toFixed(2) },
        { name: 'Max Drawdown', value: formatPercent(performance.max_drawdown) }
    ];
    
    // Add comparison metrics if available
    if (metrics.comparison && Object.keys(metrics.comparison).length > 0) {
        metricRows.push(
            { name: 'Beta (vs S&P 500)', value: metrics.comparison.beta.toFixed(2) },
            { name: 'Alpha (annual)', value: formatPercent(metrics.comparison.alpha) }
        );
    }
    
    // Create table rows
    let metricsHTML = '';
    metricRows.forEach(metric => {
        metricsHTML += `<tr>
            <td>${metric.name}</td>
            <td class="text-end"><strong>${metric.value}</strong></td>
        </tr>`;
    });
    
    metricsTable.innerHTML = metricsHTML;
}

// Display monthly returns table
function renderMonthlyReturns(monthlyReturns) {
    const tableBody = document.getElementById('monthlyReturnsBody');
    
    // Get years (rows) and months (columns)
    const years = Object.keys(monthlyReturns);
    const months = Array.from({length: 12}, (_, i) => i + 1);
    
    let tableHTML = '';
    
    // For each year
    years.forEach(year => {
        let rowHTML = `<tr><td>${year}</td>`;
        let yearTotal = 1.0;
        
        // For each month
        months.forEach(month => {
            const value = monthlyReturns[year][month];
            
            if (value !== undefined) {
                // Update yearly total
                yearTotal *= (1 + value / 100);
                
                // Format cell with color based on positive/negative
                const cellClass = value >= 0 ? 'text-success' : 'text-danger';
                rowHTML += `<td class="${cellClass}">${value.toFixed(2)}%</td>`;
            } else {
                rowHTML += '<td>-</td>';
            }
        });
        
        // Add YTD column
        const ytdReturn = (yearTotal - 1) * 100;
        const ytdClass = ytdReturn >= 0 ? 'text-success' : 'text-danger';
        rowHTML += `<td class="${ytdClass} fw-bold">${ytdReturn.toFixed(2)}%</td>`;
        
        rowHTML += '</tr>';
        tableHTML += rowHTML;
    });
    
    tableBody.innerHTML = tableHTML;
}

// Display portfolio configuration
function renderPortfolioInfo(config) {
    const infoDiv = document.getElementById('portfolioInfo');
    const lastUpdated = document.getElementById('lastUpdated');
    
    // Create HTML for portfolio config
    let infoHTML = '<div class="row">';
    
    // Assets and weights
    infoHTML += '<div class="col-md-4">';
    infoHTML += '<h4>Assets</h4>';
    infoHTML += '<ul class="list-group">';
    
    config.tickers.forEach(ticker => {
        infoHTML += `<li class="list-group-item d-flex justify-content-between">
            <span>${ticker}</span>
            <span>${formatPercent(config.weights[ticker])}</span>
        </li>`;
    });
    
    infoHTML += '</ul></div>';
    
    // Configuration details
    infoHTML += '<div class="col-md-4">';
    infoHTML += '<h4>Configuration</h4>';
    infoHTML += '<ul class="list-group">';
    
    const rebalanceMap = {
        'M': 'Monthly',
        'Q': 'Quarterly',
        'A': 'Annually',
        'N': 'Never'
    };
    
    infoHTML += `<li class="list-group-item d-flex justify-content-between">
        <span>Initial Investment</span>
        <span>${formatCurrency(config.initial_investment)}</span>
    </li>`;
    
    infoHTML += `<li class="list-group-item d-flex justify-content-between">
        <span>Rebalance Period</span>
        <span>${rebalanceMap[config.rebalance_period] || config.rebalance_period}</span>
    </li>`;
    
    infoHTML += `<li class="list-group-item d-flex justify-content-between">
        <span>Date Range</span>
        <span>${config.start_date} to ${config.end_date}</span>
    </li>`;
    
    infoHTML += '</ul></div>';
    
    // Link to interactive version
    infoHTML += '<div class="col-md-4">';
    infoHTML += '<h4>Interactive Version</h4>';
    infoHTML += '<p>For a fully interactive experience where you can customize your portfolio:</p>';
    infoHTML += '<a href="streamlit.html" class="btn btn-primary">Open Streamlit Dashboard</a>';
    infoHTML += '</div>';
    
    infoHTML += '</div>';
    
    infoDiv.innerHTML = infoHTML;
    lastUpdated.textContent = config.last_updated;
}

// Initialize the dashboard on page load
async function initDashboard() {
    const data = await loadData();
    if (!data) return;
    
    renderPortfolioChart(data.portfolio, data.benchmarks);
    renderAllocationChart(data.portfolio, data.config);
    renderMetrics(data.metrics);
    renderMonthlyReturns(data.monthlyReturns);
    renderPortfolioInfo(data.config);
}

// Start the dashboard
window.addEventListener('DOMContentLoaded', initDashboard); 
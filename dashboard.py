import json
from datetime import datetime
import operator
from collections import defaultdict

def format_currency(amount):
    return f"€{amount:.2f}"

def generate_dashboard_html(data):
    # Process time series data
    spending_by_day = [(datetime.strptime(date, '%Y-%m-%d'), amount) 
                      for date, amount in data['spending_by_day'].items()]
    spending_by_day.sort(key=operator.itemgetter(0))
    
    # Process monthly data
    monthly_spending = defaultdict(float)
    for date, amount in spending_by_day:
        month_key = date.strftime('%Y-%m')
        monthly_spending[month_key] += amount
    
    # Calculate month-over-month change
    months = sorted(monthly_spending.keys())
    if len(months) >= 2:
        current = monthly_spending[months[-1]]
        previous = monthly_spending[months[-2]]
        monthly_change = ((current - previous) / previous * 100) if previous != 0 else 0
    else:
        monthly_change = 0

    # Generate HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shopping Analytics Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {{
            --primary-color: #8884d8;
            --secondary-color: #82ca9d;
            --background-color: #f9fafb;
            --card-background: white;
            --text-primary: #111827;
            --text-secondary: #6b7280;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        }}
        
        body {{
            background-color: var(--background-color);
            padding: 1rem;
        }}
        
        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .dashboard-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }}
        
        .dashboard-title {{
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--text-primary);
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        
        .stat-card {{
            background: var(--card-background);
            padding: 1.5rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .stat-card-title {{
            color: var(--text-secondary);
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
        }}
        
        .stat-card-value {{
            color: var(--text-primary);
            font-size: 1.5rem;
            font-weight: bold;
        }}
        
        .stat-card-trend {{
            color: var(--text-secondary);
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }}
        
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        
        .chart-card {{
            background: var(--card-background);
            padding: 1.5rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .chart-title {{
            font-size: 1.25rem;
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: 1rem;
        }}
        
        .chart {{
            width: 100%;
            height: 400px;
        }}
        
        @media (max-width: 768px) {{
            .chart-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="dashboard-header">
            <h1 class="dashboard-title"><i class="fas fa-chart-line"></i> Shopping Analytics Dashboard</h1>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-card-title"><i class="fas fa-wallet"></i> Total Spending</div>
                <div class="stat-card-value">{format_currency(data['total_spending'])}</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-title"><i class="fas fa-calendar"></i> Monthly Average</div>
                <div class="stat-card-value">{format_currency(data['total_spending'] / len(set([d.strftime('%Y-%m') for d, _ in spending_by_day])))}</div>
                <div class="stat-card-trend">{monthly_change:+.1f}% vs last month</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-title"><i class="fas fa-shopping-cart"></i> Total Transactions</div>
                <div class="stat-card-value">{data['num_transactions']}</div>
                <div class="stat-card-trend">Avg {format_currency(data['average_transaction'])}</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-title"><i class="fas fa-piggy-bank"></i> Total Savings</div>
                <div class="stat-card-value">{format_currency(data['total_bonus_savings'])}</div>
            </div>
        </div>
        
        <div class="chart-grid">
            <div class="chart-card">
                <div class="chart-title"><i class="fas fa-chart-area"></i> Spending Over Time</div>
                <div id="timeSeriesChart" class="chart"></div>
            </div>
            <div class="chart-card">
                <div class="chart-title"><i class="fas fa-tags"></i> Top Categories</div>
                <div id="categoriesChart" class="chart"></div>
            </div>
            <div class="chart-card">
                <div class="chart-title"><i class="fas fa-shopping-basket"></i> Most Purchased Items</div>
                <div id="itemsChart" class="chart"></div>
            </div>
            <div class="chart-card">
                <div class="chart-title"><i class="fas fa-chart-bar"></i> Monthly Spending Trends</div>
                <div id="monthlyChart" class="chart"></div>
            </div>
        </div>
    </div>

    <script>
        // Time Series Chart
        const timeSeriesData = {json.dumps(data['spending_by_day'])};
        const dates = Object.keys(timeSeriesData);
        const amounts = Object.values(timeSeriesData);
        
        Plotly.newPlot('timeSeriesChart', [{{
            "x": dates,
            "y": amounts,
            "type": 'scatter',
            "fill": 'tozeroy',
            "name": 'Daily Spending'
        }}], {{
            "margin": {{ "t": 10 }},
            "yaxis": {{ "title": 'Amount (\u20AC)' }}
        }});
        
        // Categories Chart
        const categoryData = {json.dumps(dict(sorted(data['spending_by_category'].items(), key=lambda x: x[1], reverse=True)[:10]))};
        Plotly.newPlot('categoriesChart', [{{
            "x": Object.keys(categoryData),
            "y": Object.values(categoryData),
            "type": 'bar',
            "marker": {{ "color": '#8884d8' }}
        }}], {{
            "margin": {{ "t": 10 }},
            "yaxis": {{ "title": 'Amount (\u20AC)' }},
            "xaxis": {{ "tickangle": -45 }}
        }});
        
        // Most Bought Items Chart
        const itemsData = {json.dumps(dict(data['most_bought_items']))};
        Plotly.newPlot('itemsChart', [{{
            "x": Object.values(itemsData),
            "y": Object.keys(itemsData),
            "type": 'bar',
            "orientation": 'h',
            "marker": {{ "color": '#82ca9d' }}
        }}], {{
            "margin": {{ "t": 10, "l": 150 }},
            "xaxis": {{ "title": 'Count' }}
        }});
        
        // Monthly Spending Chart
        const monthlyData = {json.dumps(dict(monthly_spending))};
        Plotly.newPlot('monthlyChart', [{{
            "x": Object.keys(monthlyData),
            "y": Object.values(monthlyData),
            "type": 'scatter',
            "name": 'Monthly Spending'
        }}], {{
            "margin": {{ "t": 10 }},
            "yaxis": {{ "title": 'Amount (\u20AC)' }},
            "xaxis": {{ "tickangle": -45 }}
        }});
    </script>
</body>
</html>
"""
    return html

def main():
    # Fix the file path to use underscore
    with open('./analysis_output/analysis_report.json', 'r') as f:
        data = json.load(f)
    
    # Generate the dashboard HTML
    html_content = generate_dashboard_html(data)
    
    # Save the HTML file
    with open('./analysis_output/dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    main()
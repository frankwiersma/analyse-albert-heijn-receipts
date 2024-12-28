# AH Receipt Analyzer 🧾

A Python tool to analyze Albert Heijn receipts, providing insights into your shopping patterns and spending habits.

## 📊 Features

- **Receipt Data Collection**: Automatically fetches receipts from your Albert Heijn account
- **Comprehensive Analysis**: Analyzes spending patterns, most bought items, and bonus savings
- **Interactive Dashboard**: Beautiful visualization of your shopping data including:
  - Daily and monthly spending trends
  - Top spending categories
  - Most frequently purchased items
  - Bonus savings tracking

## 📈 Sample Insights
Based on the analysis of recent data:

- Total transactions: 219
- Average transaction: €15.54
- Total bonus savings: €500.56
- Most bought items:
  1. AVOCADO (31 times)
  2. CHERRYTOMAAT (29 times)
  3. KOMKOMMER (29 times)

## 🚀 Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install requests matplotlib plotly google-generativeai python-dotenv
   ```
3. Set up environment variables:
   - Create a `.env` file with your Google AI API key:
     ```
     GOOGLE_API_KEY=your_api_key_here
     ```

4. Run the analyzer:
   ```bash
   # Fetch new receipts and analyze
   python main.py --fetch

   # Or analyze existing JSON file
   python main.py --process-json path/to/receipts.json
   ```

5. View results:
   - Check `analysis_output/` directory for:
     - `analysis_report.json`: Detailed analysis data
     - `dashboard.html`: Interactive visualization dashboard
     - `other_category_products.txt`: Products needing categorization
     - `daily_spending.png`: Spending trends graph

## 📊 Dashboard Features

The interactive dashboard (`dashboard.html`) includes:
- Total spending overview with month-over-month trends
- Transaction statistics and bonus savings
- Time series chart of daily spending
- Top spending categories visualization
- Most frequently purchased items
- Monthly spending trends

## 🛒 Categories

The analyzer automatically categorizes products into:
- Personal Care
- Cheese
- Milk & Yogurt
- Fruit
- Vegetables
- Meat
- Bread
- And many more...

## 📝 Analysis Details

The tool provides comprehensive insights including:
- Daily and monthly spending patterns
- Category-wise spending breakdown
- Bonus savings tracking
- Transaction frequency analysis
- Product purchase patterns

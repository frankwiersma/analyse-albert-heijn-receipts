import requests
import json
from datetime import datetime
import webbrowser
from typing import List, Dict, Any
from typing_extensions import TypedDict
import argparse
from collections import Counter
import matplotlib.pyplot as plt
from pathlib import Path
import os
import google.generativeai as genai
from dotenv import load_dotenv

class ProductCategory(TypedDict):
    product_name: str 
    category: str

class AHReceiptsFetcher:
    BASE_URL = "https://api.ah.nl"
    USER_AGENT = "Appie/8.22.3"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Content-Type': 'application/json'
        })
        self.access_token = None
        
    def get_anonymous_token(self):
        """Get an anonymous access token"""
        response = self.session.post(
            f"{self.BASE_URL}/mobile-auth/v1/auth/token/anonymous",
            json={"clientId": "appie"}
        )
        response.raise_for_status()
        return response.json()["access_token"]
    
    def get_auth_code(self):
        """Open browser for user login and get authorization code"""
        auth_url = "https://login.ah.nl/secure/oauth/authorize?client_id=appie&redirect_uri=appie://login-exit&response_type=code"
        print(f"Please login in your browser. After login, copy the 'code' parameter from the URL.")
        print(f"The URL will look like 'appie://login-exit?code=YOUR_CODE'")
        webbrowser.open(auth_url)
        
        auth_code = input("Enter the authorization code: ")
        return auth_code
    
    def get_user_token(self, auth_code):
        """Exchange authorization code for user access token"""
        response = self.session.post(
            f"{self.BASE_URL}/mobile-auth/v1/auth/token",
            json={
                "clientId": "appie",
                "code": auth_code
            }
        )
        response.raise_for_status()
        return response.json()
    
    def refresh_token(self, refresh_token):
        """Refresh the access token using a refresh token"""
        response = self.session.post(
            f"{self.BASE_URL}/mobile-auth/v1/auth/token/refresh",
            json={
                "clientId": "appie",
                "refreshToken": refresh_token
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_receipts(self):
        """Get list of receipts"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        response = self.session.get(
            f"{self.BASE_URL}/mobile-services/v1/receipts",
            headers={'Authorization': f'Bearer {self.access_token}'}
        )
        response.raise_for_status()
        return response.json()
    
    def get_receipt_details(self, transaction_id):
        """Get details for a specific receipt"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        response = self.session.get(
            f"{self.BASE_URL}/mobile-services/v2/receipts/{transaction_id}",
            headers={'Authorization': f'Bearer {self.access_token}'}
        )
        response.raise_for_status()
        return response.json()
    
    def authenticate(self):
        """Complete authentication flow"""
        auth_code = self.get_auth_code()
        token_response = self.get_user_token(auth_code)
        self.access_token = token_response["access_token"]
        return token_response

    def fetch_and_save_receipts(self):
        """Fetch receipts and save them to JSON file"""
        receipts = self.get_receipts()
        
        receipt_data = []
        for receipt in receipts:
            date = datetime.fromisoformat(receipt['transactionMoment'].replace('Z', '+00:00'))
            amount = receipt['total']['amount']['amount']
            
            details = self.get_receipt_details(receipt['transactionId'])
            products = [item for item in details['receiptUiItems'] if item['type'] == 'product' and 'amount' in item]
            
            receipt_entry = {
                "date": date.strftime('%Y-%m-%d %H:%M'),
                "amount": f"€{amount:.2f}",
                "products": []
            }
            
            for product in products:
                qty = product.get('quantity', '1')
                desc = product['description']
                product_amount = product['amount']
                receipt_entry["products"].append({
                    "quantity": qty,
                    "description": desc,
                    "amount": f"€{product_amount}"
                })
                
            receipt_data.append(receipt_entry)
        
        with open('ah_receipts.json', 'w', encoding='utf-8') as f:
            json.dump(receipt_data, f, indent=2, ensure_ascii=False)
        
        return 'ah_receipts.json'

class AHReceiptAnalyzer:
    def __init__(self, json_file: str):
        load_dotenv()
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash-8b')
        
        with open(json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.process_data()
    
    def _convert_amount(self, amount_str: str) -> float:
        """Helper method to convert amount strings to float"""
        if not isinstance(amount_str, str):
            return 0.0
        if amount_str == '€None' or amount_str.startswith('€xx'):
            return 0.0
        try:
            cleaned = amount_str.replace('€', '').replace(',', '.')
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0

    def process_data(self):
        """Convert string amounts to float and dates to datetime"""
        for receipt in self.data:
            receipt['amount'] = self._convert_amount(receipt['amount'])
            receipt['date'] = datetime.strptime(receipt['date'], '%Y-%m-%d %H:%M')
            
            for product in receipt['products']:
                product['amount'] = self._convert_amount(product['amount'])
    
    def total_spending(self) -> float:
        """Calculate total spending across all receipts"""
        return sum(receipt['amount'] for receipt in self.data)
    
    def average_transaction(self) -> float:
        """Calculate average transaction amount"""
        return self.total_spending() / len(self.data)
    
    def most_bought_items(self, top_n: int = 10) -> List[tuple]:
        """Get the most frequently bought items"""
        excluded_items = {
            'BONUSKAART', 'PINNEN', 'Waarvan', 'BONUS BOX', 
            'AIRMILES NR. *', 'MIJN AH MILES', 'eSPAARZEGELS', 'eSPAARZEGEL',
            'STATIEGELD', '+STATIEGELD', '-STATIEGELD', 'EMBALLAGE',
            'Prijs per kg', 'BONUS', 'BONUSITEM', 'INCL.HEF.SUP'
        }
        
        items = []
        for receipt in self.data:
            items.extend(product['description'] for product in receipt['products']
                        if product['description'] not in excluded_items 
                        and not product['description'].startswith('BONUS')
                        and product['quantity'] is not None)  # Only include items with non-null quantity
        return Counter(items).most_common(top_n)
    
    def bonus_savings(self) -> float:
        """Calculate total bonus savings"""
        total_bonus = 0
        for receipt in self.data:
            bonus_items = [p['amount'] for p in receipt['products'] 
                         if isinstance(p['quantity'], str) and p['quantity'] == 'BONUS']
            total_bonus += abs(sum(bonus_items))
        return total_bonus
    
    def spending_by_day(self) -> Dict[str, float]:
        """Calculate spending aggregated by day"""
        daily_spending = {}
        for receipt in self.data:
            date_str = receipt['date'].strftime('%Y-%m-%d')
            daily_spending[date_str] = daily_spending.get(date_str, 0) + receipt['amount']
        return daily_spending

    def categorize_products(self) -> Dict[str, float]:
        """Categorize products using Gemini LLM"""
        # Collect all unique product descriptions
        products = set()
        for receipt in self.data:
            for product in receipt['products']:
                # Skip bonus entries, statiegeld, non-product items and items with null quantity
                if (isinstance(product['quantity'], str) and product['quantity'] == 'BONUS' or
                    any(skip in product['description'].upper() for skip in 
                        ['STATIEGELD', 'BONUS', 'PINNEN', 'AIRMILES', 'WAARVAN', 'EMBALLAGE',
                         'DIERENKAART', 'DISNEYSPAREN', 'ESPAARZEL', 'ESPAARZEGELS']) or
                    product['quantity'] is None):  # Skip items with null quantity
                    continue
                products.add(product['description'])
        # Create prompt for Gemini
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            prompt = f.read() + "\n".join(sorted(products))
            
        try:
            # Split products into smaller batches if needed
            MAX_PRODUCTS_PER_BATCH = 50
            products_list = list(products)
            categories_map = {}
            other_products = []  # Track products categorized as OTHER
            
            for i in range(0, len(products_list), MAX_PRODUCTS_PER_BATCH):
                batch = products_list[i:i + MAX_PRODUCTS_PER_BATCH]
                batch_prompt = prompt.replace("\n".join(sorted(products)), "\n".join(batch))
                
                response = self.model.generate_content(
                    batch_prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,
                        candidate_count=1,
                    )
                )
                
                try:
                    # Extract JSON from response
                    response_text = response.text
                    # Find the start and end of the JSON array
                    start_idx = response_text.find('[')
                    end_idx = response_text.rfind(']') + 1
                    
                    if start_idx >= 0 and end_idx > start_idx:
                        json_str = response_text[start_idx:end_idx]
                        batch_categories = json.loads(json_str)
                        
                        # Update categories map and track OTHER products
                        for item in batch_categories:
                            if isinstance(item, dict) and 'product_name' in item and 'category' in item:
                                categories_map[item['product_name']] = item['category']
                                if item['category'] == 'OTHER':
                                    other_products.append(item['product_name'])
                    
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not parse batch {i//MAX_PRODUCTS_PER_BATCH + 1} response: {str(e)}")
                    continue
                
            # Save OTHER category products to a separate file
            output_path = Path('analysis_output')
            output_path.mkdir(exist_ok=True)
            with open(output_path / 'other_category_products.txt', 'w', encoding='utf-8') as f:
                f.write("Products in OTHER category:\n")
                for product in sorted(other_products):
                    f.write(f"- {product}\n")
                
        except Exception as e:
            print(f"Warning: Error processing AI categorization: {str(e)}. Using 'OTHER' as default category.")
            categories_map = {}
        
        # Calculate spending by category
        category_spending = {}
        for receipt in self.data:
            for product in receipt['products']:
                # Skip bonus/action entries, null quantities and ensure amount is valid
                if (isinstance(product['quantity'], str) and (product['quantity'] == 'BONUS' or product['quantity'] == 'ACTIE') or
                    not isinstance(product['amount'], (int, float)) or
                    product['quantity'] is None):  # Skip items with null quantity
                    continue
                category = categories_map.get(product['description'], 'OTHER')
                category_spending[category] = category_spending.get(category, 0) + product['amount']
        
        return category_spending
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive analysis report"""
        report = {
            'total_spending': self.total_spending(),
            'num_transactions': len(self.data),
            'average_transaction': self.average_transaction(),
            'total_bonus_savings': self.bonus_savings(),
            'most_bought_items': self.most_bought_items(),
            'spending_by_day': self.spending_by_day(),
            'spending_by_category': self.categorize_products()
        }
        return report
    
    def save_report(self, output_dir: str = 'analysis_output'):
        """Save analysis results and generate visualizations"""
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Generate and save report
        report = self.generate_report()
        with open(output_path / 'analysis_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        # Create spending by category pie chart
        plt.figure(figsize=(10, 8))
        categories = report.get('spending_by_category', {})
        if not categories:  # Handle empty or None categories
            print("Warning: No category spending data available")
            categories = {}
        
        # Filter out negative values and sort by value
        positive_categories = {k: v for k, v in categories.items() if v > 0}
        
        if positive_categories:  # Only create pie chart if there are positive values
            values = list(positive_categories.values())
            labels = list(positive_categories.keys())
            plt.pie(values, labels=labels, autopct='%1.1f%%')
            plt.title('Spending by Category (Positive Values Only)')
            plt.savefig(output_path / 'category_spending.png')
        else:
            print("Warning: No positive category spending values to create pie chart")
        plt.close()
        
        # Create daily spending line chart
        plt.figure(figsize=(12, 6))
        daily_spending = report.get('spending_by_day', {})
        if daily_spending:
            dates = list(daily_spending.keys())
            amounts = list(daily_spending.values())
            plt.plot(dates, amounts, marker='o')
            plt.xticks(rotation=45)
            plt.title('Daily Spending')
            plt.xlabel('Date')
            plt.ylabel('Amount (€)')
            plt.tight_layout()
            plt.savefig(output_path / 'daily_spending.png')
        else:
            print("Warning: No daily spending data available")
        plt.close()

def main():
    parser = argparse.ArgumentParser(description='AH Receipts Fetcher and Analyzer')
    parser.add_argument('--fetch', action='store_true', help='Fetch new receipts from AH')
    parser.add_argument('--process-json', type=str, help='Process existing JSON file')
    
    args = parser.parse_args()
    
    if args.fetch:
        print("Starting receipt fetching process...")
        fetcher = AHReceiptsFetcher()
        print("Starting authentication process...")
        auth_data = fetcher.authenticate()
        print("Successfully authenticated!")
        
        print("\nFetching receipts...")
        json_file = fetcher.fetch_and_save_receipts()
        print(f"\nReceipts have been saved to {json_file}")
        
        # Automatically analyze the fetched receipts
        print("\nAnalyzing fetched receipts...")
        analyzer = AHReceiptAnalyzer(json_file)
        analyzer.save_report()
    
    if args.process_json:
        print(f"\nAnalyzing receipts from {args.process_json}...")
        analyzer = AHReceiptAnalyzer(args.process_json)
        analyzer.save_report()
        print("\nAnalysis complete! Check the 'analysis_output' directory for results.")
        
        # Print some quick insights
        report = analyzer.generate_report()
        print(f"\nQuick insights:")
        print(f"Total spending: €{report['total_spending']:.2f}")
        print(f"Number of transactions: {report['num_transactions']}")
        print(f"Average transaction: €{report['average_transaction']:.2f}")
        print(f"Total bonus savings: €{report['total_bonus_savings']:.2f}")
        print("\nTop 10 most bought items:")
        for item, count in report['most_bought_items'][:10]:
            print(f"- {item}: {count} times")

if __name__ == "__main__":
    main()
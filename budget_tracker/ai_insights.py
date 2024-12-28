import google.generativeai as genai
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import numpy as np
from functools import lru_cache

# Load environment variables from .env file
load_dotenv()

class AIFinancialInsights:
    def __init__(self, api_key=None):
        """
        Initialize Gemini client for financial insights
        Prioritizes passed API key, then environment variable
        """
        # First, try the passed API key
        if api_key:
            self.api_key = api_key
        else:
            # If no key passed, try getting from environment
            self.api_key = os.getenv('GOOGLE_API_KEY')
        
        # Raise error if no API key is found
        if not self.api_key:
            raise ValueError(
                "Google API key is required. "
                "Set it in .env file as GOOGLE_API_KEY or pass directly to constructor."
            )
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self._cached_insights = {}
    
    @lru_cache(maxsize=32)
    def _get_cached_insights(self, expense_hash):
        """Cache insights based on expense data hash"""
        return self._cached_insights.get(expense_hash)
    
    def analyze_spending_patterns(self, expenses_df):
        """Analyze spending patterns and trends"""
        if expenses_df.empty:
            return {}
            
        expenses_df['date'] = pd.to_datetime(expenses_df['date'])
        
        # Group by year, month, and category with proper column names
        monthly_spending = (expenses_df.groupby([
            expenses_df['date'].dt.year.rename('year'),
            expenses_df['date'].dt.month.rename('month'),
            'category'
        ])['amount'].sum()
        .reset_index())
        
        trends = {
            'total_spent': expenses_df['amount'].sum(),
            'avg_transaction': expenses_df['amount'].mean(),
            'most_expensive_category': expenses_df.groupby('category')['amount'].sum().idxmax(),
            'monthly_spending': monthly_spending.to_dict('records')
        }
        return trends
    
    def suggest_category(self, description):
        """Suggest expense category based on description"""
        prompt = f"""
        Based on this expense description, what would be the most appropriate category?
        Description: {description}
        Categories: Food, Transportation, Housing, Utilities, Entertainment, Other
        
        Reply with just the category name.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            return "Other"

    def generate_spending_insights(self, expenses_df):
        """
        Generate AI-powered insights from expense data with caching
        """
        if expenses_df.empty:
            return "No expenses data available for analysis."
            
        # Create a hash of the expense data for caching
        expense_hash = hash(str(expenses_df.to_dict()))
        
        # Check cache
        cached_result = self._get_cached_insights(expense_hash)
        if cached_result is not None:
            return cached_result
            
        # Generate new insights if not in cache
        insights = self.generate_spending_insights_internal(expense_hash, expenses_df)
        self._cached_insights[expense_hash] = insights
        return insights
    
    def generate_spending_insights_internal(self, expense_hash, expenses_df):
        """Internal method for generating insights"""
        patterns = self.analyze_spending_patterns(expenses_df)
        
        prompt = f"""
        Analyze this financial data and provide detailed insights:
        
        Total Spent: ${patterns['total_spent']:.2f}
        Average Transaction: ${patterns['avg_transaction']:.2f}
        Most Expensive Category: {patterns['most_expensive_category']}
        
        Please provide:
        1. Spending Analysis
        2. Budget Recommendations
        3. Cost-cutting Opportunities
        4. Future Projections
        5. Specific Action Items
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error generating insights: {str(e)}"
            
    def get_budget_alerts(self, expenses_df, budgets_df):
        """Generate budget alerts and warnings"""
        if expenses_df.empty or budgets_df.empty:
            return []
            
        alerts = []
        for _, budget in budgets_df.iterrows():
            category_expenses = expenses_df[
                expenses_df['category'] == budget['category']
            ]['amount'].sum()
            
            usage_percentage = (category_expenses / budget['monthly_limit']) * 100
            if usage_percentage >= 90:
                alerts.append({
                    'category': budget['category'],
                    'severity': 'high',
                    'message': f"Critical: {budget['category']} spending at {usage_percentage:.1f}% of budget"
                })
            elif usage_percentage >= 75:
                alerts.append({
                    'category': budget['category'],
                    'severity': 'medium',
                    'message': f"Warning: {budget['category']} spending at {usage_percentage:.1f}% of budget"
                })
        
        return alerts
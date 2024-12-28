import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from database import ExpenseDatabase
from ai_insights import AIFinancialInsights

class ExpenseTracker:
    def __init__(self):
        """
        Initialize Expense Tracker Streamlit Application
        """
        st.set_page_config(
            page_title="Smart Expense Tracker",
            page_icon="💰",
            layout="wide"
        )
        
        # Initialize database
        self.db = ExpenseDatabase()
        
        # Initialize AI insights
        try:
            self.ai_insights = AIFinancialInsights()
            self.ai_enabled = True
        except ValueError:
            st.warning("Google API key not found. AI features will be limited.")
            self.ai_enabled = False
        
        # Initialize session state
        if 'show_success' not in st.session_state:
            st.session_state.show_success = False
    
    def render_sidebar(self):
        """
        Create sidebar for navigation and budget settings
        """
        st.sidebar.title("💰 Smart Finance")
        menu_options = [
            "Dashboard",
            "Add Expense",
            "View Expenses",
            "Budget Management",
            "AI Insights"
        ]
        return st.sidebar.radio("Navigation", menu_options)
    
    def render_dashboard(self):
        """
        Render main dashboard with key metrics and charts
        """
        st.title("Financial Dashboard")
        
        # Get data for dashboard
        budget_summary = self.db.get_budget_summary()
        spending_trends = self.db.get_spending_trends()
        
        # Display metrics in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_spent = sum(spending_trends.get('monthly_totals', {}).values())
            st.metric("Total Spending", f"${total_spent:,.2f}")
        
        with col2:
            avg_transaction = spending_trends.get('average_transaction', 0)
            st.metric("Average Transaction", f"${avg_transaction:,.2f}")
        
        with col3:
            num_transactions = sum(spending_trends.get('transaction_counts', {}).values())
            st.metric("Total Transactions", num_transactions)
        
        # Create visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Monthly Spending Trends")
            monthly_data = pd.DataFrame(list(spending_trends.get('monthly_totals', {}).items()),
                                      columns=['Month', 'Amount'])
            
            if not monthly_data.empty:
                # Convert Month to datetime for proper sorting
                monthly_data['Month'] = pd.to_datetime(monthly_data['Month'])
                monthly_data = monthly_data.sort_values('Month')
                # Format month for display
                monthly_data['Month'] = monthly_data['Month'].dt.strftime('%b %Y')
                
                fig = px.line(monthly_data, x='Month', y='Amount',
                             title="Monthly Spending",
                             labels={'Amount': 'Amount ($)', 'Month': 'Month'})
                fig.update_layout(
                    xaxis_tickangle=-45,
                    yaxis_title="Amount ($)",
                    showlegend=True,
                    hovermode='x unified'
                )
                # Add markers to the line
                fig.update_traces(mode='lines+markers')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No spending data available for the selected period.")
        
        with col2:
            st.subheader("Category Distribution")
            category_data = pd.DataFrame(list(spending_trends.get('category_trends', {}).items()),
                                       columns=['Category', 'Amount'])
            fig = px.pie(category_data, values='Amount', names='Category',
                        title="Spending by Category")
            st.plotly_chart(fig, use_container_width=True)
        
        # Display budget alerts
        if not budget_summary.empty:
            st.subheader("Budget Alerts")
            for _, row in budget_summary.iterrows():
                # Create a container for each budget category
                with st.container():
                    # Header with category and percentage
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{row['category']}** ({row['usage_percentage']}% used)")
                    with col2:
                        if row['usage_percentage'] >= 90:
                            st.error("⚠️ Critical")
                        elif row['usage_percentage'] >= 75:
                            st.warning("⚠️ Warning")
                        else:
                            st.success("✅ On Track")
                    
                    # Progress bar
                    progress_color = (
                        "red" if row['usage_percentage'] >= 90
                        else "orange" if row['usage_percentage'] >= 75
                        else "green"
                    )
                    st.progress(min(row['usage_percentage'] / 100, 1.0))
                    
                    # Budget details
                    details_col1, details_col2, details_col3 = st.columns(3)
                    with details_col1:
                        st.write(f"Budget: ${row['monthly_limit']:,.2f}")
                    with details_col2:
                        st.write(f"Spent: ${row['current_spend']:,.2f}")
                    with details_col3:
                        if row['remaining'] < 0:
                            st.error(f"Overspent: ${abs(row['remaining']):,.2f}")
                        else:
                            st.write(f"Remaining: ${row['remaining']:,.2f}")
                    
                    st.write(f"Number of transactions: {int(row['transaction_count'])}")
                    st.divider()
        else:
            st.info("No budgets set yet. Go to Budget Management to set up your first budget.")
    
    def add_expense_section(self):
        """
        Section for adding new expenses with AI category suggestion
        """
        st.title("Add New Expense")
        
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                expense_date = st.date_input("Date", datetime.now())
                amount = st.number_input("Amount", min_value=0.0, step=0.1)
            
            with col2:
                description = st.text_input("Description")
                
                # Get AI suggestion for category if enabled
                suggested_category = None
                if self.ai_enabled and description:
                    suggested_category = self.ai_insights.suggest_category(description)
                
                categories = ["Food", "Transportation", "Housing", "Utilities", "Entertainment", "Other"]
                category = st.selectbox("Category", categories,
                                      index=categories.index(suggested_category) if suggested_category in categories else 0)
            
            submitted = st.form_submit_button("Add Expense")
            
            if submitted:
                success = self.db.add_expense(
                    category=category,
                    amount=amount,
                    description=description,
                    date=expense_date.strftime("%Y-%m-%d")
                )
                
                if success:
                    st.success("Expense added successfully!")
                    st.session_state.show_success = True
                else:
                    st.error("Failed to add expense. Please try again.")
    
    def view_expenses_section(self):
        """
        Section for viewing and analyzing expenses
        """
        st.title("Expense History")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date = st.date_input("Start Date", datetime.now().replace(day=1))
        
        with col2:
            end_date = st.date_input("End Date", datetime.now())
        
        with col3:
            categories = ["All"] + ["Food", "Transportation", "Housing", "Utilities", "Entertainment", "Other"]
            selected_category = st.selectbox("Category Filter", categories)
        
        # Get filtered expenses
        category_filter = None if selected_category == "All" else selected_category
        expenses = self.db.get_expenses(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            category_filter
        )
        
        if not expenses.empty:
            # Summary metrics
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Expenses", f"${expenses['amount'].sum():,.2f}")
            
            with col2:
                st.metric("Average Expense", f"${expenses['amount'].mean():,.2f}")
            
            # Display expenses table
            st.dataframe(
                expenses[['date', 'category', 'amount', 'description']],
                use_container_width=True
            )
            
            # Visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                daily_expenses = expenses.groupby('date')['amount'].sum().reset_index()
                fig = px.line(daily_expenses, x='date', y='amount',
                            title="Daily Spending Trend")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                category_expenses = expenses.groupby('category')['amount'].sum().reset_index()
                fig = px.pie(category_expenses, values='amount', names='category',
                            title="Spending Distribution")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expenses found for the selected period.")
    
    def budget_management_section(self):
        st.title("Budget Management")
        
        if 'budget_error' not in st.session_state:
            st.session_state.budget_error = None
        if 'budget_success' not in st.session_state:
            st.session_state.budget_success = None
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Set Monthly Budgets")
            
            if st.session_state.budget_error:
                st.error(st.session_state.budget_error)
                st.session_state.budget_error = None
            if st.session_state.budget_success:
                st.success(st.session_state.budget_success)
                st.session_state.budget_success = None
            
            with st.form("budget_form", clear_on_submit=True):
                categories = ["Food", "Transportation", "Housing", "Utilities", "Entertainment", "Other"]
                category = st.selectbox(
                    "Category",
                    categories,
                    help="Select the spending category for this budget"
                )
                
                monthly_limit = st.number_input(
                    "Monthly Budget",
                    min_value=0.0,
                    value=0.0,  # Changed from current_budget
                    step=1.0,   # Changed step to 1 for more precise input
                    format="%.2f"  # Ensure 2 decimal places
                )
                
                

                submitted = st.form_submit_button("Save Budget", use_container_width=True)
                
                if submitted:
                    try:
                        if monthly_limit <= 0:
                            st.session_state.budget_error = "Budget amount must be greater than zero."
                            st.rerun()
                        else:
                            # Additional debug print
                            print(f"Attempting to set budget - Category: {category}, Limit: {monthly_limit}")
                            
                            if self.db.set_budget(category, monthly_limit):
                                st.session_state.budget_success = f"Budget for {category} set to ${monthly_limit:,.2f}"
                                st.rerun()
                            else:
                                st.session_state.budget_error = f"Failed to set budget for {category}. Please try again."
                                st.rerun()
                    except Exception as e:
                        st.session_state.budget_error = f"Error setting budget: {str(e)}"
                        st.rerun()
    
    def ai_insights_section(self):
        """
        Section for AI-powered financial insights
        """
        st.title("AI Financial Insights")
        
        if self.ai_enabled:
            expenses = self.db.get_expenses()
            
            if not expenses.empty:
                with st.spinner("Generating AI insights..."):
                    insights = self.ai_insights.generate_spending_insights(expenses)
                    st.write(insights)
                
                # Get and display budget alerts
                budget_summary = self.db.get_budget_summary()
                alerts = self.ai_insights.get_budget_alerts(expenses, budget_summary)
                
                if alerts:
                    st.subheader("Budget Alerts")
                    for alert in alerts:
                        if alert['severity'] == 'high':
                            st.error(alert['message'])
                        else:
                            st.warning(alert['message'])
            else:
                st.info("Add some expenses to generate AI insights.")
        else:
            st.warning("AI insights require a Google API key.")
    
    def run(self):
        """
        Main application runner
        """
        selected_section = self.render_sidebar()
        
        if selected_section == "Dashboard":
            self.render_dashboard()
        elif selected_section == "Add Expense":
            self.add_expense_section()
        elif selected_section == "View Expenses":
            self.view_expenses_section()
        elif selected_section == "Budget Management":
            self.budget_management_section()
        elif selected_section == "AI Insights":
            self.ai_insights_section()

def main():
    tracker = ExpenseTracker()
    tracker.run()

if __name__ == "__main__":
    main()
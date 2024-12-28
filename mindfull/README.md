# Smart Expense Tracker

## Overview
The Smart Expense Tracker is a web application built using Streamlit that helps users manage their finances by tracking expenses, setting budgets, and providing insights into spending habits. The application integrates AI features to suggest categories for expenses and generate financial insights.

## Features
- **Dashboard**: View key financial metrics and visualizations of spending trends.
- **Add Expense**: Input new expenses with optional AI category suggestions.
- **View Expenses**: Analyze past expenses with filtering options.
- **Budget Management**: Set and manage monthly budgets for different categories.
- **AI Insights**: Generate insights and alerts based on spending patterns and budget usage.

## Installation
To run the Smart Expense Tracker, follow these steps:

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the database and AI insights configurations as needed.

4. Run the application:
   ```bash
   streamlit run budget_tracker/main.py
   ```

## Input
The application accepts the following inputs:

- **Add Expense Section**:
  - **Date**: Date of the expense (default is the current date).
  - **Amount**: Amount spent (must be a positive number).
  - **Description**: A brief description of the expense.
  - **Category**: Category of the expense (suggested by AI if enabled).

- **Budget Management Section**:
  - **Category**: Category for which the budget is being set.
  - **Monthly Budget**: The limit for spending in the selected category (must be greater than zero).

## Output
The application provides the following outputs:

- **Dashboard**:
  - Total Spending
  - Average Transaction Amount
  - Total Number of Transactions
  - Monthly Spending Trends (line chart)
  - Spending by Category (pie chart)
  - Budget Alerts with progress bars indicating budget usage.

- **View Expenses Section**:
  - Total Expenses for the selected period.
  - Average Expense for the selected period.
  - Detailed table of expenses including date, category, amount, and description.
  - Daily Spending Trend (line chart).
  - Spending Distribution by Category (pie chart).

- **AI Insights Section**:
  - AI-generated insights based on spending data.
  - Budget alerts based on spending patterns.

## Usage
1. Navigate through the sidebar to select different sections of the application.
2. Use the "Add Expense" section to input new expenses.
3. View your spending history and analyze it in the "View Expenses" section.
4. Set monthly budgets in the "Budget Management" section.
5. Access AI insights to understand your financial habits better.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
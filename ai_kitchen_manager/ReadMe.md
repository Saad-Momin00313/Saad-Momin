# AI Kitchen Inventory Manager

## Project Description

The AI Kitchen Inventory Manager is a web application built using Streamlit that helps users manage their kitchen inventory efficiently. It leverages AI to estimate the value of inventory items based on current market prices, provides recommendations, and tracks expiration dates. The application allows users to visualize their inventory status, including low stock and expiring items, and offers insights into the overall health and sustainability of their kitchen inventory.

## Features

- **Inventory Management**: Add, view, and manage kitchen inventory items.
- **AI Price Estimation**: Uses AI to estimate the market value of items based on quantity and category.
- **Expiration Tracking**: Monitors expiration dates and alerts users about items that are expiring soon.
- **Meal Planning**: Suggests meal ideas based on available ingredients in the inventory.
- **Shopping Recommendations**: Provides a shopping list of items needed to prepare suggested meals or to replenish low stock items.
- **Data Visualization**: Provides visual insights into inventory status, including charts for category distribution and stock levels.
- **Clear Database**: Option to clear the entire inventory database.

## Inputs

The application accepts the following inputs for each inventory item:

- **name**: The name of the inventory item (string).
- **quantity**: The quantity of the item (float).
- **unit**: The unit of measurement (e.g., kg, liters, units) (string).
- **category**: The category of the item (e.g., dairy, meat, vegetables) (string).
- **expiration_date**: The expiration date of the item (datetime).
- **created_at**: The timestamp when the item was added to the inventory (datetime).
- **updated_at**: The timestamp when the item was last updated (datetime).

## Outputs

The application generates the following outputs:

- **Estimated Price**: The estimated market price for each item based on AI analysis.
- **Total Inventory Value**: The total value of all items in the inventory.
- **Health Score**: A score representing the nutritional balance of the inventory (0-100).
- **Sustainability Score**: A score representing the environmental impact of the inventory (0-100).
- **Inventory Summary**: A detailed summary of the inventory, including:
  - Total items
  - Categories
  - Low stock items
  - Expiring items
- **Meal Planning Suggestions**: Recommended meal ideas based on the ingredients available in the inventory.
- **Shopping Recommendations**: A list of items needed to prepare suggested meals or to restock low inventory items.
- **Visualizations**: Charts displaying category distribution and stock levels.

## Usage

1. **Installation**: Clone the repository and install the required dependencies.
   ```bash
   git clone <repository-url>
   cd ai_kitchen_manager
   pip install -r requirements.txt
   ```

2. **Run the Application**: Start the Streamlit application.
   ```bash
   streamlit run main.py
   ```

3. **Interact with the Application**: Open your web browser and navigate to `http://localhost:8501` to access the application. You can add items to your inventory, view the dashboard, and analyze your kitchen inventory.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.

## Acknowledgments

- [Streamlit](https://streamlit.io/) for the web framework.
- [SQLAlchemy](https://www.sqlalchemy.org/) for database management.
- [Pandas](https://pandas.pydata.org/) for data manipulation and analysis.
- [Logging](https://docs.python.org/3/library/logging.html) for error tracking and debugging.

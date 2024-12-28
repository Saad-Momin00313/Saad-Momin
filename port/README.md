# Portfolio Management Application

## Overview
This application is a Streamlit-based portfolio management assistant that provides users with tools to track their investments, analyze financial data, and receive AI-powered insights. It integrates various financial data sources, including stock and cryptocurrency prices, and offers technical analysis and risk assessment features.

## Features
- **Portfolio Dashboard**: View the overall performance of your portfolio.
- **Add Asset**: Add new assets to your portfolio, including stocks, ETFs, cryptocurrencies, and more.
- **Asset Analysis**: Analyze individual assets with technical indicators and historical data.
- **AI Insights**: Get AI-driven investment insights and predictions.
- **Risk Analysis**: Assess the risk associated with your portfolio and individual assets.

## Installation
To run this application, ensure you have Python installed along with the required libraries. You can install the necessary packages using pip:

bash
pip install streamlit yfinance pandas plotly requests ta numpy


## Configuration
Before running the application, ensure you have a configuration file (`config/config.py`) that includes necessary API keys and settings.

## Input
The application accepts the following inputs:
- **Asset Symbol**: The ticker symbol of the asset (e.g., AAPL for Apple).
- **Asset Type**: The type of asset (e.g., Stock, ETF, Crypto).
- **Quantity**: The number of units of the asset.
- **Purchase Price**: The price at which the asset was purchased.

## Output
The application provides the following outputs:
- **Portfolio Summary**: Total value of the portfolio and individual asset performance.
- **Technical Indicators**: RSI, SMA, MACD, and other indicators for assets.
- **Risk Metrics**: Beta, Alpha, Sharpe Ratio, and Sortino Ratio for assessing risk.
- **AI Insights**: Predictions and recommendations based on AI analysis.

## Running the Application
To run the application, execute the following command in your terminal:

bash
streamlit run port/src/main.py


## Usage
1. Open the application in your web browser.
2. Use the sidebar to navigate between different sections.
3. Add assets to your portfolio and view their performance.
4. Analyze assets using technical indicators and receive AI insights.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.

## Acknowledgments
- [Streamlit](https://streamlit.io/)
- [yfinance](https://pypi.org/project/yfinance/)
- [Plotly](https://plotly.com/python/)
- [Technical Analysis Library in Python (ta)](https://github.com/bukosabino/ta)


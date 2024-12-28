# Dynamic Customer Churn Predictor

A flexible Streamlit application that utilizes Google's Gemini AI to analyze customer churn patterns in any dataset structure.

## Features

- Dynamic data loading and column analysis
- Automatic feature type detection
- AI-powered insights using Google's Gemini AI
- Interactive visualizations
- Flexible data preprocessing
- Works with any CSV dataset structure

## Inputs

- **CSV File**: The application accepts any CSV file containing customer data. The CSV can include various data types such as:
  - Numeric
  - Categorical
  - Dates
  - Text

### Example Input Structure
```csv
customer_id,age,income,signup_date,churn
1,25,50000,2021-01-15,0
2,30,60000,2020-05-20,1
3,22,45000,2022-03-10,0
```

## Outputs

- **Column Type Analysis**: The application automatically detects and categorizes the types of columns in the dataset (e.g., numeric, categorical, date, text).
- **AI Insights**: Generates comprehensive insights regarding customer churn, including:
  - Churn risk dynamics
  - Strategic recommendations for retention
  - Predictive insights on future churn trends
  - Business impact analysis
- **Visualizations**: Provides interactive visualizations of the top predictive features influencing churn.

## Setup

1. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root and add your Google API key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

3. Run the application:
   ```bash
   streamlit run main.py
   ```

## Usage

1. Launch the application using the command above.
2. Upload any CSV file containing customer data.
3. The app will automatically analyze the column types and structure.
4. Use the interactive interface to:
   - View column categorization
   - Generate AI insights
   - Create dynamic visualizations
   - Analyze patterns and correlations

## Data Requirements

- The application accepts any CSV file.
- No specific column names are required.
- Supports various data types:
  - Numeric
  - Categorical
  - Dates
  - Text

## Security Note

- Never commit your `.env` file containing the API key.
- Keep your API keys secure and rotate them regularly.
- Follow best practices for data privacy and security.

## Contributing

Feel free to submit issues and enhancement requests!
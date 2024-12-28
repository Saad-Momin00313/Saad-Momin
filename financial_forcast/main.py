import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime, timedelta
import yfinance as yf
import json
from dotenv import load_dotenv
import os

# Machine Learning and Advanced Analytics
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

# Load environment variables
load_dotenv()

# Initialize Gemini AI client
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')

def calculate_risk_metrics(financial_data):
    """
    Advanced risk calculation module
    """
    # Check for NaN values and drop them
    if financial_data['Close'].isnull().any():
        financial_data = financial_data.dropna(subset=['Close'])

    returns = financial_data['Close'].pct_change().dropna()  # Drop NaN returns
    
    # Ensure returns are not empty
    if returns.empty:
        return {
            'value_at_risk': None,
            'conditional_var': None,
            'sharpe_ratio': None,
            'max_drawdown': None
        }

    risk_metrics = {
        'value_at_risk': np.percentile(returns, 5),  # 5% VaR
        'conditional_var': returns[returns <= np.percentile(returns, 5)].mean(),
        'sharpe_ratio': calculate_sharpe_ratio(returns),
        'max_drawdown': calculate_max_drawdown(financial_data['Close'])
    }
    
    return risk_metrics

def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """
    Calculate Sharpe Ratio with adjustable risk-free rate
    """
    excess_returns = returns - (risk_free_rate / 252)  # Annualized risk-free rate
    return np.sqrt(252) * excess_returns.mean() / excess_returns.std()

def calculate_max_drawdown(prices):
    """
    Calculate maximum portfolio drawdown
    """
    cumulative = (1 + prices.pct_change()).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return drawdown.min()

def calculate_rsi(prices, periods=14):
    """
    Calculate Relative Strength Index (RSI)
    """
    delta = prices.diff()
    
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def ml_enhanced_prediction(financial_data):
    """
    Machine Learning enhanced prediction model using XGBoost
    Updated to handle feature consistency and data validation
    """
    # Validate input data
    if financial_data is None or financial_data.empty:
        raise ValueError("Input financial data is empty")

    # Ensure we have the necessary columns
    required_columns = pd.Index(['Close', 'Volume'])  # Convert to Index
    if not all(col in financial_data.columns for col in required_columns):
        raise ValueError(f"DataFrame must contain the following columns: {required_columns}")
    
    # Ensure we have enough data points for feature engineering
    if len(financial_data) < 50:  # Need at least 50 points for MA_50
        raise ValueError("Insufficient data points. Need at least 50 data points for feature engineering")

    # Feature engineering with robust handling
    features = pd.DataFrame({
        'Close': financial_data['Close'],
        'MA_10': financial_data['Close'].rolling(window=10, min_periods=1).mean(),
        'MA_50': financial_data['Close'].rolling(window=50, min_periods=1).mean(),
        'RSI': calculate_rsi(financial_data['Close']),
        'Volume': financial_data['Volume'].fillna(method='ffill')  # Forward fill any missing volume data
    })
    
    # Drop any remaining NaN values and validate
    features = features.dropna()
    if len(features) == 0:
        raise ValueError("No valid data points after feature engineering")
    
    # Prepare data
    X = features[['MA_10', 'MA_50', 'RSI', 'Volume']]
    y = features['Close']
    
    # Ensure we have enough data for training
    if len(X) < 10:  # Minimum threshold for meaningful training
        raise ValueError("Insufficient data points after preprocessing")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale features with error handling
    try:
        scaler = MinMaxScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
    except ValueError as e:
        raise ValueError(f"Error during feature scaling: {str(e)}")
    
    # Train XGBoost model
    try:
        xgb_model = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42)
        xgb_model.fit(X_train_scaled, y_train)
    except Exception as e:
        raise ValueError(f"Error during model training: {str(e)}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': xgb_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return {
        'model': xgb_model,
        'feature_importance': feature_importance,
        'scaler': scaler,
        'feature_columns': X.columns.tolist(),
        'data_points': len(features)  # Add information about the number of valid data points
    }

def portfolio_correlation_analysis(symbols):
    """
    Advanced portfolio correlation and diversification analysis
    """
    try:
        # Download data for multiple assets
        portfolio_data = {symbol: yf.download(symbol, period='1y')['Close'] for symbol in symbols}
        portfolio_df = pd.DataFrame(portfolio_data)
        
        # Calculate correlation matrix
        correlation_matrix = portfolio_df.pct_change().corr()
        
        # Compute portfolio statistics
        portfolio_stats = {
            'correlation_matrix': correlation_matrix.to_dict(),
            'portfolio_volatility': portfolio_df.pct_change().std(),
            'diversification_score': 1 - correlation_matrix.values.mean(),  # Higher is better
        }
        
        return portfolio_stats
    except Exception as e:
        st.error(f"Portfolio analysis error: {str(e)}")
        return None

def validate_prediction(prediction_dict):
    """
    Validate the structure of the AI prediction with enhanced checks
    """
    required_keys = ['trend', 'factors', 'risks', 'opportunities', 'forecast']
    for key in required_keys:
        if key not in prediction_dict:
            raise KeyError(f"Missing required key: {key}")
    
    # Validate forecast values are numeric
    if not isinstance(prediction_dict['forecast'], dict):
        raise ValueError("Forecast must be a dictionary")
    
    forecast_keys = ['month1', 'month2', 'month3']
    for key in forecast_keys:
        if key not in prediction_dict['forecast']:
            raise ValueError(f"Missing forecast key: {key}")
        if not isinstance(prediction_dict['forecast'][key], (int, float)):
            raise ValueError(f"Forecast value for {key} must be numeric")
    
    # Validate arrays
    array_keys = ['factors', 'risks', 'opportunities']
    for key in array_keys:
        if not isinstance(prediction_dict[key], list):
            raise ValueError(f"{key} must be an array")
        if not all(isinstance(item, str) for item in prediction_dict[key]):
            raise ValueError(f"All items in {key} must be strings")
    
    return True

def get_asset_type(symbol):
    """
    Determine the type of financial asset with expanded mappings
    """
    asset_type_mappings = {
        # Cryptocurrencies
        'BTC': 'Cryptocurrency', 'ETH': 'Cryptocurrency', 
        'DOGE': 'Cryptocurrency', 'BNB': 'Cryptocurrency',
        
        # Indices
        '^DJI': 'Stock Index', '^IXIC': 'Stock Index', 
        '^GSPC': 'Stock Index', '^NYA': 'Stock Index',
        
        # ETFs
        'SPY': 'ETF', 'QQQ': 'ETF', 'VTI': 'ETF',
        
        # Commodities
        'GC=F': 'Commodity', 'CL=F': 'Commodity',
        
        # Currencies
        '^DX': 'Currency Index',
        
        # Default
        'default': 'Stock'
    }
    
    return asset_type_mappings.get(symbol, asset_type_mappings['default'])

def get_ai_prediction(financial_data_df, context, asset_type):
    """
    Enhanced AI predictions with more robust error handling and context
    """
    # Ensure we're working with a DataFrame
    if isinstance(financial_data_df, dict):
        # If dict contains series or arrays, convert properly
        financial_data_df = pd.DataFrame.from_dict(financial_data_df)
    elif isinstance(financial_data_df, np.ndarray):
        # Ensure proper column assignment for numpy arrays
        if financial_data_df.ndim == 1:
            financial_data_df = pd.DataFrame(financial_data_df.reshape(-1, 1), columns=['Close'])
        else:
            cols = ['Close', 'Volume'][:financial_data_df.shape[1]]
            financial_data_df = pd.DataFrame(financial_data_df, columns=cols)
    elif isinstance(financial_data_df, pd.Series):
        financial_data_df = financial_data_df.to_frame(name='Close')
    elif not isinstance(financial_data_df, pd.DataFrame):
        raise TypeError("financial_data_df must be a DataFrame, Series, dict, or numpy array")
    
    # Ensure required columns exist
    required_columns = pd.Index(['Close'])  # Convert to Index
    if not all(col in financial_data_df.columns for col in required_columns):
        raise ValueError(f"DataFrame must contain the following columns: {required_columns}")
    
    # Filter to include only relevant columns for prediction, handling missing Volume column
    if 'Volume' in financial_data_df.columns:
        financial_data_df = financial_data_df[['Close', 'Volume']]
    else:
        financial_data_df = financial_data_df[['Close']]
    
    # Advanced data summary
    summary = {
        'latest_close': financial_data_df['Close'].iloc[-1],
        'avg_price': financial_data_df['Close'].mean(),
        'price_change': (financial_data_df['Close'].iloc[-1] - financial_data_df['Close'].iloc[0]) / financial_data_df['Close'].iloc[0],
        'volatility': financial_data_df['Close'].std(),
        'volume': financial_data_df['Volume'].mean() if 'Volume' in financial_data_df else None,
        'price_7d': financial_data_df['Close'].tail(7).tolist(),
        'rsi': calculate_rsi(financial_data_df['Close']).iloc[-1]
    }
    
    # Asset-specific prompt customization
    asset_specific_prompt = f"""
    Advanced Analysis for {asset_type}:
    - Provide nuanced, multi-factor insights
    - Consider macroeconomic trends
    - Highlight potential disruptive factors
    """
    
    prompt = f"""
    Return a JSON object (without backticks, markdown formatting, or any other decorators) following this structure:
    {{
        "trend": "string describing the trend",
        "factors": ["factor1", "factor2", "factor3"],
        "risks": ["risk1", "risk2", "risk3"],
        "opportunities": ["opportunity1", "opportunity2", "opportunity3"],
        "forecast": {{
            "month1": 0.0,
            "month2": 0.0,
            "month3": 0.0
        }}
    }}

    Financial Data:
    - Latest Close: ${summary['latest_close']:.2f}
    - Price Volatility: {summary['volatility']:.2f}
    - 7-Day Price Trend: {summary['price_7d']}
    - RSI: {summary['rsi']:.2f}
    
    {asset_specific_prompt}
    Context: {context}
    
    Important: 
    1. Return ONLY the JSON object
    2. Use numeric values for forecasts (no currency symbols or quotes around numbers)
    3. Do not include any markdown formatting, backticks, or decorators
    """
    
    try:
        completion = model.generate_content(prompt)
        response_content = completion.text
        
        # Clean the response
        response_content = response_content.strip()
        if response_content.startswith('```'):
            response_content = response_content.split('```')[1]
        if response_content.endswith('```'):
            response_content = response_content.rsplit('```', 1)[0]
        response_content = response_content.strip()
        
        # Parsing and validation
        try:
            prediction_dict = json.loads(response_content)
            validate_prediction(prediction_dict)
            return json.dumps(prediction_dict)
        except (json.JSONDecodeError, KeyError, ValueError) as json_err:
            st.error(f"Invalid JSON or prediction format: {json_err}")
            st.error(f"Problematic Response: {response_content}")
            return None
        
    except Exception as e:
        st.error(f"Error getting AI prediction: {str(e)}")
        return None

def load_financial_data(symbol, period='2y', asset_type=None):
    """
    Enhanced financial data loading with additional error handling
    """
    try:
        # Advanced download with more parameters
        data = yf.download(
            symbol, 
            period=period, 
            interval='1d',  # Daily data
            progress=False  # Suppress progress bar
        )
        
        if data.empty:
            st.error(f"No data found for symbol: {symbol}")
            return None
        
        return data
    except Exception as e:
        st.error(f"Comprehensive error loading financial data for {symbol}: {str(e)}")
        return None

def create_advanced_forecast_plot(historical_data, forecast_data, symbol, asset_type, ml_model=None):
    """
    Create an advanced interactive plot with multiple data layers
    """
    # Prepare historical data
    historical_df = pd.DataFrame(historical_data)
    
    # Rename columns to handle different data sources
    historical_columns = list(historical_df.columns)
    if 'Close' not in historical_columns and len(historical_columns) > 0:
        historical_df.columns = ['Close'] + historical_columns[1:]
    
    # Create figure with multiple traces
    title = f"Advanced {symbol} {asset_type} Forecast"
    fig = px.line(title=title)
    
    # Historical price
    fig.add_scatter(x=historical_df.index, y=historical_df['Close'], 
                    name='Historical Price', line=dict(color='blue'))
    
    # Forecast trace
    forecast_values = forecast_data.iloc[:, 0]  # Take first column
    fig.add_scatter(x=forecast_data.index, y=forecast_values,
                    name='Forecast', line=dict(dash='dash', color='red'))
    
    # Optional ML prediction confidence interval
    if ml_model is not None:
        # Placeholder for ML model confidence interval
        pass
    
    # Customize layout with advanced options
    fig.update_layout(
        xaxis_title='Date',
        yaxis_title='Price',
        legend_title='Price Trend',
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig

def plot_risk_metrics(sharpe_ratio, value_at_risk):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=['Sharpe Ratio', 'Value at Risk'], y=[sharpe_ratio, value_at_risk],
                         marker_color=['blue', 'red']))
    fig.update_layout(title='Risk Metrics',
                      xaxis_title='Metrics',
                      yaxis_title='Values',
                      template='plotly_white')
    return fig

def generate_forecast(model, scaler, last_data, forecast_period=30):
    """
    Generate future price forecasts using the trained model
    Updated to handle feature consistency and prevent scaling errors
    """
    try:
        # Validate input data
        if last_data is None or len(last_data) < 50:
            raise ValueError("Insufficient data for forecasting. Need at least 50 data points.")
            
        # Prepare feature data with the exact columns used in training
        feature_data = pd.DataFrame({
            'MA_10': last_data['Close'].rolling(window=10, min_periods=1).mean(),
            'MA_50': last_data['Close'].rolling(window=50, min_periods=1).mean(),
            'RSI': calculate_rsi(last_data['Close']),
            'Volume': last_data['Volume'].fillna(method='ffill')  # Forward fill missing values
        })
        
        # Drop any remaining NaN values
        feature_data = feature_data.dropna()
        if len(feature_data) == 0:
            raise ValueError("No valid data points after feature engineering")
            
        # Get the last complete row of features
        last_features = feature_data.iloc[-1:]
        
        if last_features.empty:
            raise ValueError("Could not get valid features for prediction")
            
        # Scale the features
        try:
            last_features_scaled = scaler.transform(last_features)
        except ValueError as e:
            raise ValueError(f"Error scaling features: {str(e)}")
        
        # Generate predictions
        predictions = []
        current_features = last_features.copy()
        
        for _ in range(forecast_period):
            # Make prediction
            try:
                current_scaled = scaler.transform(current_features)
                pred = model.predict(current_scaled)
                predictions.append(pred[0])
                
                # Update features for next prediction (simplified)
                new_features = pd.DataFrame({
                    'MA_10': [pred[0]],
                    'MA_50': current_features['MA_50'].iloc[-1],
                    'RSI': current_features['RSI'].iloc[-1],
                    'Volume': current_features['Volume'].iloc[-1]
                })
                current_features = new_features
                
            except Exception as e:
                raise ValueError(f"Error during prediction iteration: {str(e)}")
        
        # Create forecast dates
        forecast_dates = pd.date_range(
            start=last_data.index[-1] + pd.Timedelta(days=1),
            periods=forecast_period,
            freq='B'  # Business days
        )
        
        return pd.Series(predictions, index=forecast_dates)
        
    except Exception as e:
        logger.error(f"Forecast generation error: {str(e)}")
        raise

def main():
    st.set_page_config(
        page_title="Financial Market Analysis Platform",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("Financial Market Analysis Platform")
    
    # Configuration sidebar
    st.sidebar.header("Analysis Configuration")
    
    # Multi-asset support
    symbols = st.sidebar.text_input(
        "Trading Symbols", 
        value="AAPL", 
        help="Enter stock tickers or cryptocurrency symbols (comma-separated)"
    )
    
    # Split symbols
    symbol_list = [sym.strip() for sym in symbols.split(',')]
    
    # Period and analysis depth
    period = st.sidebar.selectbox(
        "Analysis Timeframe",
        ["6mo", "1y", "2y", "5y"],
        index=1,
        help="Select historical data timeframe for analysis"
    )
    
    # Contextual input for more nuanced predictions
    context = st.sidebar.text_area(
        "Market Context",
        "Enter relevant market conditions, news, or economic factors that may impact the analysis.",
        height=100
    )
    
    # Advanced analysis toggle
    advanced_analysis = st.sidebar.checkbox("Enable Advanced Analytics", value=True)
    
    if st.sidebar.button("Generate Analysis"):
        # Results container
        results_container = st.container()
        
        with results_container:
            # Portfolio-level analysis
            if len(symbol_list) > 1:
                st.subheader("Portfolio Correlation Analysis")
                portfolio_stats = portfolio_correlation_analysis(symbol_list)
                
                if portfolio_stats:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Portfolio Diversification Score", 
                                  f"{portfolio_stats['diversification_score']:.2%}")
                    with col2:
                        st.json(json.dumps(portfolio_stats, indent=2))
            
            # Individual asset analysis
            for symbol in symbol_list:
                # Detect asset type
                asset_type = get_asset_type(symbol)
                
                st.header(f"Market Analysis: {symbol} ({asset_type})")
                
                # Load financial data
                data = load_financial_data(symbol, period, asset_type)
                
                if data is not None:
                    st.write("Recent Market Data")
                    st.write(data.head())
                    
                    if len(data) < 2:
                        st.error("Insufficient data for analysis.")
                    else:
                        risk_metrics = calculate_risk_metrics(data)
                    
                    # Key Performance Metrics
                    st.subheader("Key Performance Metrics")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Risk-Adjusted Return (Sharpe)", f"{risk_metrics['sharpe_ratio']:.2f}")
                    with col2:
                        st.metric("Value at Risk (95%)", f"{risk_metrics['value_at_risk']:.2%}")
                    with col3:
                        st.metric("Maximum Drawdown", f"{risk_metrics['max_drawdown']:.2%}")
                    
                    # Price Analysis
                    st.subheader("Historical Price Analysis")
                    st.line_chart(data['Close'])
                    
                    # Market Analysis
                    prediction = get_ai_prediction(
                        data.tail(30),  # Pass the DataFrame directly
                        context, 
                        asset_type
                    )
                    
                    if prediction:
                        try:
                            prediction_dict = json.loads(prediction)
                            
                            st.subheader("Market Analysis Insights")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**Market Trend Analysis**")
                                st.write(prediction_dict['trend'])
                                
                                st.write("**Key Market Drivers**")
                                for factor in prediction_dict['factors']:
                                    st.write(f"• {factor}")
                            
                            with col2:
                                st.write("**Risk Assessment**")
                                for risk in prediction_dict['risks']:
                                    st.write(f"• {risk}")
                                
                                st.write("**Market Opportunities**")
                                for opp in prediction_dict['opportunities']:
                                    st.write(f"• {opp}")
                            
                            # Machine Learning Analysis
                            if advanced_analysis:
                                st.subheader("Quantitative Analysis")
                                
                                try:
                                    # Ensure we have enough data
                                    if len(data) < 50:
                                        st.warning("Insufficient data for quantitative analysis. Need at least 50 data points.")
                                        return
                                        
                                    # Perform ML prediction with error handling
                                    ml_results = ml_enhanced_prediction(data)
                                    
                                    if ml_results and 'model' in ml_results:
                                        # Create tabs for different analysis sections
                                        ml_tabs = st.tabs(["Feature Analysis", "Technical Indicators", "Forecast Analysis", "Market Regime"])
                                        
                                        with ml_tabs[0]:
                                            st.write("### Feature Importance Analysis")
                                            
                                            # Display feature importance with interpretation
                                            importance_df = ml_results['feature_importance']
                                            st.dataframe(importance_df)
                                            
                                            # Interpret top features
                                            top_feature = importance_df.iloc[0]
                                            st.write("#### Key Driver Analysis")
                                            st.write(f"The most significant factor in price movement is **{top_feature['feature']}** "
                                                   f"with an importance score of {top_feature['importance']:.2%}")
                                            
                                            # Feature correlation analysis
                                            st.write("#### Feature Correlations")
                                            feature_data = data[['Close', 'Volume']].copy()
                                            feature_data['MA_10'] = data['Close'].rolling(window=10).mean()
                                            feature_data['MA_50'] = data['Close'].rolling(window=50).mean()
                                            feature_data['RSI'] = calculate_rsi(data['Close'])
                                            
                                            correlation_matrix = feature_data.corr()
                                            fig = px.imshow(correlation_matrix,
                                                          labels=dict(color="Correlation"),
                                                          color_continuous_scale="RdBu")
                                            st.plotly_chart(fig, use_container_width=True)
                                        
                                        with ml_tabs[1]:
                                            st.write("### Technical Analysis")
                                            
                                            # RSI Analysis
                                            rsi = calculate_rsi(data['Close'])
                                            current_rsi = rsi.iloc[-1]
                                            
                                            # Moving Average Analysis
                                            ma_10 = data['Close'].rolling(window=10).mean()
                                            ma_50 = data['Close'].rolling(window=50).mean()
                                            
                                            # Current price vs MAs
                                            current_price = data['Close'].iloc[-1]
                                            price_vs_ma10 = (current_price / ma_10.iloc[-1] - 1) * 100
                                            price_vs_ma50 = (current_price / ma_50.iloc[-1] - 1) * 100
                                            
                                            # Technical signals
                                            col1, col2 = st.columns(2)
                                            with col1:
                                                st.metric("RSI (14)", f"{current_rsi:.1f}", 
                                                         help="RSI > 70: Overbought, RSI < 30: Oversold")
                                                st.metric("Price vs MA(10)", f"{price_vs_ma10:+.1f}%")
                                            with col2:
                                                st.metric("Volume Trend", 
                                                         "Above Average" if data['Volume'].iloc[-1] > data['Volume'].mean() else "Below Average")
                                                st.metric("Price vs MA(50)", f"{price_vs_ma50:+.1f}%")
                                            
                                            # Technical Analysis Summary
                                            st.write("#### Technical Outlook")
                                            signals = []
                                            if current_rsi > 70:
                                                signals.append("• RSI indicates **overbought** conditions")
                                            elif current_rsi < 30:
                                                signals.append("• RSI indicates **oversold** conditions")
                                            
                                            if price_vs_ma10 > 0 and price_vs_ma50 > 0:
                                                signals.append("• Price is **above** both moving averages, indicating an uptrend")
                                            elif price_vs_ma10 < 0 and price_vs_ma50 < 0:
                                                signals.append("• Price is **below** both moving averages, indicating a downtrend")
                                            
                                            for signal in signals:
                                                st.write(signal)
                                        
                                        with ml_tabs[2]:
                                            st.write("### Forecast Analysis")
                                            
                                            # Generate forecast using sufficient historical data
                                            forecast_window = min(60, len(data))
                                            forecast_values = generate_forecast(
                                                ml_results['model'], 
                                                ml_results['scaler'], 
                                                data.tail(forecast_window),
                                                forecast_period=30
                                            )
                                            
                                            if forecast_values is not None:
                                                # Create forecast dataframe
                                                forecast_df = pd.DataFrame(forecast_values, columns=['Forecast'])
                                                
                                                # Calculate forecast metrics
                                                forecast_change = (forecast_df['Forecast'].iloc[-1] / current_price - 1) * 100
                                                forecast_volatility = forecast_df['Forecast'].std() / forecast_df['Forecast'].mean() * 100
                                                
                                                # Display forecast metrics
                                                col1, col2 = st.columns(2)
                                                with col1:
                                                    st.metric("30-Day Forecast Change", f"{forecast_change:+.1f}%")
                                                    st.metric("Forecast Volatility", f"{forecast_volatility:.1f}%")
                                                with col2:
                                                    st.metric("Data Points Used", f"{ml_results.get('data_points', 'N/A')}")
                                                    st.metric("Forecast Window", f"{forecast_window} days")
                                                
                                                # Forecast visualization
                                                fig = create_advanced_forecast_plot(
                                                    data['Close'],
                                                    forecast_df,
                                                    symbol,
                                                    asset_type,
                                                    ml_results['model']
                                                )
                                                st.plotly_chart(fig, use_container_width=True)
                                                
                                                # Forecast interpretation
                                                st.write("#### Forecast Interpretation")
                                                if forecast_change > 0:
                                                    st.write(f"The model predicts a **positive trend** with an expected return of {forecast_change:+.1f}% "
                                                           f"over the next 30 days, with a volatility of {forecast_volatility:.1f}%")
                                                else:
                                                    st.write(f"The model predicts a **negative trend** with an expected return of {forecast_change:+.1f}% "
                                                           f"over the next 30 days, with a volatility of {forecast_volatility:.1f}%")
                                        
                                        with ml_tabs[3]:
                                            st.write("### Market Regime Analysis")
                                            
                                            # Calculate returns
                                            returns = data['Close'].pct_change()
                                            volatility = returns.rolling(window=20).std() * np.sqrt(252) * 100
                                            current_volatility = volatility.iloc[-1]
                                            
                                            # Determine market regime
                                            if current_volatility < 15:
                                                regime = "Low Volatility"
                                                regime_desc = "The market is currently in a stable state with low volatility"
                                            elif current_volatility < 25:
                                                regime = "Normal Volatility"
                                                regime_desc = "The market is showing typical volatility levels"
                                            else:
                                                regime = "High Volatility"
                                                regime_desc = "The market is experiencing elevated volatility levels"
                                            
                                            # Display regime analysis
                                            st.metric("Current Market Regime", regime)
                                            st.metric("Annualized Volatility", f"{current_volatility:.1f}%")
                                            st.write(f"**Regime Description:** {regime_desc}")
                                            
                                            # Plot volatility trend
                                            fig = px.line(volatility, 
                                                        title="Historical Volatility Trend",
                                                        labels={"value": "Annualized Volatility (%)", "index": "Date"})
                                            st.plotly_chart(fig, use_container_width=True)
                                            
                                    else:
                                        st.warning("Could not perform quantitative analysis. Check the data quality.")
                                except Exception as e:
                                    st.error(f"Error in quantitative analysis: {str(e)}")
                                    logger.error(f"Quantitative analysis error for {symbol}: {str(e)}")
                        except Exception as e:
                            st.error(f"Error processing predictions: {str(e)}")

def generate_shareable_report(symbol, historical_data, ai_prediction, ml_results):
    """
    Generate a comprehensive shareable investment report
    """
    report = f"""
    INVESTMENT INSIGHTS REPORT
    Asset: {symbol}
    Generated: {datetime.now()}

    MARKET TREND
    ------------
    {ai_prediction['trend']}

    KEY INVESTMENT FACTORS
    ----------------------
    Positive Factors:
    {', '.join(ai_prediction['factors'])}

    RISK ASSESSMENT
    ---------------
    Identified Risks:
    {', '.join(ai_prediction['risks'])}

    OPPORTUNITIES
    -------------
    Potential Opportunities:
    {', '.join(ai_prediction['opportunities'])}

    MACHINE LEARNING INSIGHTS
    -------------------------
    Top Influential Features:
    {ml_results['feature_importance'].to_string()}

    FORECAST PROJECTION
    -------------------
    {json.dumps(ai_prediction['forecast'], indent=2)}

    DISCLAIMER
    ----------
    This report is for informational purposes only. 
    Not financial advice. Consult a licensed financial advisor.
    """
    
    return report

def setup_logging():
    """
    Setup logging for the application
    """
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('financial_forecast.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

if __name__ == "__main__":
    # Setup logging
    logger = setup_logging()
    
    try:
        # Run main application
        main()
    except Exception as e:
        logger.error(f"Critical application error: {str(e)}")
        st.error(f"An unexpected error occurred: {str(e)}")
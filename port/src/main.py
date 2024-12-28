import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from config.config import Config
from src.asset_tracker import AssetTracker
from src.financial_analyzer import FinancialAnalyzer
from src.ai_insights import AIInvestmentAdvisor
from src.chatbot import FinanceChatbot
import time
import requests
import numpy as np
import ta
from src.database import Database
from src.background_manager import BackgroundManager
from src.utils import calculate_technical_indicators, get_asset_info, calculate_correlation

# Initialize session state for caching
if 'portfolio_summary' not in st.session_state:
    st.session_state.portfolio_summary = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'crypto_prices' not in st.session_state:
    st.session_state.crypto_prices = {}

# Cache duration in seconds
CACHE_DURATION = 900  # 15 minutes

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def get_crypto_price(coin_id):
    """Cached cryptocurrency price fetch"""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return float(data[coin_id]['usd'])
    except Exception:
        return None
    return None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_crypto_history(coin_id):
    """Cached cryptocurrency history fetch"""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=30&interval=daily"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            prices = data.get('prices', [])
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
    except Exception:
        return None
    return None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_market_data():
    """Cache market data for reuse"""
    spy = yf.Ticker("SPY")
    return spy.history(period="1y")

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_asset_info_with_history(symbol: str, asset_type: str = 'stock'):
    """Get asset information and history with caching"""
    info = get_asset_info(symbol, asset_type)
    if asset_type.lower() == 'stock':
        ticker = yf.Ticker(symbol)
        history = ticker.history(period='1mo')
    else:
        history = pd.DataFrame()  # For crypto, history is handled separately
    return info, history

class PortfolioManagementApp:
    def __init__(self):
        st.set_page_config(layout="wide")
        Config.validate_config()
        
        # Initialize database
        self.db = Database()
        
        # Initialize background manager
        self.background_manager = BackgroundManager()
        
        # Initialize components
        self.asset_tracker = AssetTracker(self.db)
        self.financial_analyzer = FinancialAnalyzer()
        self.ai_advisor = AIInvestmentAdvisor(Config.GEMINI_API_KEY)
        self.chatbot = FinanceChatbot(Config.GEMINI_API_KEY)
        
        # Setup background tasks
        self._setup_background_tasks()
        
        # Page mapping
        self.pages = {
            "Portfolio Dashboard": self.portfolio_dashboard_page,
            "Add Asset": self.add_asset_page,
            "Asset Analysis": self.asset_analysis_page,
            "AI Insights": self.ai_insights_page,
            "Risk Analysis": self.risk_analysis_page
        }
    
    def _setup_background_tasks(self):
        """Setup background refresh tasks"""
        # Update portfolio summary every 5 minutes
        self.background_manager.add_task(
            'portfolio_summary',
            self.asset_tracker.get_portfolio_summary,
            300  # 5 minutes
        )
        
        # Update market data every 15 minutes
        self.background_manager.add_task(
            'market_data',
            self.get_market_conditions,
            900  # 15 minutes
        )
    
    @st.cache_data(ttl=900)  # Cache portfolio summary for 15 minutes
    def get_cached_portfolio_summary(_self):
        """Get portfolio summary from background task or calculate if needed"""
        result = _self.background_manager.get_result('portfolio_summary')
        if result and result['status'] == 'success':
            return result['result']
        return _self.asset_tracker.get_portfolio_summary()
    
    def run(self):
        """Run the Streamlit application with lazy loading"""
        st.title("AI-Powered Portfolio Management Assistant")
        
        # Sidebar for navigation
        with st.sidebar:
            st.image("https://img.icons8.com/color/96/000000/investment-portfolio.png", width=100)
            menu = st.selectbox(
                "Navigation", 
                list(self.pages.keys())
            )
            
            # Show portfolio value in sidebar using cached data
            summary = self.get_cached_portfolio_summary()
            if summary:
                st.metric(
                    "Portfolio Value", 
                    f"${summary['total_portfolio_value']:,.2f}",
                    delta=None
                )
        
        # Update chatbot context with latest portfolio data
        if summary:
            self.chatbot.update_context('portfolio_data', summary)
            
        # Display chatbot UI (will be shown on all pages)
        self.chatbot.display_chat_ui()
        
        # Load selected page
        self.pages[menu]()
    
    def portfolio_dashboard_page(self):
        """Enhanced portfolio overview with interactive charts"""
        st.header("Portfolio Dashboard")
        
        # Get processed data using helper methods
        assets, processed_assets = self._get_processed_assets()
        if not assets:
            st.info("Your portfolio is empty. Add some assets to get started!")
            return
        
        summary = self._get_portfolio_metrics()
        
        # Layout with metrics using container for better performance
        metrics_container = st.container()
        with metrics_container:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Value", f"${summary['total_portfolio_value']:,.2f}")
            with col2:
                st.metric("Volatility", f"{summary['performance_metrics']['volatility']:.1f}%")
            with col3:
                st.metric("Sharpe Ratio", f"{summary['performance_metrics']['sharpe_ratio']:.2f}")
            with col4:
                st.metric("Diversification", f"{summary['risk_metrics']['diversification_score']:.0f}%")
        
        # Display portfolio charts and tables
        self._display_portfolio_charts(summary)
        self._display_assets_table(processed_assets)
        self._display_asset_removal(assets)
    
    def add_asset_page(self):
        """Enhanced page for adding new assets"""
        st.header("Add New Asset")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            with st.form("add_asset_form"):
                symbol = st.text_input("Symbol").upper()
                asset_type = st.selectbox(
                    "Asset Type",
                    ["Stock", "ETF", "Crypto", "Bond", "Commodity", "Real Estate", "Other"]
                )
                quantity = st.number_input("Quantity", min_value=0.0, step=0.1)
                purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, step=0.01)
                
                submit = st.form_submit_button("Add Asset")
                
                if submit and symbol and quantity > 0 and purchase_price > 0:
                    try:
                        asset_id = self.asset_tracker.add_asset(
                            symbol, asset_type, quantity, purchase_price
                        )
                        # Clear cache after adding new asset
                        st.session_state.last_update = None
                        st.success(f"Asset {symbol} added successfully!")
                        st.rerun()  # Refresh the page to show updated portfolio
                    except Exception as e:
                        st.error(f"Error adding asset: {str(e)}")
        
        with col2:
            if symbol:
                try:
                    st.subheader("Asset Preview")
                    
                    if asset_type == "Crypto":
                        # Handle crypto preview
                        clean_symbol = symbol.upper().strip()
                        # Get current price from Binance
                        try:
                            current_price = self.asset_tracker._get_current_price(clean_symbol, "Crypto")
                            if current_price:
                                st.metric("Current Price", f"${current_price:,.2f}")
                            
                            # Get historical data for price chart
                            history = self.asset_tracker.get_asset_history(clean_symbol, "Crypto", period="1mo")
                            if not history.empty:
                                fig = px.line(history, y='Close', title='1 Month Price History')
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning("No historical data available for this crypto")
                        except Exception as e:
                            st.warning(f"Unable to fetch crypto data: {str(e)}")
                    else:
                        # Handle stock preview
                        @st.cache_data(ttl=60)
                        def get_stock_info(symbol):
                            ticker = yf.Ticker(symbol)
                            return ticker.info, ticker.history(period='1mo')
                        
                        info, history = get_stock_info(symbol)
                        st.write(f"**{info.get('longName', symbol)}**")
                        if not history.empty:
                            current = history['Close'].iloc[-1]
                            st.metric("Current Price", f"${current:.2f}")
                        st.write(f"Sector: {info.get('sector', 'Other')}")
                        st.write(f"Industry: {info.get('industry', 'N/A')}")
                        
                        if not history.empty:
                            fig = px.line(history, y='Close', title='1 Month Price History')
                            st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.warning(f"Unable to fetch preview data: {str(e)}")
    
    def _get_processed_assets(self):
        """Helper method to get processed assets with performance data"""
        assets = self.asset_tracker.get_all_assets()
        if not assets:
            return None, None
        
        processed_assets = {}
        for asset_id, asset in assets.items():
            performance = self.asset_tracker.get_asset_performance(asset_id)
            current_price = performance.get('current_price', 0.0)
            asset['current_price'] = current_price
            
            processed_assets[asset_id] = {
                'asset': asset,
                'performance': performance
            }
        
        return assets, processed_assets
    
    def _get_portfolio_metrics(self):
        """Helper method to get portfolio summary and metrics"""
        return self.get_cached_portfolio_summary()
    
    def _display_portfolio_charts(self, summary):
        """Helper method to display portfolio charts"""
        charts_container = st.container()
        with charts_container:
            col1, col2 = st.columns(2)
            
            with col1:
                if summary['asset_allocation']:
                    fig = go.Figure(data=[go.Pie(
                        labels=list(summary['asset_allocation'].keys()),
                        values=list(summary['asset_allocation'].values()),
                        hole=.3
                    )])
                    fig.update_layout(
                        title="Asset Allocation",
                        showlegend=True,
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No asset allocation data available")
            
            with col2:
                if summary['sector_allocation']:
                    fig = go.Figure(data=[go.Bar(
                        x=list(summary['sector_allocation'].keys()),
                        y=list(summary['sector_allocation'].values())
                    )])
                    fig.update_layout(
                        title="Sector Allocation",
                        showlegend=False,
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No sector allocation data available")
    
    def _display_assets_table(self, processed_assets):
        """Helper method to display assets table"""
        st.subheader("Your Assets")
        table_col, action_col = st.columns([4, 1])
        
        assets_data = []
        for asset_id, processed in processed_assets.items():
            asset = processed['asset']
            performance = processed['performance']
            
            try:
                return_value = float(performance['total_return_percentage'])
            except (ValueError, TypeError):
                return_value = 0.0
            
            assets_data.append({
                'ID': asset_id,
                'Name': asset.get('name', asset['symbol']),
                'Symbol': asset['symbol'],
                'Type': asset['type'],
                'Sector': asset.get('sector', 'Other'),
                'Quantity': asset['quantity'],
                'Current Price': asset.get('current_price', 0.0),
                'Total Value': performance['current_value'],
                'Return': return_value,
                'Trend': performance.get('trend_analysis', {}).get('trend', 'Unknown')
            })
        
        with table_col:
            df = pd.DataFrame(assets_data)
            df['Quantity'] = df['Quantity'].map('{:,.2f}'.format)
            df['Current Price'] = df['Current Price'].map('${:,.2f}'.format)
            df['Total Value'] = df['Total Value'].map('${:,.2f}'.format)
            df['Return'] = df['Return'].map('{:,.1f}%'.format)
            
            display_df = df.drop(columns=['ID'])
            styled_df = display_df.style.map(self._color_return, subset=['Return'])
            st.dataframe(styled_df, use_container_width=True)
    
    @staticmethod
    def _color_return(val):
        """Helper method for coloring returns"""
        try:
            numeric_val = float(val.strip('%'))
            return f"color: {'green' if numeric_val > 0 else 'red' if numeric_val < 0 else 'black'}"
        except (ValueError, TypeError):
            return 'color: black'
    
    def _display_asset_removal(self, assets):
        """Helper method to display asset removal interface"""
        with st.container():
            st.subheader("Remove Asset")
            
            asset_options = {}
            for asset_id, asset in assets.items():
                symbol = asset['symbol']
                name = asset.get('name', symbol)
                added_date = datetime.fromisoformat(asset['purchase_date']).strftime('%Y-%m-%d')
                display_name = (
                    f"{name} ({symbol}) - "
                    f"Qty: {asset['quantity']:.2f} @ ${asset['purchase_price']:.2f} "
                    f"[Added: {added_date}]"
                )
                asset_options[display_name] = asset_id
            
            selected_asset_display = st.selectbox(
                "Select Asset to Remove",
                options=list(asset_options.keys()),
                key="remove_asset_select"
            )
            
            if selected_asset_display:
                selected_asset_id = asset_options[selected_asset_display]
                selected_asset = assets[selected_asset_id]
                
                st.write(f"**Selected Asset Details:**")
                st.write(f"Symbol: {selected_asset['symbol']}")
                st.write(f"Quantity: {selected_asset['quantity']:.2f}")
                st.write(f"Purchase Price: ${selected_asset['purchase_price']:.2f}")
                st.write(f"Added Date: {datetime.fromisoformat(selected_asset['purchase_date']).strftime('%Y-%m-%d')}")
                
                if st.button("Remove Selected Asset", type="primary"):
                    if self.asset_tracker.remove_asset(selected_asset_id):
                        st.success(f"Successfully removed {selected_asset['symbol']} (Qty: {selected_asset['quantity']:.2f})")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to remove asset. Please try again.")
    
    def risk_analysis_page(self):
        """Enhanced risk analysis with interactive visualizations"""
        st.header("Portfolio Risk Analysis")
        
        # Get processed data using helper methods
        assets, processed_assets = self._get_processed_assets()
        if not assets:
            st.info("Add assets to your portfolio to see risk analysis.")
            return
        
        summary = self._get_portfolio_metrics()
        
        # Display risk metrics
        self._display_risk_metrics(summary)
        
        # Display risk visualization
        self._display_risk_visualization(assets)
        
        # Display AI risk assessment
        self._display_risk_assessment(summary, assets)
    
    def _display_risk_metrics(self, summary):
        """Helper method to display risk metrics"""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Portfolio Volatility", 
                     f"{summary['performance_metrics']['volatility']:.1f}%")
        with col2:
            st.metric("Diversification Score", 
                     f"{summary['risk_metrics']['diversification_score']:.0f}%")
        with col3:
            st.metric("Sector Concentration", 
                     f"{summary['risk_metrics']['sector_concentration']:.1f}%")
    
    def _display_risk_visualization(self, assets):
        """Helper method to display risk visualization"""
        st.subheader("Risk Distribution")
        
        risk_data = []
        for asset_id, asset in assets.items():
            perf = self.asset_tracker.get_asset_performance(asset_id)
            risk_data.append({
                'Asset': asset['symbol'],
                'Return': perf['total_return_percentage'],
                'Volatility': perf['volatility'],
                'Value': perf['current_value'],
                'Type': asset['type']
            })
        
        df = pd.DataFrame(risk_data)
        fig = px.scatter(
            df,
            x='Volatility',
            y='Return',
            size='Value',
            color='Type',
            hover_data=['Asset'],
            title='Risk-Return Analysis'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    def _display_risk_assessment(self, summary, assets):
        """Helper method to display AI risk assessment"""
        st.subheader("AI Risk Assessment")
        risk_metrics = {
            'portfolio_volatility': summary['performance_metrics']['volatility'],
            'diversification': summary['risk_metrics']['diversification_score'],
            'sector_concentration': summary['risk_metrics']['sector_concentration'],
            'asset_correlation': calculate_correlation(assets)
        }
        
        risk_assessment = self.ai_advisor.risk_recommendation(risk_metrics)
        st.write(risk_assessment)
    
    def get_market_conditions(self):
        """Get current market conditions with real data"""
        try:
            # Get S&P 500 data for market sentiment
            spy = yf.Ticker("SPY")
            hist = spy.history(period="1mo")
            
            if hist.empty:
                return self._default_market_conditions()
            
            # Calculate actual market metrics safely
            current_price = hist['Close'].iloc[-1]
            
            # Calculate monthly return using first available price if we don't have 30 days
            first_price = hist['Close'].iloc[0]
            monthly_return = ((current_price - first_price) / first_price) * 100
            
            # Calculate trend
            sma_20 = hist['Close'].rolling(window=min(20, len(hist))).mean().iloc[-1]
            rsi = ta.momentum.RSIIndicator(hist['Close']).rsi().iloc[-1]
            
            # Determine sentiment based on multiple factors
            sentiment = "Neutral"
            if current_price > sma_20:
                if rsi > 70:
                    sentiment = "Overbought"
                elif rsi > 50:
                    sentiment = "Bullish"
            elif current_price < sma_20:
                if rsi < 30:
                    sentiment = "Oversold"
                elif rsi < 50:
                    sentiment = "Bearish"
            
            return {
                "market_sentiment": sentiment,
                "monthly_return": f"{monthly_return:.1f}%",
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            st.error(f"Error fetching market conditions: {str(e)}")
            return self._default_market_conditions()
    
    def _default_market_conditions(self):
        """Return default market conditions"""
        return {
            "market_sentiment": "Neutral",
            "monthly_return": "0.0%",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def analyze_asset_sentiment(self, symbol, asset_type):
        """Analyze sentiment for a specific asset using real data"""
        try:
            if asset_type.lower() == 'crypto':
                # Handle crypto assets
                if symbol.upper() in ['ETH', 'ETHEREUM']:
                    price_data = get_crypto_history('ethereum')
                    if price_data is not None:
                        close_prices = price_data['price']
                    else:
                        return self._default_sentiment()
                else:
                    return self._default_sentiment()
            else:
                # Handle stocks and other assets
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1mo")
                close_prices = hist['Close']
            
            if len(close_prices) < 14:  # Need at least 14 days for RSI
                return self._default_sentiment()
            
            # Calculate technical indicators
            rsi = ta.momentum.RSIIndicator(close_prices).rsi().iloc[-1]
            sma_20 = close_prices.rolling(window=20).mean().iloc[-1]
            current_price = close_prices.iloc[-1]
            
            # Calculate price momentum
            price_change = ((current_price - close_prices.iloc[-14]) / close_prices.iloc[-14]) * 100
            
            # Determine sentiment score (0-100)
            base_score = 50
            
            # Adjust score based on RSI
            rsi_factor = (rsi - 50) * 0.5
            base_score += rsi_factor
            
            # Adjust score based on trend
            if current_price > sma_20:
                base_score += 10
            else:
                base_score -= 10
            
            # Adjust score based on momentum
            base_score += min(max(price_change, -20), 20) * 0.5
            
            # Ensure score is within bounds
            sentiment_score = max(min(base_score, 100), 0)
            
            # Determine sentiment category
            if sentiment_score >= 70:
                category = "Strongly Bullish"
            elif sentiment_score >= 60:
                category = "Bullish"
            elif sentiment_score <= 30:
                category = "Bearish"
            elif sentiment_score <= 40:
                category = "Slightly Bearish"
            else:
                category = "Neutral"
            
            # Calculate confidence based on volatility and data quality
            volatility = close_prices.pct_change().std() * np.sqrt(252) * 100
            confidence = max(min(100 - volatility, 90), 40)  # Cap confidence between 40% and 90%
            
            return {
                "sentiment_score": sentiment_score,
                "sentiment_category": category,
                "confidence": confidence
            }
        except Exception as e:
            st.error(f"Error analyzing sentiment for {symbol}: {str(e)}")
            return self._default_sentiment()
    
    def _default_sentiment(self):
        """Return default sentiment values"""
        return {
            "sentiment_score": 50.0,
            "sentiment_category": "Neutral",
            "confidence": 40.0
        }
    
    def asset_analysis_page(self):
        """Asset Analysis Page with optimized performance"""
        st.title("Asset Analysis")
        
        # Get processed data using helper methods
        assets, processed_assets = self._get_processed_assets()
        if not assets:
            st.warning("No assets in portfolio. Please add some assets first.")
            return
        
        # Asset selector
        asset_symbols = [f"{a['symbol']} - {a.get('name', a['symbol'])}" for a in assets.values()]
        selected_display = st.selectbox("Select Asset", asset_symbols)
        selected_symbol = selected_display.split(" - ")[0] if selected_display else None
        
        if selected_symbol:
            # Get asset data efficiently
            asset = next(a for a in assets.values() if a['symbol'] == selected_symbol)
            
            # Use containers for better performance
            main_container = st.container()
            with main_container:
                price_col, metrics_col = st.columns([2, 1])
                
                with price_col:
                    # Get cached history data
                    history = self.asset_tracker.get_asset_history(selected_symbol, asset['type'], period="1y")
                    if not history.empty:
                        fig = go.Figure(data=[go.Candlestick(
                            x=history.index,
                            open=history['Open'],
                            high=history['High'],
                            low=history['Low'],
                            close=history['Close']
                        )])
                        fig.update_layout(
                            title="Price History (1 Year)",
                            xaxis_title="Date",
                            yaxis_title="Price ($)",
                            height=400,
                            showlegend=False
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("No historical data available for this asset.")
                
                with metrics_col:
                    # Get cached performance metrics
                    performance = self.asset_tracker.get_asset_performance(asset['id'])
                    metrics_container = st.container()
                    with metrics_container:
                        st.metric("Current Value", f"${performance['current_value']:,.2f}")
                        st.metric("Total Return", f"{performance['total_return_percentage']:.1f}%")
                        st.metric("Volatility", f"{performance['volatility']:.1f}%")
                        st.metric("Max Drawdown", f"{performance['max_drawdown']:.1f}%")
            
            # Technical Indicators with cached calculations
            tech_container = st.container()
            with tech_container:
                st.subheader("Technical Indicators")
                if not history.empty:
                    # Use cached technical indicators
                    indicators = calculate_technical_indicators(history['Close'])
                    if indicators:
                        tech_col1, tech_col2, tech_col3 = st.columns(3)
                        
                        with tech_col1:
                            st.metric("RSI (14)", f"{indicators['rsi']:.1f}")
                            rsi_value = indicators['rsi']
                            if rsi_value > 70:
                                st.write("Overbought")
                            elif rsi_value < 30:
                                st.write("Oversold")
                            else:
                                st.write("Neutral")
                        
                        with tech_col2:
                            st.metric("SMA (50)", f"${indicators['sma_50']:.2f}")
                            sma_diff = ((history['Close'].iloc[-1] - indicators['sma_50']) / indicators['sma_50']) * 100
                            st.write(f"{sma_diff:+.1f}% vs Price")
                        
                        with tech_col3:
                            st.metric("MACD", f"{indicators['macd']:.2f}")
                            st.write(f"{indicators['macd_signal']:.2f} Signal")
            
            # Risk Metrics with cached market data
            risk_container = st.container()
            with risk_container:
                st.subheader("Risk Metrics")
                if not history.empty:
                    # Get cached market data
                    market_history = get_market_data()
                    
                    if not market_history.empty:
                        # Calculate returns once
                        asset_returns = history['Close'].pct_change().dropna()
                        market_returns = market_history['Close'].pct_change().dropna()
                        
                        # Calculate risk metrics
                        beta = self.financial_analyzer.calculate_beta(asset_returns, market_returns)
                        alpha = self.financial_analyzer.calculate_alpha(asset_returns, market_returns, beta)
                        sharpe = self.financial_analyzer.calculate_sharpe_ratio(asset_returns)
                        sortino = self.financial_analyzer.calculate_sortino_ratio(asset_returns)
                        
                        risk_col1, risk_col2 = st.columns(2)
                        with risk_col1:
                            st.metric("Beta", f"{beta:.2f}")
                            st.metric("Sharpe Ratio", f"{sharpe:.2f}")
                        with risk_col2:
                            st.metric("Alpha", f"{alpha:.2%}")
                            st.metric("Sortino Ratio", f"{sortino:.2f}")
            
            # Asset Instances in an expander for better UI organization
            with st.expander("Asset Purchase History"):
                instances = [a for a in assets.values() if a['symbol'] == selected_symbol]
                for instance in instances:
                    st.write(f"Added: {instance['purchase_date'][:10]}")
                    st.write(f"Purchase Price: ${instance['purchase_price']:.2f}")
                    st.write(f"Quantity: {instance['quantity']}")
                    st.write("---")

    def ai_insights_page(self):
        """Enhanced AI-powered investment insights"""
        st.header("AI Investment Insights")
        
        summary = self._get_portfolio_metrics()
        if summary['total_portfolio_value'] == 0:
            st.info("Add assets to your portfolio to get AI-powered insights!")
            return
        
        # Tabs for different types of insights
        tab1, tab2, tab3, tab4 = st.tabs([
            "Portfolio Analysis", 
            "Market Insights", 
            "Technical Analysis",
            "Risk Assessment"
        ])
        
        with tab1:
            st.subheader("Portfolio Analysis")
            
            # Portfolio health score calculation with real metrics
            health_score = min(100, max(0, 
                summary['risk_metrics']['diversification_score'] * 0.4 +
                (100 - summary['risk_metrics']['sector_concentration']) * 0.3 +
                (60 - min(60, summary['performance_metrics']['volatility'])) * 0.3
            ))
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Portfolio Health Score", f"{health_score:.0f}/100")
            with col2:
                st.progress(health_score / 100)
            
            # Show allocation recommendations
            if summary['asset_allocation']:
                st.subheader("Current Asset Allocation")
                fig = go.Figure(data=[go.Pie(
                    labels=list(summary['asset_allocation'].keys()),
                    values=list(summary['asset_allocation'].values()),
                    hole=.3
                )])
                fig.update_layout(
                    title="Asset Allocation",
                    showlegend=True,
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("Market Sentiment Analysis")
            
            # Get market conditions
            market_data = self.get_market_conditions()
            
            # Display market metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Market Sentiment", market_data["market_sentiment"])
            with col2:
                st.metric("Monthly Return", market_data["monthly_return"])
            with col3:
                st.metric("Last Updated", market_data["last_updated"])
            
            # Show sentiment for each asset
            st.subheader("Asset-Specific Sentiment")
            assets = self.asset_tracker.get_all_assets()
            
            # Create a set to track unique symbols
            seen_symbols = set()
            
            for asset in assets.values():
                symbol = asset['symbol']
                # Skip if we've already analyzed this symbol
                if symbol in seen_symbols:
                    continue
                seen_symbols.add(symbol)
                
                asset_name = asset.get('name', symbol)
                sentiment = self.analyze_asset_sentiment(symbol, asset['type'])
                
                with st.expander(f"{asset_name} ({symbol})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "Sentiment Score", 
                            f"{sentiment['sentiment_score']:.1f}",
                            sentiment['sentiment_category']
                        )
                    with col2:
                        st.metric(
                            "Confidence",
                            f"{sentiment['confidence']:.0f}%"
                        )
        
        with tab3:
            st.subheader("Technical Analysis Insights")
            
            # Show technical analysis for each asset
            assets = self.asset_tracker.get_all_assets()
            for asset in assets.values():
                asset_name = asset.get('name', asset['symbol'])
                with st.expander(f"{asset_name} ({asset['symbol']})"):
                    history = self.asset_tracker.get_asset_history(
                        asset['symbol'], 
                        asset['type'],
                        period="1mo"
                    )
                    
                    if not history.empty:
                        # Get technical indicators
                        indicators = calculate_technical_indicators(history['Close'])
                        
                        # Get price prediction
                        prediction = self.ai_advisor.predict_price_movement(history, indicators)
                        
                        # Display prediction
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                "Predicted Movement",
                                prediction['direction'],
                                f"Confidence: {prediction['confidence']:.1f}%"
                            )
                        
                        with col2:
                            st.metric(
                                "RSI Signal",
                                indicators['rsi'],
                                "Overbought" if indicators['rsi'] > 70 else "Oversold" if indicators['rsi'] < 30 else "Neutral"
                            )
                        
                        st.write("**Analysis:**")
                        st.write(prediction['analysis'])
        
        with tab4:
            st.subheader("Risk Assessment")
            
            # Calculate portfolio-wide risk metrics
            assets = self.asset_tracker.get_all_assets()
            spy = yf.Ticker("SPY")
            market_history = spy.history(period="1y")
            
            if assets and not market_history.empty:
                market_returns = market_history['Close'].pct_change().dropna()
                
                # Display risk metrics for each asset
                for asset in assets.values():
                    asset_name = asset.get('name', asset['symbol'])
                    with st.expander(f"{asset_name} ({asset['symbol']})"):
                        history = self.asset_tracker.get_asset_history(
                            asset['symbol'],
                            asset['type'],
                            period="1y"
                        )
                        
                        if not history.empty:
                            returns = history['Close'].pct_change().dropna()
                            
                            # Calculate risk metrics
                            beta = self.financial_analyzer.calculate_beta(returns, market_returns)
                            alpha = self.financial_analyzer.calculate_alpha(returns, market_returns, beta)
                            drawdown = self.financial_analyzer.calculate_drawdown(returns)
                            
                            # Display metrics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Beta", f"{beta:.2f}")
                            with col2:
                                st.metric("Alpha", f"{alpha:.2f}%")
                            with col3:
                                st.metric("Max Drawdown", f"{drawdown['max_drawdown']*100:.1f}%")
                            
                            # Get risk recommendations
                            risk_metrics = {
                                'beta': beta,
                                'alpha': alpha,
                                'drawdown': drawdown['max_drawdown'],
                                'volatility': np.std(returns) * np.sqrt(252)
                            }
                            
                            recommendations = self.ai_advisor.risk_recommendation(risk_metrics)
                            st.write("**Risk Management Recommendations:**")
                            st.write(recommendations)

def main():
    app = PortfolioManagementApp()
    app.run()

if __name__ == "__main__":
    main()

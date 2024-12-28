import yfinance as yf
import pandas as pd
from typing import Dict, List, Any
import uuid
from datetime import datetime, timedelta
import json
import os
from config.config import Config
import numpy as np
from src.ai_insights import AIInvestmentAdvisor
import requests
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException
from src.database import Database
from src.utils import calculate_technical_indicators, get_asset_info

class AssetTracker:
    def __init__(self, db: Database):
        self.db = db
        self.ai_advisor = AIInvestmentAdvisor(Config.GEMINI_API_KEY)
        # Initialize Binance client
        self.binance_client = Client(None, None)  # Public API doesn't require keys
        # Mapping of common crypto symbols to Binance symbols
        self.crypto_mapping = {
            'BTC': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'USDT': 'USDTUSD',
            'BNB': 'BNBUSDT',
            'XRP': 'XRPUSDT',
            'ADA': 'ADAUSDT',
            'DOGE': 'DOGEUSDT',
            'SOL': 'SOLUSDT',
            'DOT': 'DOTUSDT',
            'MATIC': 'MATICUSDT',
        }
    
    def add_asset(self, symbol: str, asset_type: str, quantity: float, purchase_price: float) -> str:
        """Add a new asset to the portfolio"""
        asset_id = str(uuid.uuid4())
        
        # Get additional asset info
        asset_info = self._get_asset_info(symbol, asset_type)
        
        asset_data = {
            'id': asset_id,
            'symbol': symbol,
            'name': asset_info.get('name', symbol),
            'type': asset_type,
            'quantity': quantity,
            'purchase_price': purchase_price,
            'purchase_date': datetime.now().isoformat(),
            'sector': asset_info.get('sector'),
            'metadata': asset_info
        }
        
        if self.db.add_asset(asset_data):
            return asset_id
        return None
    
    def get_all_assets(self) -> Dict[str, Dict[str, Any]]:
        """Get all assets from the database"""
        return self.db.get_all_assets()
    
    def remove_asset(self, asset_id: str) -> bool:
        """Remove an asset from the portfolio"""
        return self.db.remove_asset(asset_id)
    
    def get_asset_performance(self, asset_id: str) -> Dict[str, Any]:
        """Get performance metrics for an asset"""
        assets = self.get_all_assets()
        asset = assets.get(asset_id)
        if not asset:
            return None
        
        # Try to get cached performance data
        cache_key = f"performance_{asset_id}"
        cached_data = self.db.get_cache(cache_key)
        if cached_data and time.time() - cached_data['timestamp'] < 300:  # 5 minutes cache
            return cached_data['value']
        
        # Calculate performance metrics
        current_price = self._get_current_price(asset['symbol'], asset['type'])
        if current_price is None:
            return None
        
        current_value = current_price * asset['quantity']
        total_cost = asset['purchase_price'] * asset['quantity']
        total_return = current_value - total_cost
        total_return_percentage = (total_return / total_cost) * 100
        
        # Get historical data for volatility calculation
        history = self.get_asset_history(asset['symbol'], asset['type'], period="1mo")
        if history.empty:
            return {
                'current_price': current_price,
                'current_value': current_value,
                'total_return': total_return,
                'total_return_percentage': total_return_percentage,
                'volatility': 0.0,
                'max_drawdown': 0.0,
                'daily_returns': []
            }
        
        # Calculate daily returns
        daily_returns = history['Close'].pct_change().dropna()
        
        # Calculate annualized volatility
        daily_volatility = np.std(daily_returns)
        annualized_volatility = daily_volatility * np.sqrt(252) * 100
        
        # Calculate max drawdown
        peak = history['Close'].expanding(min_periods=1).max()
        drawdown = ((history['Close'] - peak) / peak) * 100
        max_drawdown = abs(drawdown.min()) if not drawdown.empty else 0
        
        performance_data = {
            'current_price': current_price,
            'current_value': current_value,
            'total_return': total_return,
            'total_return_percentage': total_return_percentage,
            'volatility': annualized_volatility,
            'max_drawdown': max_drawdown,
            'daily_returns': daily_returns.tolist()
        }
        
        # Cache the results
        self.db.set_cache(cache_key, performance_data, time.time())
        
        return performance_data
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary with performance metrics"""
        assets = self.get_all_assets()
        if not assets:
            return {
                'total_portfolio_value': 0.0,
                'asset_allocation': {},
                'sector_allocation': {},
                'type_allocation': {},
                'performance_metrics': {
                    'volatility': 0.0,
                    'sharpe_ratio': 0.0,
                },
                'risk_metrics': {
                    'diversification_score': 0.0,
                    'sector_concentration': 0.0
                }
            }
        
        # Calculate total value and allocations
        total_value = 0.0
        asset_values = {}
        sector_values = {}
        type_values = {}
        all_returns = []
        weights = []
        
        # First pass: calculate total value and collect asset values
        for asset_id, asset in assets.items():
            performance = self.get_asset_performance(asset_id)
            if not performance:
                continue
            
            current_value = performance.get('current_value', 0.0)
            total_value += current_value
            asset_values[asset['symbol']] = current_value
            sector_values[asset.get('sector', 'Other')] = sector_values.get(asset.get('sector', 'Other'), 0) + current_value
            type_values[asset['type']] = type_values.get(asset['type'], 0) + current_value
            
            # Get historical data for returns calculation
            history = self.get_asset_history(asset['symbol'], asset['type'], period="1mo")
            if not history.empty:
                returns = history['Close'].pct_change().dropna()
                if len(returns) > 0:
                    all_returns.append(returns)
                    weights.append(current_value / total_value)
        
        # Calculate percentage allocations
        asset_allocation = {k: (v / total_value) * 100 for k, v in asset_values.items()} if total_value > 0 else {}
        sector_allocation = {k: (v / total_value) * 100 for k, v in sector_values.items()} if total_value > 0 else {}
        type_allocation = {k: (v / total_value) * 100 for k, v in type_values.items()} if total_value > 0 else {}
        
        # Calculate portfolio-level metrics
        if all_returns and weights:
            # Align all return series to the same dates
            aligned_returns = pd.concat(all_returns, axis=1).fillna(0)
            weights = np.array(weights)
            
            # Calculate portfolio returns
            portfolio_returns = aligned_returns.dot(weights)
            
            # Calculate annualized metrics
            daily_volatility = portfolio_returns.std()
            annualized_volatility = daily_volatility * np.sqrt(252) * 100  # Convert to percentage
            
            # Calculate annualized return
            daily_return_mean = portfolio_returns.mean()
            annualized_return = ((1 + daily_return_mean) ** 252 - 1) * 100  # Convert to percentage
            
            # Calculate Sharpe ratio using annualized values
            risk_free_rate = Config.DEFAULT_RISK_FREE_RATE * 100  # Convert to percentage
            excess_return = annualized_return - risk_free_rate
            sharpe_ratio = excess_return / annualized_volatility if annualized_volatility > 0 else 0
        else:
            annualized_volatility = 0.0
            sharpe_ratio = 0.0
        
        # Calculate diversification score
        num_assets = len(assets)
        num_sectors = len(sector_values)
        max_weight = max(asset_allocation.values()) if asset_allocation else 0
        
        diversification_score = (
            (min(num_assets, 10) / 10) * 40 +  # Number of assets (max 40 points)
            (min(num_sectors, 5) / 5) * 30 +   # Number of sectors (max 30 points)
            (max(0, 100 - max_weight)) * 0.3   # Concentration (max 30 points)
        )
        
        return {
            'total_portfolio_value': total_value,
            'asset_allocation': asset_allocation,
            'sector_allocation': sector_allocation,
            'type_allocation': type_allocation,
            'performance_metrics': {
                'volatility': annualized_volatility,
                'sharpe_ratio': sharpe_ratio,
            },
            'risk_metrics': {
                'diversification_score': diversification_score,
                'sector_concentration': max(sector_allocation.values()) if sector_allocation else 0
            }
        }
    
    def _get_asset_info(self, symbol: str, asset_type: str) -> Dict[str, Any]:
        """Get asset information from appropriate source"""
        return get_asset_info(symbol, asset_type, self.binance_client)
    
    def _get_current_price(self, symbol: str, asset_type: str) -> float:
        """Get current price for an asset"""
        try:
            if asset_type.lower() == 'crypto':
                ticker = self.crypto_mapping.get(symbol.upper(), f"{symbol}USDT")
                price = float(self.binance_client.get_symbol_ticker(symbol=ticker)['price'])
            else:
                ticker = yf.Ticker(symbol)
                price = ticker.history(period='1d')['Close'].iloc[-1]
            return price
        except Exception:
            return None
    
    def get_asset_history(self, symbol: str, asset_type: str, period: str = "1mo") -> pd.DataFrame:
        """Get historical data for an asset"""
        try:
            if asset_type.lower() == 'crypto':
                # Convert period to days for Binance API
                period_days = {
                    "1mo": "30 days ago UTC",
                    "1y": "365 days ago UTC",
                    "1d": "1 day ago UTC",
                    "1w": "7 days ago UTC"
                }.get(period, "30 days ago UTC")
                
                ticker = self.crypto_mapping.get(symbol.upper(), f"{symbol}USDT")
                klines = self.binance_client.get_historical_klines(
                    ticker,
                    Client.KLINE_INTERVAL_1DAY,
                    period_days
                )
                
                if not klines:
                    return pd.DataFrame()
                    
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'Open', 'High', 'Low', 'Close', 
                    'Volume', 'close_time', 'quote_av', 'trades',
                    'tb_base_av', 'tb_quote_av', 'ignore'
                ])
                
                # Convert timestamp to datetime and set as index
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Ensure index is timezone naive
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                
                # Convert price columns to float
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Keep only necessary columns to match yfinance format
                return df[['Open', 'High', 'Low', 'Close', 'Volume']]
            else:
                ticker = yf.Ticker(symbol)
                history = ticker.history(period=period)
                if history.empty:
                    return pd.DataFrame()
                
                # Ensure index is timezone naive
                if history.index.tz is not None:
                    history.index = history.index.tz_localize(None)
                
                # Keep only necessary columns
                return history[['Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception as e:
            print(f"Error fetching history for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray, volatility: float) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) == 0 or volatility == 0:
            return 0
        risk_free_rate = Config.DEFAULT_RISK_FREE_RATE
        excess_returns = np.mean(returns) - risk_free_rate
        return excess_returns / volatility if volatility > 0 else 0

import numpy as np
import pandas as pd
from typing import List, Dict, Any
import yfinance as yf
from scipy.optimize import minimize
from src.utils import calculate_technical_indicators, calculate_correlation

class FinancialAnalyzer:
    def __init__(self):
        self.risk_free_rate = 0.02  # 2% risk-free rate assumption
        
    def calculate_returns(self, prices: pd.Series) -> pd.Series:
        """Calculate daily returns"""
        if prices.empty:
            return pd.Series()
        # Ensure timezone-naive
        if isinstance(prices.index, pd.DatetimeIndex) and prices.index.tz is not None:
            prices.index = prices.index.tz_localize(None)
        return prices.pct_change().dropna()
    
    def calculate_beta(self, asset_returns: pd.Series, market_returns: pd.Series) -> float:
        """Calculate beta coefficient"""
        if asset_returns.empty or market_returns.empty:
            return 0.0
            
        # Ensure timezone-naive for both series
        if asset_returns.index.tz is not None:
            asset_returns.index = asset_returns.index.tz_localize(None)
        if market_returns.index.tz is not None:
            market_returns.index = market_returns.index.tz_localize(None)
            
        # Align the series
        asset_returns, market_returns = asset_returns.align(market_returns, join='inner')
        
        if len(asset_returns) < 2:
            return 0.0
            
        covariance = np.cov(asset_returns, market_returns)[0][1]
        market_variance = np.var(market_returns)
        
        return covariance / market_variance if market_variance != 0 else 0.0
    
    def calculate_alpha(self, asset_returns: pd.Series, market_returns: pd.Series, beta: float) -> float:
        """Calculate Jensen's Alpha"""
        if asset_returns.empty or market_returns.empty:
            return 0.0
            
        # Ensure timezone-naive
        if asset_returns.index.tz is not None:
            asset_returns.index = asset_returns.index.tz_localize(None)
        if market_returns.index.tz is not None:
            market_returns.index = market_returns.index.tz_localize(None)
            
        # Align the series
        asset_returns, market_returns = asset_returns.align(market_returns, join='inner')
        
        if len(asset_returns) < 2:
            return 0.0
            
        avg_asset_return = np.mean(asset_returns)
        avg_market_return = np.mean(market_returns)
        
        return avg_asset_return - (self.risk_free_rate + beta * (avg_market_return - self.risk_free_rate))
    
    def calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe Ratio"""
        if returns.empty:
            return 0.0
        if isinstance(returns.index, pd.DatetimeIndex) and returns.index.tz is not None:
            returns.index = returns.index.tz_localize(None)
        excess_returns = returns - self.risk_free_rate / 252  # Daily risk-free rate
        return np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) != 0 else 0.0
    
    def calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate Sortino Ratio"""
        if returns.empty:
            return 0.0
        if isinstance(returns.index, pd.DatetimeIndex) and returns.index.tz is not None:
            returns.index = returns.index.tz_localize(None)
        excess_returns = returns - self.risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
        return np.sqrt(252) * np.mean(excess_returns) / downside_std if downside_std != 0 else 0.0
    
    @staticmethod
    def calculate_technical_indicators(prices: pd.Series) -> Dict[str, float]:
        """Calculate various technical indicators"""
        return calculate_technical_indicators(prices)
    
    @staticmethod
    def calculate_correlation_matrix(assets: Dict[str, pd.Series]) -> pd.DataFrame:
        """Calculate correlation matrix between assets"""
        return calculate_correlation(assets)
    
    @staticmethod
    def optimize_portfolio(returns: pd.DataFrame, 
                         target_return: float = None,
                         risk_free_rate: float = 0.02) -> Dict[str, Any]:
        """Optimize portfolio weights using Modern Portfolio Theory"""
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        
        def portfolio_return(weights):
            return np.sum(returns.mean() * weights) * 252
        
        num_assets = len(returns.columns)
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # weights sum to 1
        ]
        
        if target_return is not None:
            constraints.append(
                {'type': 'eq', 'fun': lambda x: portfolio_return(x) - target_return}
            )
        
        bounds = tuple((0, 1) for _ in range(num_assets))
        
        # Minimize volatility
        result = minimize(portfolio_volatility,
                        num_assets * [1./num_assets],
                        method='SLSQP',
                        bounds=bounds,
                        constraints=constraints)
        
        optimal_weights = result.x
        opt_volatility = portfolio_volatility(optimal_weights)
        opt_return = portfolio_return(optimal_weights)
        sharpe = (opt_return - risk_free_rate) / opt_volatility
        
        return {
            'weights': dict(zip(returns.columns, optimal_weights)),
            'expected_return': opt_return,
            'volatility': opt_volatility,
            'sharpe_ratio': sharpe
        }
    
    @staticmethod
    def calculate_drawdown(returns: pd.Series) -> Dict[str, float]:
        """Calculate maximum drawdown and current drawdown"""
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdowns = cumulative / rolling_max - 1
        
        return {
            'max_drawdown': drawdowns.min(),
            'current_drawdown': drawdowns.iloc[-1]
        }
    
    @staticmethod
    def risk_assessment(portfolio_returns: List[float], 
                       market_returns: List[float] = None) -> Dict[str, Any]:
        """Comprehensive risk assessment"""
        if not portfolio_returns:
            return {
                'volatility': 0,
                'max_drawdown': 0,
                'value_at_risk': 0,
                'beta': 0,
                'alpha': 0,
                'sharpe_ratio': 0
            }
        
        returns_series = pd.Series(portfolio_returns)
        
        risk_metrics = {
            'volatility': np.std(portfolio_returns) * np.sqrt(252) * 100,
            'max_drawdown': FinancialAnalyzer.calculate_drawdown(returns_series)['max_drawdown'] * 100,
            'value_at_risk': np.percentile(portfolio_returns, 5) * 100,
            'sharpe_ratio': FinancialAnalyzer.calculate_sharpe_ratio(portfolio_returns)
        }
        
        if market_returns:
            risk_metrics.update({
                'beta': FinancialAnalyzer.calculate_beta(portfolio_returns, market_returns),
                'alpha': FinancialAnalyzer.calculate_alpha(portfolio_returns, market_returns)
            })
        
        return risk_metrics

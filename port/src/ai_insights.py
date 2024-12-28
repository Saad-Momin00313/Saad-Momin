import google.generativeai as genai
from typing import List, Dict, Any
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from textblob import TextBlob

class AIInvestmentAdvisor:
    def __init__(self, api_key: str):
        """Initialize Gemini AI client"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
    def analyze_market_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Analyze market sentiment using news and social media"""
        try:
            # Get news articles
            url = f"https://api.coingecko.com/api/v3/news?q={symbol}" if symbol in ['BTC', 'ETH'] else None
            if url:
                response = requests.get(url)
                if response.status_code == 200:
                    news = response.json()
                else:
                    news = []
            else:
                # Fallback to a general market sentiment
                news = []
            
            # Analyze sentiment
            sentiments = []
            for article in news:
                blob = TextBlob(article.get('title', '') + ' ' + article.get('description', ''))
                sentiments.append(blob.sentiment.polarity)
            
            if sentiments:
                avg_sentiment = np.mean(sentiments)
                sentiment_score = (avg_sentiment + 1) * 50  # Convert to 0-100 scale
            else:
                sentiment_score = 50  # Neutral
            
            # Determine sentiment category
            if sentiment_score >= 70:
                category = "Very Bullish"
            elif sentiment_score >= 55:
                category = "Bullish"
            elif sentiment_score >= 45:
                category = "Neutral"
            elif sentiment_score >= 30:
                category = "Bearish"
            else:
                category = "Very Bearish"
            
            return {
                'sentiment_score': sentiment_score,
                'sentiment_category': category,
                'confidence': min(abs(sentiment_score - 50) * 2, 100)
            }
        except Exception as e:
            return {
                'sentiment_score': 50,
                'sentiment_category': 'Neutral',
                'confidence': 0,
                'error': str(e)
            }

    def predict_price_movement(self, price_history, technical_indicators):
        """Predict price movement based on technical analysis"""
        if price_history is None or technical_indicators is None:
            return {
                'direction': 'Unknown',
                'confidence': 0.0,
                'analysis': 'Insufficient data for prediction'
            }
        
        try:
            current_price = price_history['Close'].iloc[-1]
            
            # Analyze technical indicators
            rsi = technical_indicators['rsi']
            sma_20 = technical_indicators['sma_20']
            sma_50 = technical_indicators['sma_50']
            macd = technical_indicators['macd']
            macd_signal = technical_indicators['macd_signal']
            
            # Initialize signals
            signals = []
            confidence_factors = []
            
            # RSI Analysis
            if rsi > 70:
                signals.append('Bearish')
                confidence_factors.append(0.7)
            elif rsi < 30:
                signals.append('Bullish')
                confidence_factors.append(0.7)
            else:
                signals.append('Neutral')
                confidence_factors.append(0.3)
            
            # Moving Average Analysis
            if current_price > sma_50:
                if current_price > sma_20:
                    signals.append('Bullish')
                    confidence_factors.append(0.8)
                else:
                    signals.append('Neutral')
                    confidence_factors.append(0.4)
            else:
                if current_price < sma_20:
                    signals.append('Bearish')
                    confidence_factors.append(0.8)
                else:
                    signals.append('Neutral')
                    confidence_factors.append(0.4)
            
            # MACD Analysis
            if macd > macd_signal:
                signals.append('Bullish')
                confidence_factors.append(0.6)
            else:
                signals.append('Bearish')
                confidence_factors.append(0.6)
            
            # Calculate overall direction and confidence
            bullish_count = signals.count('Bullish')
            bearish_count = signals.count('Bearish')
            
            if bullish_count > bearish_count:
                direction = 'Bullish'
                confidence = sum(cf for s, cf in zip(signals, confidence_factors) if s == 'Bullish') / len(confidence_factors) * 100
            elif bearish_count > bullish_count:
                direction = 'Bearish'
                confidence = sum(cf for s, cf in zip(signals, confidence_factors) if s == 'Bearish') / len(confidence_factors) * 100
            else:
                direction = 'Neutral'
                confidence = 50.0
            
            # Generate analysis text
            analysis = f"""Technical Analysis Summary:
            RSI ({rsi:.1f}): {'Overbought' if rsi > 70 else 'Oversold' if rsi < 30 else 'Neutral'}
            20-day SMA: {technical_indicators['sma_20']:.2f}
            50-day SMA: {technical_indicators['sma_50']:.2f}
            MACD: {macd:.2f} (Signal: {macd_signal:.2f})
            
            The asset is showing {direction.lower()} signals with {confidence:.1f}% confidence based on technical indicators.
            """
            
            return {
                'direction': direction,
                'confidence': confidence,
                'analysis': analysis
            }
            
        except Exception as e:
            return {
                'direction': 'Error',
                'confidence': 0.0,
                'analysis': f'Error analyzing price movement: {str(e)}'
            }

    def generate_portfolio_insights(self, portfolio_data: Dict[str, Any]) -> str:
        """Generate comprehensive portfolio insights"""
        prompt = f"""
        Analyze this portfolio data and provide actionable insights:
        
        Portfolio Value: ${portfolio_data['total_portfolio_value']:,.2f}
        
        Asset Allocation:
        {portfolio_data['asset_allocation']}
        
        Sector Allocation:
        {portfolio_data['sector_allocation']}
        
        Performance Metrics:
        - Volatility: {portfolio_data['performance_metrics']['volatility']:.1f}%
        - Sharpe Ratio: {portfolio_data['performance_metrics']['sharpe_ratio']:.2f}
        
        Risk Metrics:
        - Diversification: {portfolio_data['risk_metrics']['diversification_score']:.0f}%
        - Sector Concentration: {portfolio_data['risk_metrics']['sector_concentration']:.1f}%
        
        Provide detailed analysis on:
        1. Portfolio Health Assessment
        2. Risk Management Recommendations
        3. Diversification Opportunities
        4. Rebalancing Suggestions
        5. Sector Exposure Recommendations
        
        Keep recommendations specific and actionable.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Unable to generate portfolio insights: {str(e)}"

    def generate_recommendations(self, 
                               portfolio_details: Dict[str, Any],
                               market_conditions: Dict[str, Any]) -> str:
        """Generate specific investment recommendations"""
        prompt = f"""
        Based on:
        
        Portfolio Details:
        - Total Value: ${portfolio_details['total_portfolio_value']:,.2f}
        - Asset Allocation: {portfolio_details['asset_allocation']}
        - Risk Metrics: {portfolio_details['risk_metrics']}
        
        Market Conditions:
        - Sentiment: {market_conditions['market_sentiment']}
        - Monthly Return: {market_conditions['monthly_return']}
        
        Provide specific, actionable recommendations for:
        1. Portfolio Adjustments
        2. Risk Management Actions
        3. Market Timing Considerations
        4. Specific Assets to Consider
        
        Focus on practical, implementable suggestions.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Unable to generate recommendations: {str(e)}"

    def analyze_asset_trend(self, trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze asset trend and generate AI insights"""
        prompt = f"""
        Analyze these trend metrics:
        
        Recent Price History: {trend_data['price_history'][-5:]}
        Average Return: {trend_data['avg_return']:.2f}%
        Volatility: {trend_data['volatility']:.2f}%
        Momentum Score: {trend_data['momentum']:.2f}
        
        Determine the trend (Bullish/Bearish/Neutral) and confidence (0-100).
        Consider momentum, volatility, and recent price action.
        """
        
        try:
            response = self.model.generate_content(prompt)
            result = response.text.strip().lower()
            
            # Determine trend and confidence
            if "bullish" in result:
                trend = "Bullish"
                confidence = 80 if trend_data['momentum'] > 0.6 else 60
            elif "bearish" in result:
                trend = "Bearish"
                confidence = 80 if trend_data['momentum'] < 0.4 else 60
            else:
                trend = "Neutral"
                confidence = 50
            
            # Adjust confidence based on volatility
            if trend_data['volatility'] > 30:
                confidence = max(confidence - 20, 0)
            
            return {
                'trend': trend,
                'confidence': confidence,
                'analysis': response.text
            }
        except Exception as e:
            return {
                'trend': "Unknown",
                'confidence': 0,
                'analysis': f"Analysis error: {str(e)}"
            }

    def risk_recommendation(self, risk_metrics: Dict[str, Any]) -> str:
        """Generate risk-based recommendations"""
        prompt = f"""
        Analyze these risk metrics:
        {risk_metrics}
        
        Provide specific recommendations for:
        1. Risk Mitigation Strategies
        2. Portfolio Protection Measures
        3. Hedging Suggestions
        4. Volatility Management
        5. Correlation-based Diversification
        
        Focus on practical risk management actions.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Risk Analysis Error: {str(e)}"

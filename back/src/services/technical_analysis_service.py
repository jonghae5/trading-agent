"""Advanced technical analysis service using yfinance and technical indicators."""

import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import warnings
from src.models.base import get_kst_now

# Suppress yfinance warnings
warnings.filterwarnings('ignore', category=FutureWarning)

logger = logging.getLogger(__name__)


@dataclass
class TechnicalIndicator:
    """Technical indicator result."""
    name: str
    value: float
    signal: str  # 'bullish', 'bearish', 'neutral'
    strength: float  # 0-100
    description: str


@dataclass
class TechnicalAnalysisResult:
    """Complete technical analysis result."""
    ticker: str
    timestamp: datetime
    indicators: List[TechnicalIndicator]
    overall_signal: str
    confidence: float
    support_levels: List[float]
    resistance_levels: List[float]
    trend_direction: str
    volatility: float


class TechnicalAnalysisService:
    """Advanced technical analysis service."""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 900  # 15 minutes
    
    def _get_cache_key(self, ticker: str, period: str) -> str:
        """Generate cache key."""
        return f"{ticker}_{period}_{get_kst_now().strftime('%Y%m%d%H%M')}"
    
    def _is_cache_valid(self, cache_time: datetime) -> bool:
        """Check if cache is still valid."""
        return get_kst_now() - cache_time < timedelta(seconds=self.cache_duration)
    
    async def get_stock_data(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """Get stock data from yfinance."""
        try:
            # Run yfinance in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            stock = await loop.run_in_executor(
                None, 
                lambda: yf.Ticker(ticker).history(period=period)
            )
            
            if stock.empty:
                raise ValueError(f"No data found for ticker {ticker}")
            
            return stock
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            raise
    
    def calculate_sma(self, data: pd.Series, window: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return data.rolling(window=window).mean()
    
    def calculate_ema(self, data: pd.Series, window: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return data.ewm(span=window).mean()
    
    def calculate_rsi(self, data: pd.Series, window: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD indicator."""
        ema_fast = self.calculate_ema(data, fast)
        ema_slow = self.calculate_ema(data, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_bollinger_bands(self, data: pd.Series, window: int = 20, num_std: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands."""
        sma = self.calculate_sma(data, window)
        std = data.rolling(window=window).std()
        
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, k_window: int = 14, d_window: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator."""
        lowest_low = low.rolling(window=k_window).min()
        highest_high = high.rolling(window=k_window).max()
        
        k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d_percent = k_percent.rolling(window=d_window).mean()
        
        return {
            'k': k_percent,
            'd': d_percent
        }
    
    def calculate_williams_r(self, high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
        """Calculate Williams %R."""
        highest_high = high.rolling(window=window).max()
        lowest_low = low.rolling(window=window).min()
        
        williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
        return williams_r
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = high - low
        high_close_prev = np.abs(high - close.shift())
        low_close_prev = np.abs(low - close.shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close_prev, low_close_prev))
        atr = pd.Series(true_range).rolling(window=window).mean()
        
        return atr
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> Dict[str, pd.Series]:
        """Calculate Average Directional Index."""
        # Calculate True Range
        tr = self.calculate_atr(high, low, close, 1)
        
        # Calculate Directional Movement
        dm_plus = np.where((high - high.shift()) > (low.shift() - low), 
                          np.maximum(high - high.shift(), 0), 0)
        dm_minus = np.where((low.shift() - low) > (high - high.shift()), 
                           np.maximum(low.shift() - low, 0), 0)
        
        # Smooth the values
        tr_smooth = pd.Series(tr).rolling(window=window).mean()
        dm_plus_smooth = pd.Series(dm_plus).rolling(window=window).mean()
        dm_minus_smooth = pd.Series(dm_minus).rolling(window=window).mean()
        
        # Calculate DI
        di_plus = 100 * dm_plus_smooth / tr_smooth
        di_minus = 100 * dm_minus_smooth / tr_smooth
        
        # Calculate DX and ADX
        dx = 100 * np.abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(window=window).mean()
        
        return {
            'adx': adx,
            'di_plus': di_plus,
            'di_minus': di_minus
        }
    
    def calculate_fibonacci_retracements(self, data: pd.Series) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels."""
        high = data.max()
        low = data.min()
        
        difference = high - low
        
        return {
            'high': high,
            'low': low,
            '23.6%': high - 0.236 * difference,
            '38.2%': high - 0.382 * difference,
            '50%': high - 0.5 * difference,
            '61.8%': high - 0.618 * difference,
            '78.6%': high - 0.786 * difference
        }
    
    def find_support_resistance_levels(self, data: pd.Series, window: int = 20) -> Tuple[List[float], List[float]]:
        """Find support and resistance levels."""
        highs = []
        lows = []
        
        for i in range(window, len(data) - window):
            # Check for local maximum (resistance)
            if all(data.iloc[i] >= data.iloc[i-j] for j in range(1, window+1)) and \
               all(data.iloc[i] >= data.iloc[i+j] for j in range(1, window+1)):
                highs.append(data.iloc[i])
            
            # Check for local minimum (support)
            if all(data.iloc[i] <= data.iloc[i-j] for j in range(1, window+1)) and \
               all(data.iloc[i] <= data.iloc[i+j] for j in range(1, window+1)):
                lows.append(data.iloc[i])
        
        # Remove duplicates and sort
        support_levels = sorted(list(set(lows)))
        resistance_levels = sorted(list(set(highs)), reverse=True)
        
        return support_levels[-5:], resistance_levels[:5]  # Return top 5 of each
    
    def analyze_trend(self, data: pd.Series, short_window: int = 20, long_window: int = 50) -> str:
        """Analyze overall trend direction."""
        short_ma = self.calculate_sma(data, short_window).iloc[-1]
        long_ma = self.calculate_sma(data, long_window).iloc[-1]
        current_price = data.iloc[-1]
        
        if current_price > short_ma > long_ma:
            return "strong_uptrend"
        elif current_price > short_ma and short_ma < long_ma:
            return "weak_uptrend"
        elif current_price < short_ma < long_ma:
            return "strong_downtrend"
        elif current_price < short_ma and short_ma > long_ma:
            return "weak_downtrend"
        else:
            return "sideways"
    
    def calculate_volatility(self, data: pd.Series, window: int = 20) -> float:
        """Calculate volatility (standard deviation of returns)."""
        returns = data.pct_change().dropna()
        volatility = returns.rolling(window=window).std().iloc[-1]
        return volatility * np.sqrt(252) * 100  # Annualized volatility in percentage
    
    async def get_comprehensive_analysis(self, ticker: str, period: str = "6mo") -> TechnicalAnalysisResult:
        """Get comprehensive technical analysis for a ticker."""
        cache_key = self._get_cache_key(ticker, period)
        
        # Check cache
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if self._is_cache_valid(cache_entry['timestamp']):
                return cache_entry['result']
        
        try:
            # Get stock data
            df = await self.get_stock_data(ticker, period)
            
            if df.empty:
                raise ValueError(f"No data available for {ticker}")
            
            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume']
            
            indicators = []
            
            # RSI Analysis
            rsi = self.calculate_rsi(close)
            rsi_current = rsi.iloc[-1]
            if rsi_current > 70:
                rsi_signal = "bearish"
                rsi_strength = min((rsi_current - 70) * 3.33, 100)
            elif rsi_current < 30:
                rsi_signal = "bullish"
                rsi_strength = min((30 - rsi_current) * 3.33, 100)
            else:
                rsi_signal = "neutral"
                rsi_strength = 50 - abs(rsi_current - 50)
            
            indicators.append(TechnicalIndicator(
                name="RSI",
                value=rsi_current,
                signal=rsi_signal,
                strength=rsi_strength,
                description=f"RSI is {rsi_current:.2f}, indicating {'overbought' if rsi_current > 70 else 'oversold' if rsi_current < 30 else 'neutral'} conditions"
            ))
            
            # MACD Analysis
            macd_data = self.calculate_macd(close)
            macd_current = macd_data['macd'].iloc[-1]
            signal_current = macd_data['signal'].iloc[-1]
            histogram_current = macd_data['histogram'].iloc[-1]
            
            if macd_current > signal_current and histogram_current > 0:
                macd_signal = "bullish"
                macd_strength = min(abs(histogram_current) * 100, 100)
            elif macd_current < signal_current and histogram_current < 0:
                macd_signal = "bearish"
                macd_strength = min(abs(histogram_current) * 100, 100)
            else:
                macd_signal = "neutral"
                macd_strength = 50
            
            indicators.append(TechnicalIndicator(
                name="MACD",
                value=histogram_current,
                signal=macd_signal,
                strength=macd_strength,
                description=f"MACD histogram is {'positive' if histogram_current > 0 else 'negative'}, suggesting {'bullish' if histogram_current > 0 else 'bearish'} momentum"
            ))
            
            # Bollinger Bands Analysis
            bb = self.calculate_bollinger_bands(close)
            current_price = close.iloc[-1]
            upper_band = bb['upper'].iloc[-1]
            lower_band = bb['lower'].iloc[-1]
            middle_band = bb['middle'].iloc[-1]
            
            bb_position = (current_price - lower_band) / (upper_band - lower_band)
            
            if bb_position > 0.8:
                bb_signal = "bearish"
                bb_strength = (bb_position - 0.8) * 500
            elif bb_position < 0.2:
                bb_signal = "bullish"
                bb_strength = (0.2 - bb_position) * 500
            else:
                bb_signal = "neutral"
                bb_strength = 50 - abs(bb_position - 0.5) * 100
            
            indicators.append(TechnicalIndicator(
                name="Bollinger Bands",
                value=bb_position * 100,
                signal=bb_signal,
                strength=min(bb_strength, 100),
                description=f"Price is at {bb_position*100:.1f}% of Bollinger Band range"
            ))
            
            # Stochastic Oscillator
            stoch = self.calculate_stochastic(high, low, close)
            k_current = stoch['k'].iloc[-1]
            d_current = stoch['d'].iloc[-1]
            
            if k_current > 80 and d_current > 80:
                stoch_signal = "bearish"
                stoch_strength = min((k_current - 80) * 5, 100)
            elif k_current < 20 and d_current < 20:
                stoch_signal = "bullish"
                stoch_strength = min((20 - k_current) * 5, 100)
            else:
                stoch_signal = "neutral"
                stoch_strength = 50
            
            indicators.append(TechnicalIndicator(
                name="Stochastic",
                value=k_current,
                signal=stoch_signal,
                strength=stoch_strength,
                description=f"Stochastic %K is {k_current:.1f}, indicating {'overbought' if k_current > 80 else 'oversold' if k_current < 20 else 'neutral'} momentum"
            ))
            
            # ADX Trend Strength
            adx_data = self.calculate_adx(high, low, close)
            adx_current = adx_data['adx'].iloc[-1]
            di_plus = adx_data['di_plus'].iloc[-1]
            di_minus = adx_data['di_minus'].iloc[-1]
            
            if adx_current > 25:
                if di_plus > di_minus:
                    adx_signal = "bullish"
                else:
                    adx_signal = "bearish"
                adx_strength = min(adx_current * 2, 100)
            else:
                adx_signal = "neutral"
                adx_strength = adx_current * 2
            
            indicators.append(TechnicalIndicator(
                name="ADX",
                value=adx_current,
                signal=adx_signal,
                strength=adx_strength,
                description=f"ADX is {adx_current:.1f}, indicating {'strong' if adx_current > 25 else 'weak'} trend"
            ))
            
            # Williams %R
            williams_r = self.calculate_williams_r(high, low, close)
            williams_current = williams_r.iloc[-1]
            
            if williams_current > -20:
                williams_signal = "bearish"
                williams_strength = (williams_current + 20) * 5
            elif williams_current < -80:
                williams_signal = "bullish"
                williams_strength = (-80 - williams_current) * 5
            else:
                williams_signal = "neutral"
                williams_strength = 50
            
            indicators.append(TechnicalIndicator(
                name="Williams %R",
                value=williams_current,
                signal=williams_signal,
                strength=min(williams_strength, 100),
                description=f"Williams %R is {williams_current:.1f}, showing {'overbought' if williams_current > -20 else 'oversold' if williams_current < -80 else 'neutral'} conditions"
            ))
            
            # Calculate support and resistance levels
            support_levels, resistance_levels = self.find_support_resistance_levels(close)
            
            # Analyze trend
            trend_direction = self.analyze_trend(close)
            
            # Calculate volatility
            volatility = self.calculate_volatility(close)
            
            # Calculate overall signal
            bullish_signals = sum(1 for ind in indicators if ind.signal == "bullish")
            bearish_signals = sum(1 for ind in indicators if ind.signal == "bearish")
            
            if bullish_signals > bearish_signals + 1:
                overall_signal = "bullish"
                confidence = (bullish_signals / len(indicators)) * 100
            elif bearish_signals > bullish_signals + 1:
                overall_signal = "bearish"
                confidence = (bearish_signals / len(indicators)) * 100
            else:
                overall_signal = "neutral"
                confidence = 50
            
            # Adjust confidence based on trend strength
            if trend_direction in ["strong_uptrend", "strong_downtrend"]:
                confidence = min(confidence * 1.2, 100)
            elif trend_direction in ["weak_uptrend", "weak_downtrend"]:
                confidence = min(confidence * 1.1, 100)
            
            result = TechnicalAnalysisResult(
                ticker=ticker,
                timestamp=get_kst_now(),
                indicators=indicators,
                overall_signal=overall_signal,
                confidence=confidence,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                trend_direction=trend_direction,
                volatility=volatility
            )
            
            # Cache the result
            self.cache[cache_key] = {
                'result': result,
                'timestamp': get_kst_now()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in technical analysis for {ticker}: {e}")
            raise


# Global service instance
technical_analysis_service = TechnicalAnalysisService()


def get_technical_analysis_service() -> TechnicalAnalysisService:
    """Get the global technical analysis service instance."""
    return technical_analysis_service
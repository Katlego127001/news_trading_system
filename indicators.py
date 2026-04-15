"""
Technical indicators for trading strategies
"""

import numpy as np
import pandas as pd
from logger_config import logger

def calculate_ema(data, period):
    """Calculate Exponential Moving Average"""
    return pd.Series(data).ewm(span=period, adjust=False).mean().values

def calculate_sma(data, period):
    """Calculate Simple Moving Average"""
    return pd.Series(data).rolling(window=period).mean().values

def calculate_atr(high, low, close, period=14):
    """
    Calculate Average True Range
    
    Returns: ATR array
    """
    high = np.array(high)
    low = np.array(low)
    close = np.array(close)
    
    # True Range
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]  # First value
    
    # ATR using EMA
    atr = pd.Series(tr).ewm(span=period, adjust=False).mean().values
    
    return atr

def detect_consolidation(atr_values, threshold=0.7):
    """
    Detect if market is in consolidation
    
    Args:
        atr_values: Array of ATR values
        threshold: Ratio threshold (current ATR / average ATR)
    
    Returns:
        bool: True if consolidating
    """
    if len(atr_values) < 20:
        return False
    
    current_atr = atr_values[-1]
    avg_atr = np.mean(atr_values[-20:])
    
    ratio = current_atr / avg_atr if avg_atr > 0 else 1
    
    return ratio < threshold

def detect_volatility_expansion(atr_values, ratio=1.8):
    """
    Detect volatility expansion
    
    Args:
        atr_values: Array of ATR values
        ratio: Expansion ratio threshold
    
    Returns:
        bool: True if volatility expanded
    """
    if len(atr_values) < 10:
        return False
    
    current_atr = atr_values[-1]
    prev_avg_atr = np.mean(atr_values[-10:-1])
    
    expansion_ratio = current_atr / prev_avg_atr if prev_avg_atr > 0 else 1
    
    return expansion_ratio > ratio

def find_support_resistance(highs, lows, closes, lookback=50):
    """
    Find support and resistance levels
    
    Returns:
        dict: {'support': float, 'resistance': float}
    """
    if len(highs) < lookback:
        lookback = len(highs)
    
    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]
    recent_closes = closes[-lookback:]
    
    # Simple approach: recent high/low
    resistance = np.max(recent_highs)
    support = np.min(recent_lows)
    
    # Refine with close prices
    current_price = closes[-1]
    
    return {
        'resistance': resistance,
        'support': support,
        'current': current_price
    }

def is_strong_candle(open_price, close_price, high, low, ratio=0.6):
    """
    Check if candle has strong body (momentum)
    
    Args:
        ratio: Minimum body/total range ratio
    
    Returns:
        bool: True if strong candle
    """
    body = abs(close_price - open_price)
    total_range = high - low
    
    if total_range == 0:
        return False
    
    body_ratio = body / total_range
    
    return body_ratio >= ratio

def detect_breakout(current_price, support, resistance, atr, buffer=0.3):
    """
    Detect breakout from support/resistance
    
    Args:
        current_price: Current price
        support: Support level
        resistance: Resistance level
        atr: Current ATR value
        buffer: Buffer as ATR multiplier
    
    Returns:
        str: 'buy', 'sell', or None
    """
    buffer_value = atr * buffer
    
    if current_price > resistance + buffer_value:
        return 'buy'
    elif current_price < support - buffer_value:
        return 'sell'
    
    return None

def calculate_tick_volume_spike(volumes, threshold=1.5):
    """
    Detect volume spike
    
    Args:
        volumes: Array of tick volumes
        threshold: Spike ratio threshold
    
    Returns:
        bool: True if volume spike detected
    """
    if len(volumes) < 10:
        return False
    
    current_volume = volumes[-1]
    avg_volume = np.mean(volumes[-10:-1])
    
    if avg_volume == 0:
        return False
    
    volume_ratio = current_volume / avg_volume
    
    return volume_ratio > threshold

def ema_crossover(fast_ema, slow_ema):
    """
    Detect EMA crossover
    
    Returns:
        str: 'bullish', 'bearish', or None
    """
    if len(fast_ema) < 2 or len(slow_ema) < 2:
        return None
    
    # Current
    fast_current = fast_ema[-1]
    slow_current = slow_ema[-1]
    
    # Previous
    fast_prev = fast_ema[-2]
    slow_prev = slow_ema[-2]
    
    # Bullish crossover
    if fast_prev <= slow_prev and fast_current > slow_current:
        return 'bullish'
    
    # Bearish crossover
    if fast_prev >= slow_prev and fast_current < slow_current:
        return 'bearish'
    
    return None

class TechnicalAnalyzer:
    """Complete technical analysis for a symbol"""
    
    def __init__(self, symbol, candles_df):
        """
        Initialize with candles dataframe
        
        candles_df should have: time, open, high, low, close, tick_volume
        """
        self.symbol = symbol
        self.df = candles_df
    
    def analyze(self, atr_period=14, ema_fast=9, ema_slow=21):
        """
        Perform complete technical analysis
        
        Returns:
            dict: Analysis results
        """
        if len(self.df) < 50:
            logger.warning(f"Insufficient data for {self.symbol}: {len(self.df)} candles")
            return None
        
        # Calculate indicators
        atr = calculate_atr(
            self.df['high'].values,
            self.df['low'].values,
            self.df['close'].values,
            period=atr_period
        )
        
        ema_fast_values = calculate_ema(self.df['close'].values, ema_fast)
        ema_slow_values = calculate_ema(self.df['close'].values, ema_slow)
        
        # Find levels
        levels = find_support_resistance(
            self.df['high'].values,
            self.df['low'].values,
            self.df['close'].values
        )
        
        # Detect patterns
        is_consolidating = detect_consolidation(atr)
        volatility_expanding = detect_volatility_expansion(atr)
        volume_spike = calculate_tick_volume_spike(self.df['tick_volume'].values)
        
        # Check last candle strength
        last_candle = self.df.iloc[-1]
        strong_candle = is_strong_candle(
            last_candle['open'],
            last_candle['close'],
            last_candle['high'],
            last_candle['low']
        )
        
        # EMA crossover
        crossover = ema_crossover(ema_fast_values, ema_slow_values)
        
        # Breakout detection
        breakout_signal = detect_breakout(
            levels['current'],
            levels['support'],
            levels['resistance'],
            atr[-1]
        )
        
        return {
            'atr': atr[-1],
            'ema_fast': ema_fast_values[-1],
            'ema_slow': ema_slow_values[-1],
            'support': levels['support'],
            'resistance': levels['resistance'],
            'current_price': levels['current'],
            'is_consolidating': is_consolidating,
            'volatility_expanding': volatility_expanding,
            'volume_spike': volume_spike,
            'strong_candle': strong_candle,
            'ema_crossover': crossover,
            'breakout_signal': breakout_signal,
        }
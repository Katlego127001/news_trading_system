"""
Configuration file for News Trading System
"""

import os
from datetime import time

# ========================
# MT5 CONFIGURATION
# ========================
MT5_CONFIG = {
    'login': 435181777,  # Your MT5 account number
    'password': 'pwdord',
    'server': 'Exness-MT5Trial9',  # Your broker server
    'timeout': 60000,
    'portable': False
}

# ========================
# RISK MANAGEMENT
# ========================
RISK_CONFIG = {
    'risk_percent': 0.75,          # Risk per trade (% of balance)
    'max_loss_per_trade': 1.50,    # Max $ loss per trade
    'max_trades_per_day': 15,      # Max trades per day (all symbols)
    'max_trades_per_symbol': 3,    # Max trades per symbol per day
    'max_spread_pips': {
        'XAUUSDm': 0.50,
        'US30m': 3.0,
        'NAS100m': 2.5,
        'EURUSDm': 0.00020,
        'GBPUSDm': 0.00025,
        'default': 0.00030
    },
    'min_profit_breakeven': 1.0,   # Move to BE at $1 profit
    'trailing_start': 1.50,         # Start trailing at $1.50
    'trailing_step': 0.30,          # Trailing step in $
}

# ========================
# TRADING PARAMETERS
# ========================
TRADING_CONFIG = {
    'magic_number': 999888,
    'slippage': 10,
    'trade_comment': 'NewsBot_v1',
    'use_pending_orders': True,
    'pending_expiry_minutes': 15,
    'position_timeout_minutes': 30,  # Close position if no movement
}

# ========================
# NEWS FILTER
# ========================
NEWS_CONFIG = {
    'api_url': 'https://nfs.faireconomy.media/ff_calendar_thisweek.json',
    'update_interval': 300,  # Fetch news every 5 minutes
    'impact_filter': ['High', 'Medium'],  # Trade only High/Medium impact
    'pre_news_minutes': 15,   # Start monitoring 15 min before
    'post_news_minutes': 30,  # Monitor 30 min after news
    'avoid_minutes': 2,       # Don't trade 2 min before to 1 min after
    'blacklist_keywords': ['Holiday', 'Speech'],  # Skip these events
}

# ========================
# SYMBOL MAPPING
# ========================
CURRENCY_SYMBOLS = {
    'USD': ['XAUUSDm', 'US30m', 'NAS100m', 'EURUSDm', 'GBPUSDm', 'USDJPYm', 'USDCADm', 'USDCHFm'],
    'EUR': ['EURUSDm', 'EURJPYm', 'EURGBPm'],
    'GBP': ['GBPUSDm', 'GBPJPYm', 'EURGBPm'],
    'JPY': ['USDJPYm', 'EURJPYm', 'GBPJPYm'],
    'AUD': ['AUDUSDm', 'AUDJPYm'],
    'NZD': ['NZDUSDm'],
    'CAD': ['USDCADm'],
    'CHF': ['USDCHFm'],
    'CNY': ['XAUUSDm'],
    'ALL': ['XAUUSDm', 'US30m', 'NAS100m'],
}

# Priority symbols (always monitor)
PRIORITY_SYMBOLS = ['XAUUSDm', 'US30m', 'NAS100m', 'EURUSDm']

# ========================
# STRATEGY PARAMETERS
# ========================
STRATEGY_CONFIG = {
    'atr_period': 14,
    'atr_multiplier': 1.5,
    'ema_fast': 9,
    'ema_slow': 21,
    'consolidation_threshold': 0.7,  # ATR ratio for consolidation
    'volatility_expansion_ratio': 1.8,  # Post-news volatility spike
    'breakout_buffer_atr': 0.3,
    'min_candle_body_ratio': 0.6,  # For momentum confirmation
    'volume_spike_ratio': 1.5,
}

# ========================
# TRADING SESSIONS (UTC)
# ========================
TRADING_SESSIONS = {
    'london': {'start': time(7, 0), 'end': time(16, 0)},
    'new_york': {'start': time(13, 0), 'end': time(22, 0)},
}

ACTIVE_SESSIONS = ['london', 'new_york']  # Trade only during these sessions

# ========================
# TELEGRAM CONFIGURATION
# ========================
TELEGRAM_CONFIG = {
    'enabled': True,
    'bot_token': 'BotToken-dPg',  # Get from @BotFather
    'chat_id': 'Chat ID',      # Your Telegram chat ID
    'send_on_trade': True,
    'send_on_error': True,
    'send_daily_summary': True,
}

# ========================
# LOGGING
# ========================
LOG_CONFIG = {
    'log_level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'log_to_file': True,
    'log_to_console': True,
    'log_file': 'trading_bot.log',
    'trade_journal': 'trades.csv',
}

# ========================
# AI/ADAPTIVE SETTINGS
# ========================
AI_CONFIG = {
    'enabled': True,
    'learning_window': 50,  # Last N trades for analysis
    'winning_streak_boost': 1.2,  # Increase lot size by 20%
    'losing_streak_reduction': 0.7,  # Reduce lot size by 30%
    'streak_threshold': 3,  # Consecutive wins/losses
    'high_volatility_events': ['CPI', 'NFP', 'PPI', 'GDP', 'Interest Rate', 'FOMC'],
}

# ========================
# SYMBOL-SPECIFIC OPTIMIZATIONS
# ========================
SYMBOL_OPTIMIZATIONS = {
    'XAUUSDm': {
        'risk_percent': 0.5,
        'atr_multiplier': 2.0,
        'min_profit_breakeven': 1.5,
        'use_dxy_correlation': True,
    },
    'US30m': {
        'risk_percent': 0.75,
        'atr_multiplier': 1.5,
        'min_profit_breakeven': 2.0,
    },
    'NAS100m': {
        'risk_percent': 0.6,
        'atr_multiplier': 1.8,
    },
    'EURUSDm': {
        'risk_percent': 1.0,
        'atr_multiplier': 1.2,
    },
}

# ========================
# PATHS
# ========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Create directories if they don't exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
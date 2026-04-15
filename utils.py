"""
Utility functions for the trading system
"""

import csv
import os
from datetime import datetime, time
import MetaTrader5 as mt5
from config import LOGS_DIR, LOG_CONFIG, TRADING_SESSIONS, ACTIVE_SESSIONS
from logger_config import logger

def get_pip_value(symbol):
    """Get pip value for a symbol"""
    if 'JPY' in symbol:
        return 0.01
    elif any(idx in symbol for idx in ['XAU', 'XAG', 'BTC']):
        return 0.01
    elif any(idx in symbol for idx in ['US30', 'NAS100', 'SPX']):
        return 1.0
    else:
        return 0.0001

def get_point_value(symbol):
    """Get point value (minimum price change)"""
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info:
        return symbol_info.point
    return get_pip_value(symbol) / 10

def is_trading_session():
    """Check if current time is within active trading sessions"""
    current_time = datetime.utcnow().time()
    
    for session_name in ACTIVE_SESSIONS:
        if session_name in TRADING_SESSIONS:
            session = TRADING_SESSIONS[session_name]
            if session['start'] <= current_time <= session['end']:
                return True
    return False

def save_trade_to_journal(trade_data):
    """Save trade to CSV journal"""
    journal_file = os.path.join(LOGS_DIR, LOG_CONFIG['trade_journal'])
    
    file_exists = os.path.isfile(journal_file)
    
    with open(journal_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=trade_data.keys())
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(trade_data)
    
    logger.info(f"Trade saved to journal: {trade_data.get('symbol', 'N/A')}")

def calculate_lot_size(symbol, account_balance, risk_amount, stop_loss_pips):
    """
    Calculate lot size based on risk
    
    Args:
        symbol: Trading symbol
        account_balance: Account balance
        risk_amount: Dollar amount to risk
        stop_loss_pips: Stop loss in pips
    
    Returns:
        float: Lot size
    """
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        logger.error(f"Symbol info not available for {symbol}")
        return 0.01
    
    # Get contract size
    contract_size = symbol_info.trade_contract_size
    
    # Get pip value
    pip_value = get_pip_value(symbol)
    
    # Calculate lot size
    # For forex: lot_size = risk / (stop_loss_pips * pip_value * contract_size / point)
    if stop_loss_pips == 0:
        return symbol_info.volume_min
    
    # Calculate value per lot per pip
    tick_value = symbol_info.trade_tick_value
    tick_size = symbol_info.trade_tick_size
    
    value_per_pip = (pip_value / tick_size) * tick_value if tick_size > 0 else 10
    
    lot_size = risk_amount / (stop_loss_pips * value_per_pip)
    
    # Round to step
    lot_step = symbol_info.volume_step
    lot_size = round(lot_size / lot_step) * lot_step
    
    # Ensure within limits
    lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))
    
    return round(lot_size, 2)

def get_spread(symbol):
    """Get current spread in pips"""
    symbol_info = mt5.symbol_info_tick(symbol)
    if symbol_info:
        spread = symbol_info.ask - symbol_info.bid
        pip_value = get_pip_value(symbol)
        return spread / pip_value
    return 999  # High value if unable to get spread

def format_price(symbol, price):
    """Format price based on symbol digits"""
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info:
        return round(price, symbol_info.digits)
    return round(price, 5)

class PerformanceTracker:
    """Track trading performance"""
    
    def __init__(self):
        self.trades = []
        self.daily_trades = 0
        self.daily_profit = 0.0
        self.symbol_trades = {}
        self.last_reset = datetime.now().date()
    
    def reset_daily(self):
        """Reset daily counters"""
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_trades = 0
            self.daily_profit = 0.0
            self.symbol_trades = {}
            self.last_reset = today
            logger.info("Daily performance counters reset")
    
    def add_trade(self, symbol, profit, outcome):
        """Add trade to tracking"""
        self.reset_daily()
        
        self.trades.append({
            'symbol': symbol,
            'profit': profit,
            'outcome': outcome,
            'time': datetime.now()
        })
        
        self.daily_trades += 1
        self.daily_profit += profit
        
        if symbol not in self.symbol_trades:
            self.symbol_trades[symbol] = 0
        self.symbol_trades[symbol] += 1
    
    def get_symbol_trades_today(self, symbol):
        """Get number of trades for symbol today"""
        self.reset_daily()
        return self.symbol_trades.get(symbol, 0)
    
    def get_daily_trades(self):
        """Get total trades today"""
        self.reset_daily()
        return self.daily_trades
    
    def get_recent_performance(self, window=50):
        """Get performance for last N trades"""
        recent = self.trades[-window:] if len(self.trades) > window else self.trades
        
        if not recent:
            return {'win_rate': 0, 'profit_factor': 0, 'total_profit': 0}
        
        wins = [t for t in recent if t['outcome'] == 'win']
        losses = [t for t in recent if t['outcome'] == 'loss']
        
        win_rate = len(wins) / len(recent) * 100 if recent else 0
        
        total_profit = sum(t['profit'] for t in wins)
        total_loss = abs(sum(t['profit'] for t in losses))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_profit': sum(t['profit'] for t in recent),
            'trades': len(recent)
        }
    
    def get_consecutive_streak(self):
        """Get current winning/losing streak"""
        if not self.trades:
            return 0
        
        recent = self.trades[-10:]
        streak = 0
        last_outcome = recent[-1]['outcome']
        
        for trade in reversed(recent):
            if trade['outcome'] == last_outcome:
                streak += 1
            else:
                break
        
        return streak if last_outcome == 'win' else -streak

# Global performance tracker
performance_tracker = PerformanceTracker()
"""
Risk Management System
"""

import MetaTrader5 as mt5
from config import RISK_CONFIG, SYMBOL_OPTIMIZATIONS, AI_CONFIG
from logger_config import logger
from utils import get_pip_value, calculate_lot_size, performance_tracker

class RiskManager:
    """Manage trading risk and position sizing"""
    
    def __init__(self):
        self.risk_percent = RISK_CONFIG['risk_percent']
        self.max_loss_per_trade = RISK_CONFIG['max_loss_per_trade']
        self.max_trades_per_day = RISK_CONFIG['max_trades_per_day']
        self.max_trades_per_symbol = RISK_CONFIG['max_trades_per_symbol']
    
    def get_account_balance(self):
        """Get current account balance"""
        account_info = mt5.account_info()
        if account_info:
            return account_info.balance
        return 0
    
    def calculate_risk_amount(self, symbol=None):
        """
        Calculate dollar amount to risk per trade
        
        Args:
            symbol: Trading symbol (for symbol-specific settings)
        
        Returns:
            float: Risk amount in dollars
        """
        balance = self.get_account_balance()
        
        # Get symbol-specific risk if available
        risk_pct = self.risk_percent
        if symbol and symbol in SYMBOL_OPTIMIZATIONS:
            risk_pct = SYMBOL_OPTIMIZATIONS[symbol].get('risk_percent', self.risk_percent)
        
        # Apply AI adjustments
        if AI_CONFIG['enabled']:
            risk_pct = self._apply_ai_risk_adjustment(risk_pct)
        
        risk_amount = balance * (risk_pct / 100)
        
        # Cap at max loss per trade
        risk_amount = min(risk_amount, self.max_loss_per_trade)
        
        logger.debug(f"Risk amount: ${risk_amount:.2f} ({risk_pct}% of ${balance:.2f})")
        
        return risk_amount
    
    def _apply_ai_risk_adjustment(self, base_risk_pct):
        """
        Adjust risk based on recent performance
        
        Args:
            base_risk_pct: Base risk percentage
        
        Returns:
            float: Adjusted risk percentage
        """
        streak = performance_tracker.get_consecutive_streak()
        threshold = AI_CONFIG['streak_threshold']
        
        adjusted_risk = base_risk_pct
        
        # Winning streak - increase risk
        if streak >= threshold:
            adjusted_risk *= AI_CONFIG['winning_streak_boost']
            logger.info(f"Winning streak detected ({streak}), increasing risk to {adjusted_risk:.2f}%")
        
        # Losing streak - decrease risk
        elif streak <= -threshold:
            adjusted_risk *= AI_CONFIG['losing_streak_reduction']
            logger.info(f"Losing streak detected ({streak}), reducing risk to {adjusted_risk:.2f}%")
        
        # Ensure within reasonable bounds
        adjusted_risk = max(0.3, min(adjusted_risk, 2.0))
        
        return adjusted_risk
    
    def calculate_position_size(self, symbol, entry_price, stop_loss_price):
        """
        Calculate position size (lot size)
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss_price: Stop loss price
        
        Returns:
            float: Lot size
        """
        risk_amount = self.calculate_risk_amount(symbol)
        
        # Calculate stop loss in pips
        pip_value = get_pip_value(symbol)
        sl_distance = abs(entry_price - stop_loss_price)
        sl_pips = sl_distance / pip_value
        
        # Calculate lot size
        lot_size = calculate_lot_size(
            symbol,
            self.get_account_balance(),
            risk_amount,
            sl_pips
        )
        
        logger.info(f"{symbol} - Risk: ${risk_amount:.2f}, SL: {sl_pips:.1f} pips, Lot: {lot_size}")
        
        return lot_size
    
    def can_open_trade(self, symbol):
        """
        Check if allowed to open new trade
        
        Args:
            symbol: Trading symbol
        
        Returns:
            bool: True if can trade
        """
        # Check daily trade limit
        daily_trades = performance_tracker.get_daily_trades()
        if daily_trades >= self.max_trades_per_day:
            logger.warning(f"Daily trade limit reached: {daily_trades}/{self.max_trades_per_day}")
            return False
        
        # Check symbol-specific limit
        symbol_trades = performance_tracker.get_symbol_trades_today(symbol)
        if symbol_trades >= self.max_trades_per_symbol:
            logger.warning(f"{symbol} trade limit reached: {symbol_trades}/{self.max_trades_per_symbol}")
            return False
        
        # Check if position already open on symbol
        positions = mt5.positions_get(symbol=symbol)
        if positions and len(positions) > 0:
            logger.warning(f"{symbol} already has open position")
            return False
        
        return True
    
    def check_spread(self, symbol):
        """
        Check if spread is acceptable
        
        Args:
            symbol: Trading symbol
        
        Returns:
            bool: True if spread is acceptable
        """
        symbol_info = mt5.symbol_info_tick(symbol)
        if not symbol_info:
            logger.error(f"Could not get symbol info for {symbol}")
            return False
        
        spread = symbol_info.ask - symbol_info.bid
        pip_value = get_pip_value(symbol)
        spread_pips = spread / pip_value
        
        # Get max spread for symbol
        max_spread = RISK_CONFIG['max_spread_pips'].get(
            symbol,
            RISK_CONFIG['max_spread_pips']['default']
        )
        
        if spread_pips > max_spread:
            logger.warning(f"{symbol} spread too high: {spread_pips:.2f} pips (max: {max_spread})")
            return False
        
        return True
    
    def calculate_sl_tp(self, symbol, entry_price, direction, atr):
        """
        Calculate stop loss and take profit
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            direction: 'buy' or 'sell'
            atr: ATR value
        
        Returns:
            tuple: (stop_loss, take_profit)
        """
        # Get symbol-specific ATR multiplier
        atr_mult = SYMBOL_OPTIMIZATIONS.get(symbol, {}).get(
            'atr_multiplier',
            RISK_CONFIG.get('atr_multiplier', 1.5)
        )
        
        sl_distance = atr * atr_mult
        tp_distance = atr * atr_mult * 2  # 2:1 RR
        
        if direction == 'buy':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:  # sell
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        
        # Format prices
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info:
            digits = symbol_info.digits
            stop_loss = round(stop_loss, digits)
            take_profit = round(take_profit, digits)
        
        return stop_loss, take_profit
    
    def should_move_to_breakeven(self, position):
        """
        Check if should move SL to breakeven
        
        Args:
            position: MT5 position object
        
        Returns:
            bool: True if should move to BE
        """
        profit = position.profit
        min_profit = SYMBOL_OPTIMIZATIONS.get(position.symbol, {}).get(
            'min_profit_breakeven',
            RISK_CONFIG['min_profit_breakeven']
        )
        
        # Check if already at breakeven
        if position.type == mt5.ORDER_TYPE_BUY:
            if position.sl >= position.price_open:
                return False
        else:
            if position.sl <= position.price_open:
                return False
        
        return profit >= min_profit
    
    def calculate_trailing_stop(self, position, current_price):
        """
        Calculate trailing stop level
        
        Args:
            position: MT5 position object
            current_price: Current market price
        
        Returns:
            float: New SL level or None
        """
        profit = position.profit
        
        if profit < RISK_CONFIG['trailing_start']:
            return None
        
        trailing_step = RISK_CONFIG['trailing_step']
        
        # Calculate new SL
        if position.type == mt5.ORDER_TYPE_BUY:
            # For buy, trail below current price
            new_sl = current_price - (trailing_step / 100 * current_price)
            
            # Only move SL up
            if new_sl > position.sl:
                return round(new_sl, mt5.symbol_info(position.symbol).digits)
        
        else:  # SELL
            # For sell, trail above current price
            new_sl = current_price + (trailing_step / 100 * current_price)
            
            # Only move SL down
            if new_sl < position.sl:
                return round(new_sl, mt5.symbol_info(position.symbol).digits)
        
        return None

# Global risk manager instance
risk_manager = RiskManager()
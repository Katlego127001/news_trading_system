"""
MT5 Trade Execution Engine
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
from config import MT5_CONFIG, TRADING_CONFIG
from logger_config import logger
from telegram_notifier import notifier
from utils import save_trade_to_journal, performance_tracker, format_price

class TradeExecutor:
    """Execute trades on MT5"""
    
    def __init__(self):
        self.magic_number = TRADING_CONFIG['magic_number']
        self.comment = TRADING_CONFIG['trade_comment']
        self.slippage = TRADING_CONFIG['slippage']
        self.initialized = False
    
    def initialize(self):
        """Initialize MT5 connection"""
        if self.initialized:
            return True
        
        if not mt5.initialize():
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        # Login
        authorized = mt5.login(
            MT5_CONFIG['login'],
            password=MT5_CONFIG['password'],
            server=MT5_CONFIG['server']
        )
        
        if not authorized:
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False
        
        account_info = mt5.account_info()
        if account_info:
            logger.info(f"Connected to MT5 - Account: {account_info.login}, Balance: ${account_info.balance:.2f}")
            self.initialized = True
            return True
        
        return False
    
    def shutdown(self):
        """Shutdown MT5 connection"""
        mt5.shutdown()
        self.initialized = False
        logger.info("MT5 connection closed")
    
    def place_market_order(self, symbol, order_type, volume, sl=None, tp=None, reason=""):
        """
        Place market order
        
        Args:
            symbol: Trading symbol
            order_type: mt5.ORDER_TYPE_BUY or mt5.ORDER_TYPE_SELL
            volume: Lot size
            sl: Stop loss price
            tp: Take profit price
            reason: Trade reason/strategy
        
        Returns:
            OrderSendResult or None
        """
        if not self.initialized:
            logger.error("MT5 not initialized")
            return None
        
        # Prepare request
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            logger.error(f"Symbol {symbol} not found")
            return None
        
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                logger.error(f"Failed to select {symbol}")
                return None
        
        # Get price
        if order_type == mt5.ORDER_TYPE_BUY:
            price = mt5.symbol_info_tick(symbol).ask
        else:
            price = mt5.symbol_info_tick(symbol).bid
        
        # Prepare request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "slippage": self.slippage,
            "magic": self.magic_number,
            "comment": self.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Add SL/TP if provided
        if sl:
            request["sl"] = format_price(symbol, sl)
        if tp:
            request["tp"] = format_price(symbol, tp)
        
        # Send order
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.retcode} - {result.comment}")
            notifier.notify_error(f"Order failed for {symbol}: {result.comment}")
            return None
        
        logger.info(f"Order placed: {symbol} {'BUY' if order_type == mt5.ORDER_TYPE_BUY else 'SELL'} {volume} @ {price}")
        
        # Send notification
        notifier.notify_trade_opened({
            'symbol': symbol,
            'type': 'BUY' if order_type == mt5.ORDER_TYPE_BUY else 'SELL',
            'entry': price,
            'sl': sl,
            'tp': tp,
            'volume': volume,
            'reason': reason
        })
        
        # Save to journal
        save_trade_to_journal({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'type': 'BUY' if order_type == mt5.ORDER_TYPE_BUY else 'SELL',
            'volume': volume,
            'entry': price,
            'sl': sl,
            'tp': tp,
            'reason': reason,
            'ticket': result.order
        })
        
        return result
    
    def place_pending_order(self, symbol, order_type, price, volume, sl=None, tp=None, expiry_minutes=15):
        """
        Place pending order (Buy Stop / Sell Stop)
        
        Args:
            symbol: Trading symbol
            order_type: mt5.ORDER_TYPE_BUY_STOP or mt5.ORDER_TYPE_SELL_STOP
            price: Order price
            volume: Lot size
            sl: Stop loss
            tp: Take profit
            expiry_minutes: Order expiry in minutes
        
        Returns:
            OrderSendResult or None
        """
        if not self.initialized:
            logger.error("MT5 not initialized")
            return None
        
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            logger.error(f"Symbol {symbol} not found")
            return None
        
        # Calculate expiry time
        expiry = datetime.now() + timedelta(minutes=expiry_minutes)
        
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": format_price(symbol, price),
            "slippage": self.slippage,
            "magic": self.magic_number,
            "comment": self.comment,
            "type_time": mt5.ORDER_TIME_SPECIFIED,
            "expiration": int(expiry.timestamp()),
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        
        if sl:
            request["sl"] = format_price(symbol, sl)
        if tp:
            request["tp"] = format_price(symbol, tp)
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Pending order failed: {result.retcode} - {result.comment}")
            return None
        
        logger.info(f"Pending order placed: {symbol} @ {price} (expires in {expiry_minutes} min)")
        
        return result
    
    def modify_position(self, ticket, sl=None, tp=None):
        """
        Modify position SL/TP
        
        Args:
            ticket: Position ticket
            sl: New stop loss
            tp: New take profit
        
        Returns:
            bool: Success
        """
        position = mt5.positions_get(ticket=ticket)
        if not position:
            logger.error(f"Position {ticket} not found")
            return False
        
        position = position[0]
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": ticket,
            "magic": self.magic_number,
        }
        
        if sl is not None:
            request["sl"] = format_price(position.symbol, sl)
        else:
            request["sl"] = position.sl
        
        if tp is not None:
            request["tp"] = format_price(position.symbol, tp)
        else:
            request["tp"] = position.tp
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Position modify failed: {result.retcode}")
            return False
        
        logger.info(f"Position {ticket} modified - SL: {request['sl']}, TP: {request['tp']}")
        
        return True
    
    def close_position(self, ticket, reason="Manual"):
        """
        Close position
        
        Args:
            ticket: Position ticket
            reason: Close reason
        
        Returns:
            bool: Success
        """
        position = mt5.positions_get(ticket=ticket)
        if not position:
            logger.warning(f"Position {ticket} not found")
            return False
        
        position = position[0]
        
        # Determine close type
        if position.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(position.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(position.symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "slippage": self.slippage,
            "magic": self.magic_number,
            "comment": f"Close: {reason}",
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Position close failed: {result.retcode}")
            return False
        
        # Calculate duration
        open_time = datetime.fromtimestamp(position.time)
        duration = (datetime.now() - open_time).total_seconds() / 60
        
        # Determine outcome
        outcome = 'win' if position.profit > 0 else 'loss'
        
        # Track performance
        performance_tracker.add_trade(position.symbol, position.profit, outcome)
        
        logger.info(f"Position closed: {position.symbol} - Profit: ${position.profit:.2f} - Duration: {duration:.1f} min")
        
        # Send notification
        notifier.notify_trade_closed({
            'symbol': position.symbol,
            'profit': position.profit,
            'entry': position.price_open,
            'exit': price,
            'duration': f"{duration:.1f}",
            'outcome': outcome.upper()
        })
        
        return True
    
    def cancel_pending_order(self, ticket):
        """Cancel pending order"""
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Pending order {ticket} cancelled")
            return True
        
        logger.error(f"Failed to cancel order {ticket}")
        return False
    
    def get_open_positions(self, symbol=None):
        """Get open positions"""
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        return positions if positions else []
    
    def get_pending_orders(self, symbol=None):
        """Get pending orders"""
        if symbol:
            orders = mt5.orders_get(symbol=symbol)
        else:
            orders = mt5.orders_get()
        
        return orders if orders else []

# Global trade executor instance
trade_executor = TradeExecutor()
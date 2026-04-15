"""
Trading Strategies
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from config import (
    STRATEGY_CONFIG, NEWS_CONFIG, TRADING_CONFIG,
    SYMBOL_OPTIMIZATIONS, AI_CONFIG
)
from logger_config import logger
from indicators import TechnicalAnalyzer
from risk_manager import risk_manager
from trade_executor import trade_executor
from news_parser import news_parser
from utils import get_pip_value

class NewsStrategy:
    """News-driven trading strategy"""
    
    def __init__(self, symbol):
        self.symbol = symbol
        self.timeframe = mt5.TIMEFRAME_M5
        self.active_trades = {}
    
    def get_candles(self, count=100):
        """Fetch recent candles"""
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, count)
        
        if rates is None or len(rates) == 0:
            logger.error(f"Failed to get candles for {self.symbol}")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        return df
    
    def analyze_pre_news(self):
        """
        Pre-news analysis (T-15 to T-5 minutes)
        
        Returns:
            dict: Analysis results or None
        """
        # Get candles
        candles = self.get_candles(100)
        if candles is None:
            return None
        
        # Technical analysis
        analyzer = TechnicalAnalyzer(self.symbol, candles)
        analysis = analyzer.analyze()
        
        if not analysis:
            return None
        
        # Check consolidation
        if not analysis['is_consolidating']:
            logger.debug(f"{self.symbol} not consolidating - skipping pre-news setup")
            return None
        
        # Check spread
        if not risk_manager.check_spread(self.symbol):
            return None
        
        logger.info(f"{self.symbol} PRE-NEWS: Consolidating, Support: {analysis['support']:.5f}, Resistance: {analysis['resistance']:.5f}")
        
        return analysis
    
    def execute_straddle_strategy(self, analysis, event):
        """
        Execute straddle strategy (pending orders above/below)
        
        Args:
            analysis: Technical analysis results
            event: News event dict
        """
        if not TRADING_CONFIG['use_pending_orders']:
            logger.debug("Pending orders disabled in config")
            return
        
        if not risk_manager.can_open_trade(self.symbol):
            return
        
        # Calculate entry levels
        atr = analysis['atr']
        buffer = atr * STRATEGY_CONFIG['breakout_buffer_atr']
        
        buy_price = analysis['resistance'] + buffer
        sell_price = analysis['support'] - buffer
        
        # Calculate position size
        current_price = analysis['current_price']
        
        # For buy stop
        buy_sl, buy_tp = risk_manager.calculate_sl_tp(
            self.symbol, buy_price, 'buy', atr
        )
        buy_volume = risk_manager.calculate_position_size(
            self.symbol, buy_price, buy_sl
        )
        
        # For sell stop
        sell_sl, sell_tp = risk_manager.calculate_sl_tp(
            self.symbol, sell_price, 'sell', atr
        )
        sell_volume = risk_manager.calculate_position_size(
            self.symbol, sell_price, sell_sl
        )
        
        # Place pending orders
        logger.info(f"{self.symbol} STRADDLE: Buy @ {buy_price:.5f}, Sell @ {sell_price:.5f}")
        
        buy_order = trade_executor.place_pending_order(
            self.symbol,
            mt5.ORDER_TYPE_BUY_STOP,
            buy_price,
            buy_volume,
            buy_sl,
            buy_tp,
            TRADING_CONFIG['pending_expiry_minutes']
        )
        
        sell_order = trade_executor.place_pending_order(
            self.symbol,
            mt5.ORDER_TYPE_SELL_STOP,
            sell_price,
            sell_volume,
            sell_sl,
            sell_tp,
            TRADING_CONFIG['pending_expiry_minutes']
        )
        
        # Track orders
        if buy_order and sell_order:
            self.active_trades[self.symbol] = {
                'buy_ticket': buy_order.order,
                'sell_ticket': sell_order.order,
                'event': event.get('title', ''),
                'time': datetime.now()
            }
    
    def check_straddle_triggered(self):
        """Check if straddle order triggered and cancel opposite"""
        if self.symbol not in self.active_trades:
            return
        
        trade_info = self.active_trades[self.symbol]
        
        # Check if any order became a position
        positions = trade_executor.get_open_positions(self.symbol)
        
        if positions and len(positions) > 0:
            # One order triggered - cancel the other
            pending_orders = trade_executor.get_pending_orders(self.symbol)
            
            for order in pending_orders:
                if order.ticket in [trade_info['buy_ticket'], trade_info['sell_ticket']]:
                    trade_executor.cancel_pending_order(order.ticket)
                    logger.info(f"{self.symbol} straddle triggered - cancelled opposite order")
            
            # Remove from tracking
            del self.active_trades[self.symbol]
    
    def execute_momentum_entry(self, analysis, direction, event):
        """
        Execute momentum entry (post-news breakout)
        
        Args:
            analysis: Technical analysis
            direction: 'buy' or 'sell'
            event: News event
        """
        if not risk_manager.can_open_trade(self.symbol):
            return
        
        # Confirm breakout
        if not analysis['strong_candle']:
            logger.debug(f"{self.symbol} weak candle - skipping momentum entry")
            return
        
        if not analysis['volume_spike']:
            logger.debug(f"{self.symbol} no volume spike - skipping")
            return
        
        # Check EMA alignment
        ema_crossover = analysis.get('ema_crossover')
        
        if direction == 'buy' and ema_crossover != 'bullish':
            if analysis['ema_fast'] <= analysis['ema_slow']:
                logger.debug(f"{self.symbol} EMA not aligned for buy")
                return
        
        if direction == 'sell' and ema_crossover != 'bearish':
            if analysis['ema_fast'] >= analysis['ema_slow']:
                logger.debug(f"{self.symbol} EMA not aligned for sell")
                return
        
        # Get entry price
        tick = mt5.symbol_info_tick(self.symbol)
        if not tick:
            return
        
        entry_price = tick.ask if direction == 'buy' else tick.bid
        
        # Calculate SL/TP
        atr = analysis['atr']
        sl, tp = risk_manager.calculate_sl_tp(self.symbol, entry_price, direction, atr)
        
        # Calculate lot size
        volume = risk_manager.calculate_position_size(self.symbol, entry_price, sl)
        
        # Place order
        order_type = mt5.ORDER_TYPE_BUY if direction == 'buy' else mt5.ORDER_TYPE_SELL
        
        reason = f"Momentum: {event.get('title', 'News')} - {event.get('classification', '')}"
        
        result = trade_executor.place_market_order(
            self.symbol,
            order_type,
            volume,
            sl,
            tp,
            reason
        )
        
        if result:
            logger.info(f"{self.symbol} MOMENTUM ENTRY: {direction.upper()} @ {entry_price:.5f}")
    
    def process_news_event(self, event):
        """
        Process news event and execute appropriate strategy
        
        Args:
            event: News event dict
        """
        time_until = event.get('time_until', 999)
        
        # Pre-news phase (15-5 minutes before)
        if 5 <= time_until <= 15:
            logger.info(f"{self.symbol} entering PRE-NEWS phase ({time_until:.1f} min)")
            
            analysis = self.analyze_pre_news()
            if analysis:
                # Execute straddle
                self.execute_straddle_strategy(analysis, event)
        
        # Post-news phase (0-30 minutes after)
        elif -30 <= time_until < 0:
            logger.info(f"{self.symbol} in POST-NEWS phase ({abs(time_until):.1f} min after)")
            
            # Get fresh analysis
            candles = self.get_candles(100)
            if candles is None:
                return
            
            analyzer = TechnicalAnalyzer(self.symbol, candles)
            analysis = analyzer.analyze()
            
            if not analysis:
                return
            
            # Check for volatility expansion
            if not analysis['volatility_expanding']:
                logger.debug(f"{self.symbol} no volatility expansion")
                return
            
            # Check breakout direction
            breakout = analysis.get('breakout_signal')
            
            if breakout == 'buy':
                self.execute_momentum_entry(analysis, 'buy', event)
            elif breakout == 'sell':
                self.execute_momentum_entry(analysis, 'sell', event)
    
    def manage_positions(self):
        """Manage open positions (breakeven, trailing, timeout)"""
        positions = trade_executor.get_open_positions(self.symbol)
        
        for position in positions:
            # Move to breakeven
            if risk_manager.should_move_to_breakeven(position):
                new_sl = position.price_open
                if trade_executor.modify_position(position.ticket, sl=new_sl):
                    logger.info(f"{self.symbol} moved to breakeven")
            
            # Trailing stop
            tick = mt5.symbol_info_tick(self.symbol)
            if tick:
                current_price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask
                new_sl = risk_manager.calculate_trailing_stop(position, current_price)
                
                if new_sl:
                    if trade_executor.modify_position(position.ticket, sl=new_sl):
                        logger.info(f"{self.symbol} trailing stop updated: {new_sl}")
            
            # Position timeout
            open_time = datetime.fromtimestamp(position.time)
            duration = (datetime.now() - open_time).total_seconds() / 60
            
            if duration > TRADING_CONFIG['position_timeout_minutes']:
                # Check if position is stagnant
                if abs(position.profit) < 0.5:  # Less than $0.50 profit/loss
                    trade_executor.close_position(position.ticket, "Timeout")

class StrategyManager:
    """Manage strategies for all symbols"""
    
    def __init__(self):
        self.strategies = {}
    
    def get_strategy(self, symbol):
        """Get or create strategy for symbol"""
        if symbol not in self.strategies:
            self.strategies[symbol] = NewsStrategy(symbol)
        return self.strategies[symbol]
    
    def process_all_events(self):
        """Process news events for all affected symbols"""
        # Update news calendar
        news_parser.update()
        
        # Get upcoming events
        events = news_parser.filter_events()
        
        if not events:
            return
        
        logger.info(f"Processing {len(events)} news events")
        
        for event in events:
            symbols = event.get('affected_symbols', [])
            
            for symbol in symbols:
                # Check if should avoid trading
                if news_parser.should_avoid_trading(symbol):
                    continue
                
                # Get strategy
                strategy = self.get_strategy(symbol)
                
                # Process event
                try:
                    strategy.process_news_event(event)
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}", exc_info=True)
    
    def manage_all_positions(self):
        """Manage positions for all symbols"""
        for symbol, strategy in self.strategies.items():
            try:
                strategy.manage_positions()
                strategy.check_straddle_triggered()
            except Exception as e:
                logger.error(f"Error managing {symbol}: {e}", exc_info=True)

# Global strategy manager
strategy_manager = StrategyManager()
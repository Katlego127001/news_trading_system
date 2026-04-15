"""
Main Trading Bot Runner
"""

import time
import signal
import sys
from datetime import datetime, timedelta
import pytz
from config import PRIORITY_SYMBOLS
from logger_config import logger
from trade_executor import trade_executor
from news_parser import news_parser
from strategy import strategy_manager
from telegram_notifier import notifier
from utils import is_trading_session, performance_tracker

class TradingBot:
    """Main trading bot controller"""
    
    def __init__(self):
        self.running = False
        self.cycle_count = 0
    
    def initialize(self):
        """Initialize all components"""
        logger.info("=" * 60)
        logger.info("INITIALIZING NEWS TRADING BOT")
        logger.info("=" * 60)
        
        # Initialize MT5
        if not trade_executor.initialize():
            logger.error("Failed to initialize MT5")
            return False
        
        # Fetch initial news calendar
        if not news_parser.fetch_calendar():
            logger.error("Failed to fetch news calendar")
            return False
        
        logger.info("[OK] All systems initialized")  # Changed from emoji
        logger.info(f"Monitoring symbols: {PRIORITY_SYMBOLS}")
        
        # Send startup notification
        notifier.send_message("🤖 <b>Trading Bot Started</b>\n\nAll systems operational!")
        
        return True
    
    def shutdown(self, signum=None, frame=None):
        """Graceful shutdown"""
        logger.info("Shutting down...")
        self.running = False
        
        # Close all open positions (optional)
        # positions = trade_executor.get_open_positions()
        # for pos in positions:
        #     trade_executor.close_position(pos.ticket, "Shutdown")
        
        # Shutdown MT5
        trade_executor.shutdown()
        
        # Send shutdown notification
        notifier.send_message("🛑 <b>Trading Bot Stopped</b>")
        
        logger.info("Shutdown complete")
        sys.exit(0)
    
    def run_cycle(self):
        """Execute one trading cycle"""
        try:
            self.cycle_count += 1
            logger.info(f"--- Cycle {self.cycle_count} @ {datetime.now().strftime('%H:%M:%S')} ---")

            # Display all upcoming tradeable events for the week
            now = datetime.now(pytz.UTC)
            week_later = now + timedelta(days=7)
            all_events = getattr(news_parser, 'events', [])
            tradeable_events = []
            for event in all_events:
                # Parse event time
                event_time = news_parser.parse_event_time(event.get('date', ''))
                if not event_time:
                    continue
                # Only show events from now to 7 days ahead
                if not (now <= event_time <= week_later):
                    continue
                # Only show events with tradeable impact
                impact = event.get('impact', '')
                if impact not in ['High', 'Medium']:
                    continue
                # Blacklist filter
                title = event.get('title', '')
                if any(keyword in title for keyword in getattr(news_parser, 'NEWS_CONFIG', {}).get('blacklist_keywords', ['Holiday', 'Speech'])):
                    continue
                # Calculate minutes away
                minutes_away = int((event_time - now).total_seconds() // 60)
                # Format line
                star = '⭐' if impact == 'High' else '•'
                logger.info(f"   {star} [{impact}] {event.get('country', 'N/A')} {event.get('title', 'N/A')} @ {event_time.strftime('%Y-%m-%d %H:%M UTC')} ({minutes_away} min away)")
                tradeable_events.append(event)
            if not tradeable_events:
                logger.info("   (No tradeable events this week)")

            # Check trading session
            if not is_trading_session():
                logger.info("Outside trading session - skipping")
                return

            # Process news events and execute strategies
            strategy_manager.process_all_events()

            # Manage existing positions
            strategy_manager.manage_all_positions()

            # Log performance every 50 cycles
            if self.cycle_count % 50 == 0:
                perf = performance_tracker.get_recent_performance()
                logger.info(f"Performance: Win Rate: {perf['win_rate']:.1f}%, "
                            f"Profit: ${perf['total_profit']:.2f}, "
                            f"Trades: {perf['trades']}")

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            notifier.notify_error(f"Cycle error: {str(e)}")
    
    def run(self):
        """Main loop"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
        # Initialize
        if not self.initialize():
            logger.error("Initialization failed - exiting")
            return
        
        self.running = True
        
        logger.info("[START] TRADING BOT RUNNING")  # Changed from emoji
        logger.info("Press Ctrl+C to stop")
        
        # Main loop
        while self.running:
            try:
                self.run_cycle()
                
                # Sleep between cycles (30 seconds)
                time.sleep(30)
                
            except KeyboardInterrupt:
                self.shutdown()
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                notifier.notify_error(f"Critical error: {str(e)}")
                time.sleep(60)  # Wait before retrying

def main():
    """Entry point"""
    bot = TradingBot()
    bot.run()

if __name__ == "__main__":
    main()
"""
Telegram notification system
"""

import requests
from datetime import datetime
from config import TELEGRAM_CONFIG
from logger_config import logger

class TelegramNotifier:
    """Send notifications via Telegram"""
    
    def __init__(self):
        self.enabled = TELEGRAM_CONFIG['enabled']
        self.bot_token = TELEGRAM_CONFIG['bot_token']
        self.chat_id = TELEGRAM_CONFIG['chat_id']
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, message):
        """Send a message to Telegram"""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    def notify_trade_opened(self, trade_info):
        """Notify when trade is opened"""
        if not TELEGRAM_CONFIG['send_on_trade']:
            return
        
        message = f"""
🚀 <b>TRADE OPENED</b>

📊 Symbol: {trade_info.get('symbol', 'N/A')}
📈 Type: {trade_info.get('type', 'N/A')}
💰 Entry: {trade_info.get('entry', 'N/A')}
🛑 SL: {trade_info.get('sl', 'N/A')}
🎯 TP: {trade_info.get('tp', 'N/A')}
📦 Lot: {trade_info.get('volume', 'N/A')}
📰 Reason: {trade_info.get('reason', 'N/A')}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
    
    def notify_trade_closed(self, trade_info):
        """Notify when trade is closed"""
        if not TELEGRAM_CONFIG['send_on_trade']:
            return
        
        profit = trade_info.get('profit', 0)
        emoji = "✅" if profit > 0 else "❌"
        
        message = f"""
{emoji} <b>TRADE CLOSED</b>

📊 Symbol: {trade_info.get('symbol', 'N/A')}
💵 Profit: ${profit:.2f}
📈 Entry: {trade_info.get('entry', 'N/A')}
🏁 Exit: {trade_info.get('exit', 'N/A')}
⏱️ Duration: {trade_info.get('duration', 'N/A')} min
📝 Outcome: {trade_info.get('outcome', 'N/A')}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
    
    def notify_news_detected(self, news_info):
        """Notify when high-impact news is detected"""
        message = f"""
📰 <b>NEWS ALERT</b>

🌍 {news_info.get('title', 'N/A')}
🏳️ Country: {news_info.get('country', 'N/A')}
⚡ Impact: {news_info.get('impact', 'N/A')}
🕐 Time: {news_info.get('time', 'N/A')}
📊 Symbols: {', '.join(news_info.get('symbols', []))}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
    
    def notify_error(self, error_msg):
        """Notify on error"""
        if not TELEGRAM_CONFIG['send_on_error']:
            return
        
        message = f"""
⚠️ <b>ERROR ALERT</b>

{error_msg}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
    
    def send_daily_summary(self, summary):
        """Send daily performance summary"""
        if not TELEGRAM_CONFIG['send_daily_summary']:
            return
        
        message = f"""
📊 <b>DAILY SUMMARY</b>

💰 Total Profit: ${summary.get('total_profit', 0):.2f}
📈 Trades: {summary.get('total_trades', 0)}
✅ Win Rate: {summary.get('win_rate', 0):.1f}%
📊 Profit Factor: {summary.get('profit_factor', 0):.2f}
🏆 Best Trade: ${summary.get('best_trade', 0):.2f}
💔 Worst Trade: ${summary.get('worst_trade', 0):.2f}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)

# Global notifier instance
notifier = TelegramNotifier()
"""
Logging configuration for the trading system
"""

import logging
import os
import sys
from datetime import datetime
from config import LOG_CONFIG, LOGS_DIR

class UnicodeFormatter(logging.Formatter):
    """Custom formatter that handles Unicode characters safely"""
    
    def format(self, record):
        """Format log record, removing problematic Unicode characters if needed"""
        result = super().format(record)
        
        # For Windows console, replace emojis with text equivalents
        if sys.platform == 'win32':
            emoji_map = {
                '✅': '[OK]',
                '❌': '[X]',
                '🚀': '[START]',
                '⚠️': '[WARN]',
                '📊': '[CHART]',
                '💰': '[MONEY]',
                '📈': '[UP]',
                '📉': '[DOWN]',
                '🛑': '[STOP]',
                '🔧': '[CONFIG]',
                '📰': '[NEWS]',
                '⚡': '[ALERT]',
                '🌍': '[GLOBAL]',
                '🏳️': '[FLAG]',
                '🕐': '[TIME]',
                '💵': '[USD]',
                '🏁': '[END]',
                '⏱️': '[TIMER]',
                '📝': '[NOTE]',
                '🏆': '[BEST]',
                '💔': '[WORST]',
                '📦': '[LOT]',
                '🎯': '[TARGET]',
                '🛡️': '[PROTECT]',
                '🤖': '[BOT]',
            }
            
            for emoji, replacement in emoji_map.items():
                result = result.replace(emoji, replacement)
        
        return result

def setup_logger(name='TradingBot'):
    """Setup logger with file and console handlers"""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_CONFIG['log_level']))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Custom formatter
    formatter = UnicodeFormatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler with UTF-8 encoding
    if LOG_CONFIG['log_to_console']:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        # Set encoding for Windows
        if hasattr(console_handler.stream, 'reconfigure'):
            try:
                console_handler.stream.reconfigure(encoding='utf-8')
            except:
                pass
        
        logger.addHandler(console_handler)
    
    # File handler with UTF-8 encoding
    if LOG_CONFIG['log_to_file']:
        log_file = os.path.join(
            LOGS_DIR,
            f"{LOG_CONFIG['log_file'].split('.')[0]}_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Create global logger
logger = setup_logger()
"""
Economic Calendar Parser - Fetches and processes news events
"""

import requests
from datetime import datetime, timedelta
import pytz
from config import NEWS_CONFIG, CURRENCY_SYMBOLS, AI_CONFIG
from logger_config import logger
from telegram_notifier import notifier

class NewsParser:
    """Parse economic calendar and manage news events"""
    
    def __init__(self):
        self.api_url = NEWS_CONFIG['api_url']
        self.events = []
        self.last_update = None
        self.upcoming_events = []
    
    def fetch_calendar(self):
        """Fetch economic calendar from API"""
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.events = data
            self.last_update = datetime.now()
            
            logger.info(f"Fetched {len(self.events)} events from calendar")
            return True
            
        except Exception as e:
            logger.error(f"Error fetching calendar: {e}")
            return False
    
    def parse_event_time(self, date_str):
        """
        Parse event time string to datetime
        
        Args:
            date_str: Date string from API
        
        Returns:
            datetime object or None
        """
        try:
            # Try multiple formats
            formats = [
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    # Ensure timezone awareness
                    if dt.tzinfo is None:
                        dt = pytz.UTC.localize(dt)
                    return dt
                except ValueError:
                    continue
            
            logger.warning(f"Could not parse date: {date_str}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing event time: {e}")
            return None
    
    def get_currency_from_country(self, country):
        """Map country to currency code"""
        country_currency_map = {
            'USD': 'USD',
            'EUR': 'EUR',
            'GBP': 'GBP',
            'JPY': 'JPY',
            'AUD': 'AUD',
            'NZD': 'NZD',
            'CAD': 'CAD',
            'CHF': 'CHF',
            'CNY': 'CNY',
        }
        
        # Direct match
        if country in country_currency_map:
            return country_currency_map[country]
        
        # Country name mapping
        country_map = {
            'United States': 'USD',
            'Eurozone': 'EUR',
            'Germany': 'EUR',
            'France': 'EUR',
            'United Kingdom': 'GBP',
            'Japan': 'JPY',
            'Australia': 'AUD',
            'New Zealand': 'NZD',
            'Canada': 'CAD',
            'Switzerland': 'CHF',
            'China': 'CNY',
        }
        
        return country_map.get(country, 'ALL')
    
    def get_affected_symbols(self, currency):
        """Get symbols affected by currency"""
        if currency in CURRENCY_SYMBOLS:
            return CURRENCY_SYMBOLS[currency]
        return CURRENCY_SYMBOLS.get('ALL', [])
    
    def classify_event(self, event):
        """
        Classify event type for AI strategy selection
        
        Returns:
            str: Event classification
        """
        title = event.get('title', '').upper()
        
        # High volatility events
        if any(keyword in title for keyword in AI_CONFIG['high_volatility_events']):
            return 'high_volatility'
        
        # Employment data
        if any(keyword in title for keyword in ['EMPLOYMENT', 'JOBS', 'NFP', 'UNEMPLOYMENT']):
            return 'employment'
        
        # Inflation data
        if any(keyword in title for keyword in ['CPI', 'PPI', 'INFLATION']):
            return 'inflation'
        
        # GDP
        if 'GDP' in title:
            return 'gdp'
        
        # Central bank
        if any(keyword in title for keyword in ['FOMC', 'RATE DECISION', 'MONETARY POLICY']):
            return 'central_bank'
        
        return 'standard'
    
    def filter_events(self, impact_filter=None):
        """
        Filter events by impact and time
        
        Args:
            impact_filter: List of impact levels to include
        
        Returns:
            list: Filtered events
        """
        if impact_filter is None:
            impact_filter = NEWS_CONFIG['impact_filter']
        
        filtered = []
        now = datetime.now(pytz.UTC)
        
        for event in self.events:
            # Check impact
            impact = event.get('impact', '')
            if impact not in impact_filter:
                continue
            
            # Check blacklist
            title = event.get('title', '')
            if any(keyword in title for keyword in NEWS_CONFIG['blacklist_keywords']):
                continue
            
            # Parse time
            event_time = self.parse_event_time(event.get('date', ''))
            if not event_time:
                continue
            
            # Check if upcoming
            time_until = (event_time - now).total_seconds() / 60
            
            # Include events from -15 min to +30 min window
            if -NEWS_CONFIG['pre_news_minutes'] <= time_until <= NEWS_CONFIG['post_news_minutes']:
                event['event_time'] = event_time
                event['time_until'] = time_until
                event['currency'] = self.get_currency_from_country(event.get('country', ''))
                event['affected_symbols'] = self.get_affected_symbols(event['currency'])
                event['classification'] = self.classify_event(event)
                
                filtered.append(event)
        
        return filtered
    
    def get_upcoming_events(self, minutes_ahead=30):
        """Get events coming up in next N minutes"""
        now = datetime.now(pytz.UTC)
        upcoming = []
        
        for event in self.events:
            event_time = self.parse_event_time(event.get('date', ''))
            if not event_time:
                continue
            
            time_until = (event_time - now).total_seconds() / 60
            
            if 0 <= time_until <= minutes_ahead:
                event['event_time'] = event_time
                event['time_until'] = time_until
                event['currency'] = self.get_currency_from_country(event.get('country', ''))
                event['affected_symbols'] = self.get_affected_symbols(event['currency'])
                event['classification'] = self.classify_event(event)
                
                upcoming.append(event)
        
        return upcoming
    
    def should_avoid_trading(self, symbol):
        """
        Check if should avoid trading due to imminent news
        
        Args:
            symbol: Trading symbol
        
        Returns:
            bool: True if should avoid
        """
        now = datetime.now(pytz.UTC)
        avoid_minutes = NEWS_CONFIG['avoid_minutes']
        
        for event in self.events:
            # Check if event affects this symbol
            currency = self.get_currency_from_country(event.get('country', ''))
            affected_symbols = self.get_affected_symbols(currency)
            
            if symbol not in affected_symbols:
                continue
            
            # Check time
            event_time = self.parse_event_time(event.get('date', ''))
            if not event_time:
                continue
            
            time_until = (event_time - now).total_seconds() / 60
            
            # Avoid from -avoid_minutes to +1 minute
            if -avoid_minutes <= time_until <= 1:
                logger.warning(f"Avoiding {symbol} - news in {time_until:.1f} minutes: {event.get('title')}")
                return True
        
        return False
    
    def update(self):
        """Update calendar if needed"""
        if not self.last_update or \
           (datetime.now() - self.last_update).total_seconds() > NEWS_CONFIG['update_interval']:
            
            logger.info("Updating economic calendar...")
            success = self.fetch_calendar()
            
            if success:
                # Get upcoming high-impact events
                upcoming = self.get_upcoming_events(60)
                
                # Notify about new high-impact events
                for event in upcoming:
                    if event.get('impact') == 'High' and event.get('time_until', 999) > 5:
                        notifier.notify_news_detected({
                            'title': event.get('title', 'N/A'),
                            'country': event.get('country', 'N/A'),
                            'impact': event.get('impact', 'N/A'),
                            'time': event.get('event_time', 'N/A'),
                            'symbols': event.get('affected_symbols', [])
                        })
            
            return success
        
        return True

# Global news parser instance
news_parser = NewsParser()
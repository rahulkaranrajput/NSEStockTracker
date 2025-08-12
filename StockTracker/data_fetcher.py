# data_fetcher.py
# Stock data fetching using yfinance

import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, time, timedelta
from typing import List, Optional, Dict, Any
from config import Config
from models import StockCandle, FetchResult, MarketStatus

class StockDataFetcher:
    """
    Fetches stock data using yfinance API
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or Config.STOCK_SYMBOLS
        self.session = None  # Let yfinance handle sessions internally
        logging.info("Data fetcher initialized successfully")
    
    def fetch_latest_candle(self, symbol: str) -> FetchResult:
        """
        Fetch the latest 5-minute candle for a symbol
        """
        try:
            logging.info(f"Fetching data for {symbol}")
            
            # Create ticker object with error handling for different yfinance versions
            try:
                ticker = yf.Ticker(symbol)
            except Exception as e:
                if "curl_cffi" in str(e):
                    # Try with requests_cache disabled
                    ticker = yf.Ticker(symbol)
                else:
                    raise
            
            # Get 5-minute data for today
            data = ticker.history(
                period="1d",
                interval=Config.DATA_INTERVAL,
                prepost=False,  # Don't include pre/post market data
                auto_adjust=True,
                back_adjust=False,
                repair=True
            )
            
            if data.empty:
                error_msg = f"No data returned for {symbol}"
                logging.warning(error_msg)
                return FetchResult(
                    success=False,
                    symbol=symbol,
                    error_message=error_msg
                )
            
            # Get the latest candle
            latest_timestamp = data.index[-1]
            latest_row = data.iloc[-1]
            
            # Convert to our StockCandle model
            candle = StockCandle.from_yfinance_row(
                symbol=symbol,
                timestamp=latest_timestamp.to_pydatetime(),
                row=latest_row
            )
            
            logging.info(f"Successfully fetched data for {symbol}: ${candle.close_price:.2f}")
            
            return FetchResult(
                success=True,
                symbol=symbol,
                data=candle
            )
            
        except Exception as e:
            error_msg = f"Error fetching data for {symbol}: {str(e)}"
            logging.error(error_msg)
            
            return FetchResult(
                success=False,
                symbol=symbol,
                error_message=error_msg
            )
    
    def fetch_historical_data(self, symbol: str, days: int = 1) -> List[StockCandle]:
        """
        Fetch historical 5-minute candles for a symbol
        """
        try:
            ticker = yf.Ticker(symbol)  # Let yfinance handle sessions
            
            # Calculate period
            if days <= 1:
                period = "1d"
            elif days <= 5:
                period = "5d"
            elif days <= 30:
                period = "1mo"
            else:
                period = "3mo"
            
            data = ticker.history(
                period=period,
                interval=Config.DATA_INTERVAL,
                prepost=False,
                auto_adjust=True,
                back_adjust=False,
                repair=True
            )
            
            if data.empty:
                logging.warning(f"No historical data for {symbol}")
                return []
            
            candles = []
            for timestamp, row in data.iterrows():
                candle = StockCandle.from_yfinance_row(
                    symbol=symbol,
                    timestamp=timestamp.to_pydatetime(),
                    row=row
                )
                candles.append(candle)
            
            logging.info(f"Fetched {len(candles)} historical candles for {symbol}")
            return candles
            
        except Exception as e:
            logging.error(f"Error fetching historical data for {symbol}: {e}")
            return []
    
    def fetch_all_symbols(self) -> List[FetchResult]:
        """
        Fetch latest candles for all tracked symbols
        """
        results = []
        
        for symbol in self.symbols:
            result = self.fetch_latest_candle(symbol)
            results.append(result)
            
            # Small delay to avoid rate limiting
            import time
            time.sleep(0.1)
        
        successful = sum(1 for r in results if r.success)
        logging.info(f"Fetched data for {successful}/{len(self.symbols)} symbols")
        
        return results
    
    def get_market_status(self) -> MarketStatus:
        """
        Check if the Indian market is currently open
        """
        from datetime import timezone
        import pytz
        
        # Get current time in Indian timezone (IST)
        ist_tz = pytz.timezone('Asia/Kolkata')
        current_ist = datetime.now(ist_tz)
        current_date = current_ist.date()
        current_time = current_ist.time()
        current_weekday = current_date.weekday()
        
        # Check if it's a trading day (Monday=0 to Friday=4)
        is_trading_day = current_weekday in Config.TRADING_DAYS
        
        # Check if market is open (9:15 AM to 3:30 PM IST)
        is_open = (
            is_trading_day and 
            Config.MARKET_OPEN_TIME <= current_time <= Config.MARKET_CLOSE_TIME
        )
        
        # Calculate next open/close times
        next_open = self._calculate_next_market_open(current_ist)
        next_close = self._calculate_next_market_close(current_ist) if is_open else None
        
        return MarketStatus(
            is_open=is_open,
            is_trading_day=is_trading_day,
            current_time=current_ist.replace(tzinfo=None),
            next_open=next_open,
            next_close=next_close
        )
    
    def _calculate_next_market_open(self, current_ist) -> datetime:
        """Calculate next Indian market open time"""
        import pytz
        ist_tz = pytz.timezone('Asia/Kolkata')
        
        # Start with today
        next_date = current_ist.date()
        
        # If market closed today, try tomorrow
        if current_ist.time() > Config.MARKET_CLOSE_TIME:
            next_date += timedelta(days=1)
        
        # Find next trading day
        while next_date.weekday() not in Config.TRADING_DAYS:
            next_date += timedelta(days=1)
        
        # Combine date and time
        next_open = datetime.combine(next_date, Config.MARKET_OPEN_TIME)
        return ist_tz.localize(next_open).replace(tzinfo=None)
    
    def _calculate_next_market_close(self, current_ist) -> datetime:
        """Calculate next Indian market close time (only if market is open)"""
        import pytz
        ist_tz = pytz.timezone('Asia/Kolkata')
        
        next_close = datetime.combine(current_ist.date(), Config.MARKET_CLOSE_TIME)
        return ist_tz.localize(next_close).replace(tzinfo=None)
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a stock symbol exists
        """
        try:
            ticker = yf.Ticker(symbol)  # Let yfinance handle sessions
            info = ticker.info
            
            # Check if we got valid info
            return 'symbol' in info or 'shortName' in info
            
        except Exception as e:
            logging.warning(f"Symbol validation failed for {symbol}: {e}")
            return False
    
    def add_symbol(self, symbol: str) -> bool:
        """
        Add a new symbol to track
        """
        symbol = symbol.upper().strip()
        
        if symbol in self.symbols:
            logging.info(f"Symbol {symbol} already being tracked")
            return True
        
        if self.validate_symbol(symbol):
            self.symbols.append(symbol)
            Config.add_stock_symbol(symbol)
            logging.info(f"Added symbol {symbol} to tracking list")
            return True
        else:
            logging.error(f"Invalid symbol: {symbol}")
            return False
    
    def remove_symbol(self, symbol: str) -> bool:
        """
        Remove a symbol from tracking
        """
        symbol = symbol.upper().strip()
        
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            Config.remove_stock_symbol(symbol)
            logging.info(f"Removed symbol {symbol} from tracking list")
            return True
        else:
            logging.warning(f"Symbol {symbol} not in tracking list")
            return False
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get basic information about a symbol
        """
        try:
            ticker = yf.Ticker(symbol)  # Let yfinance handle sessions
            info = ticker.info
            
            return {
                'symbol': symbol,
                'name': info.get('longName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap', 0),
                'currency': info.get('currency', 'USD')
            }
            
        except Exception as e:
            logging.error(f"Error getting info for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
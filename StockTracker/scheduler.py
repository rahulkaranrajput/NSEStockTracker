# scheduler.py
# Background scheduler for automatic data collection

import schedule
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional, List
from config import Config
from data_fetcher import StockDataFetcher
from database import StockDatabase
from models import MarketStatus, FetchResult

class DataScheduler:
    """
    Manages background data collection on a schedule
    """
    
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.database = StockDatabase()
        self.is_running = False
        self.scheduler_thread = None
        self.last_fetch_time = None
        self.fetch_count = 0
        self.error_count = 0
        self.market_hours_only = True  # Only fetch during market hours
        
    def start(self, market_hours_only: bool = True):
        """
        Start the background data collection scheduler
        """
        if self.is_running:
            logging.warning("Scheduler is already running")
            return
        
        self.market_hours_only = market_hours_only
        self.is_running = True
        
        # Schedule data collection every 5 minutes
        schedule.every(Config.FETCH_INTERVAL_MINUTES).minutes.do(self._collect_data)
        
        # Schedule daily cleanup at 6 AM
        schedule.every().day.at("06:00").do(self._daily_cleanup)
        
        # Start scheduler in background thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logging.info(f"Data scheduler started (market hours only: {market_hours_only})")
    
    def stop(self):
        """
        Stop the background scheduler
        """
        self.is_running = False
        schedule.clear()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            # Wait for thread to finish (up to 5 seconds)
            self.scheduler_thread.join(timeout=5)
        
        logging.info("Data scheduler stopped")
    
    def _run_scheduler(self):
        """
        Main scheduler loop (runs in background thread)
        """
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(1)  # Check every second
            except Exception as e:
                logging.error(f"Scheduler error: {e}")
                self.error_count += 1
                time.sleep(10)  # Wait before retrying
    
    def _collect_data(self):
        """
        Collect data for all symbols (called by scheduler)
        """
        try:
            # Check market status
            market_status = self.fetcher.get_market_status()
            
            # Skip if market is closed and we're in market-hours-only mode
            if self.market_hours_only and not market_status.is_open:
                logging.debug(f"Market closed, skipping data collection. {market_status}")
                return
            
            logging.info(f"Starting scheduled data collection. {market_status}")
            
            # Fetch data for all symbols
            results = self.fetcher.fetch_all_symbols()
            
            # Save successful results to database
            saved_count = 0
            for result in results:
                if result.success and result.data:
                    if self.database.save_candle(result.data):
                        saved_count += 1
                else:
                    self.error_count += 1
                    logging.warning(f"Failed to fetch {result.symbol}: {result.error_message}")
            
            # Update statistics
            self.last_fetch_time = datetime.now()
            self.fetch_count += 1
            
            logging.info(f"Completed data collection: {saved_count} new records saved")
            
        except Exception as e:
            logging.error(f"Error during data collection: {e}")
            self.error_count += 1
    
    def _daily_cleanup(self):
        """
        Daily maintenance tasks
        """
        try:
            logging.info("Starting daily cleanup")
            
            # Clean up old data
            deleted_count = self.database.cleanup_old_data()
            
            # Reset error count
            self.error_count = 0
            
            logging.info(f"Daily cleanup completed: {deleted_count} old records removed")
            
        except Exception as e:
            logging.error(f"Error during daily cleanup: {e}")
    
    def collect_now(self, force: bool = False) -> List[FetchResult]:
        """
        Manually trigger data collection immediately
        """
        try:
            market_status = self.fetcher.get_market_status()
            
            if not force and self.market_hours_only and not market_status.is_open:
                logging.info("Market is closed. Use force=True to collect anyway.")
                return []
            
            logging.info("Manual data collection triggered")
            results = self.fetcher.fetch_all_symbols()
            
            # Save to database
            saved_count = 0
            for result in results:
                if result.success and result.data:
                    if self.database.save_candle(result.data):
                        saved_count += 1
            
            self.last_fetch_time = datetime.now()
            logging.info(f"Manual collection completed: {saved_count} records saved")
            
            return results
            
        except Exception as e:
            logging.error(f"Error during manual collection: {e}")
            return []
    
    def get_status(self) -> dict:
        """
        Get current scheduler status
        """
        market_status = self.fetcher.get_market_status()
        
        return {
            'is_running': self.is_running,
            'last_fetch_time': self.last_fetch_time,
            'fetch_count': self.fetch_count,
            'error_count': self.error_count,
            'market_status': market_status,
            'symbols_count': len(self.fetcher.symbols),
            'total_records': self.database.get_total_records(),
            'market_hours_only': self.market_hours_only
        }
    
    def add_symbol(self, symbol: str) -> bool:
        """
        Add a new symbol to track
        """
        return self.fetcher.add_symbol(symbol)
    
    def remove_symbol(self, symbol: str) -> bool:
        """
        Remove a symbol from tracking
        """
        return self.fetcher.remove_symbol(symbol)
    
    def get_symbols(self) -> List[str]:
        """
        Get list of currently tracked symbols
        """
        return self.fetcher.symbols.copy()
    
    def backfill_data(self, symbol: str, days: int = 1) -> int:
        """
        Backfill historical data for a symbol
        """
        try:
            logging.info(f"Backfilling {days} days of data for {symbol}")
            
            candles = self.fetcher.fetch_historical_data(symbol, days)
            
            saved_count = 0
            for candle in candles:
                if self.database.save_candle(candle):
                    saved_count += 1
            
            logging.info(f"Backfilled {saved_count} records for {symbol}")
            return saved_count
            
        except Exception as e:
            logging.error(f"Error backfilling data for {symbol}: {e}")
            return 0
    
    def backfill_all_symbols(self, days: int = 1) -> dict:
        """
        Backfill historical data for all symbols
        """
        results = {}
        
        for symbol in self.fetcher.symbols:
            results[symbol] = self.backfill_data(symbol, days)
            time.sleep(0.5)  # Avoid rate limiting
        
        total_saved = sum(results.values())
        logging.info(f"Backfill completed: {total_saved} total records saved")
        
        return results
    
    def set_market_hours_only(self, market_hours_only: bool):
        """
        Set whether to collect data only during market hours
        """
        self.market_hours_only = market_hours_only
        logging.info(f"Market hours only mode: {market_hours_only}")
    
    def get_next_collection_time(self) -> Optional[datetime]:
        """
        Get the next scheduled collection time
        """
        if not self.is_running:
            return None
        
        # Get next scheduled job
        jobs = schedule.jobs
        if jobs:
            next_run = min(job.next_run for job in jobs if job.next_run)
            return next_run
        
        return None
    
    def force_immediate_collection(self):
        """
        Force immediate data collection regardless of schedule
        """
        logging.info("Forcing immediate data collection")
        self._collect_data()
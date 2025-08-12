#!/usr/bin/env python3
# main.py
# Main entry point for Stock Tracker application

import sys
import os
import logging
import argparse
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from gui import StockTrackerGUI
from scheduler import DataScheduler
from data_fetcher import StockDataFetcher
from database import StockDatabase

class StockTrackerApp:
    """
    Main Stock Tracker Application
    """
    
    def __init__(self):
        self.setup_logging()
        self.scheduler = None
        self.gui = None
        
    def setup_logging(self):
        """Setup application logging"""
        # Ensure data directory exists
        Config.ensure_data_directory()
        
        # Configure logging
        handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        handlers.append(console_handler)
        
        # File handler (if enabled)
        if Config.LOG_TO_FILE:
            file_handler = logging.FileHandler(Config.LOG_FILE_PATH)
            file_handler.setLevel(logging.DEBUG)
            handlers.append(file_handler)
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        
        # Reduce yfinance logging noise
        logging.getLogger('yfinance').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        logging.info(f"Starting {Config.APP_NAME} v{Config.APP_VERSION}")
    
    def run_gui(self):
        """Run the GUI version"""
        try:
            logging.info("Starting GUI mode")
            self.gui = StockTrackerGUI()
            self.gui.run()
        except Exception as e:
            logging.error(f"GUI mode failed: {e}")
            raise
    
    def run_console(self):
        """Run in console mode (background service)"""
        try:
            logging.info("Starting console mode")
            self.scheduler = DataScheduler()
            
            # Start the scheduler
            self.scheduler.start()
            
            print(f"\n{Config.APP_NAME} is now running in background mode.")
            print("Data will be collected every 5 minutes during market hours.")
            print("Press Ctrl+C to stop.\n")
            
            # Keep the application running
            import time
            while True:
                try:
                    status = self.scheduler.get_status()
                    print(f"\rStatus: {status['is_running']} | "
                          f"Records: {status['total_records']} | "
                          f"Fetches: {status['fetch_count']} | "
                          f"Errors: {status['error_count']}", end="")
                    time.sleep(30)  # Update every 30 seconds
                except KeyboardInterrupt:
                    break
            
        except KeyboardInterrupt:
            logging.info("Received interrupt signal")
        except Exception as e:
            logging.error(f"Console mode failed: {e}")
            raise
        finally:
            if self.scheduler:
                logging.info("Stopping scheduler...")
                self.scheduler.stop()
    
    def test_connection(self):
        """Test the data fetching capability"""
        try:
            print("Testing stock data connection...")
            
            fetcher = StockDataFetcher(['AAPL'])  # Test with Apple
            result = fetcher.fetch_latest_candle('AAPL')
            
            if result.success:
                print(f"✅ Connection test successful!")
                print(f"   Symbol: {result.data.symbol}")
                print(f"   Price: ${result.data.close_price:.2f}")
                print(f"   Time: {result.data.timestamp}")
                return True
            else:
                print(f"❌ Connection test failed: {result.error_message}")
                return False
                
        except Exception as e:
            print(f"❌ Connection test error: {e}")
            return False
    
    def show_status(self):
        """Show application status"""
        try:
            database = StockDatabase()
            fetcher = StockDataFetcher()
            
            print(f"\n{Config.APP_NAME} v{Config.APP_VERSION} Status")
            print("=" * 50)
            
            # Database stats
            stats = database.get_database_stats()
            print(f"Total Records: {stats.get('total_records', 0)}")
            print(f"Database Size: {stats.get('database_size', 'Unknown')}")
            
            # Symbols
            symbols = fetcher.symbols
            print(f"Tracked Symbols: {', '.join(symbols)}")
            
            # Market status
            market_status = fetcher.get_market_status()
            status_text = "OPEN" if market_status.is_open else "CLOSED"
            print(f"Market Status: {status_text}")
            
            # Recent data
            print(f"\nRecent Data:")
            for symbol in symbols[:3]:  # Show first 3 symbols
                latest = database.get_latest_candle(symbol)
                if latest:
                    print(f"  {symbol}: ${latest.close_price:.2f} at {latest.timestamp.strftime('%H:%M')}")
                else:
                    print(f"  {symbol}: No data")
                    
        except Exception as e:
            print(f"Error getting status: {e}")
    
    def backfill_data(self, days=1):
        """Backfill historical data"""
        try:
            print(f"Backfilling {days} days of historical data...")
            
            scheduler = DataScheduler()
            results = scheduler.backfill_all_symbols(days)
            
            total_records = sum(results.values())
            print(f"✅ Backfilled {total_records} total records")
            
            for symbol, count in results.items():
                print(f"   {symbol}: {count} records")
                
        except Exception as e:
            print(f"❌ Backfill failed: {e}")

def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description=f"{Config.APP_NAME} - Automated stock price data collection"
    )
    
    parser.add_argument(
        'mode',
        nargs='?',
        choices=['gui', 'console', 'test', 'status', 'backfill'],
        default='gui',
        help='Application mode (default: gui)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Number of days for backfill mode (default: 1)'
    )
    
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Override default symbols to track'
    )
    
    parser.add_argument(
        '--market-hours-only',
        action='store_true',
        help='Only collect data during market hours'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f"{Config.APP_NAME} {Config.APP_VERSION}"
    )
    
    return parser

def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Override symbols if provided
    if args.symbols:
        Config.STOCK_SYMBOLS = [symbol.upper() for symbol in args.symbols]
    
    # Create application instance
    app = StockTrackerApp()
    
    try:
        if args.mode == 'gui':
            app.run_gui()
            
        elif args.mode == 'console':
            app.run_console()
            
        elif args.mode == 'test':
            success = app.test_connection()
            sys.exit(0 if success else 1)
            
        elif args.mode == 'status':
            app.show_status()
            
        elif args.mode == 'backfill':
            app.backfill_data(args.days)
            
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        logging.info("Application terminated by user")
        
    except Exception as e:
        print(f"\nApplication error: {e}")
        logging.error(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
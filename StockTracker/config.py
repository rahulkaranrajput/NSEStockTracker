# config.py
# Configuration settings for Stock Tracker

import os
from datetime import time

class Config:
    # Database settings
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'stocks.db')
    
    # Stock symbols to track - Indian Market (NSE)
    STOCK_SYMBOLS = [
        'RELIANCE.NS',  # Reliance Industries
        'TCS.NS',       # Tata Consultancy Services
        'INFY.NS',      # Infosys
        'HDFCBANK.NS',  # HDFC Bank
        'ICICIBANK.NS', # ICICI Bank
        'HINDUNILVR.NS',# Hindustan Unilever
        'ITC.NS',       # ITC Limited
        'SBIN.NS',      # State Bank of India
        'BHARTIARTL.NS',# Bharti Airtel
        'LT.NS',        # Larsen & Toubro
    ]
    
    # Data fetching settings
    FETCH_INTERVAL_MINUTES = 5  # Fetch data every 5 minutes
    DATA_INTERVAL = '5m'        # 5-minute candles
    
    # Market hours (Indian Standard Time - IST)
    MARKET_OPEN_TIME = time(9, 15)   # 9:15 AM IST
    MARKET_CLOSE_TIME = time(15, 30)  # 3:30 PM IST
    
    # Trading days (0=Monday, 6=Sunday)
    TRADING_DAYS = [0, 1, 2, 3, 4]  # Monday to Friday
    
    # Application settings
    APP_NAME = "Stock Tracker"
    APP_VERSION = "1.0.0"
    
    # GUI settings
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    UPDATE_GUI_INTERVAL = 30000  # Update GUI every 30 seconds (in milliseconds)
    
    # Data retention settings
    KEEP_DATA_DAYS = 30  # Keep data for 30 days
    
    # Error handling
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 10
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_TO_FILE = True
    LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'stock_tracker.log')
    
    @classmethod
    def ensure_data_directory(cls):
        """Ensure the data directory exists"""
        data_dir = os.path.dirname(cls.DATABASE_PATH)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
    @classmethod
    def add_stock_symbol(cls, symbol):
        """Add a new stock symbol to track"""
        if symbol.upper() not in cls.STOCK_SYMBOLS:
            cls.STOCK_SYMBOLS.append(symbol.upper())
            
    @classmethod
    def remove_stock_symbol(cls, symbol):
        """Remove a stock symbol from tracking"""
        if symbol.upper() in cls.STOCK_SYMBOLS:
            cls.STOCK_SYMBOLS.remove(symbol.upper())
            
    @classmethod
    def get_database_url(cls):
        """Get the database connection URL"""
        cls.ensure_data_directory()
        return f"sqlite:///{cls.DATABASE_PATH}"
# models.py
# Data models for Stock Tracker

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class StockCandle:
    """
    Represents a single 5-minute stock candle with OHLCV data
    """
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set created_at to current time if not provided"""
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self):
        """Convert to dictionary for database storage"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'close_price': self.close_price,
            'volume': self.volume,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create StockCandle from dictionary"""
        return cls(
            symbol=data['symbol'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            open_price=data['open_price'],
            high_price=data['high_price'],
            low_price=data['low_price'],
            close_price=data['close_price'],
            volume=data['volume'],
            created_at=datetime.fromisoformat(data['created_at'])
        )
    
    @classmethod
    def from_yfinance_row(cls, symbol, timestamp, row):
        """Create StockCandle from yfinance data row"""
        return cls(
            symbol=symbol,
            timestamp=timestamp,
            open_price=float(row['Open']),
            high_price=float(row['High']),
            low_price=float(row['Low']),
            close_price=float(row['Close']),
            volume=int(row['Volume'])
        )
    
    def __str__(self):
        """String representation"""
        return f"{self.symbol} {self.timestamp}: O:{self.open_price:.2f} H:{self.high_price:.2f} L:{self.low_price:.2f} C:{self.close_price:.2f} V:{self.volume}"

@dataclass
class MarketStatus:
    """
    Represents current market status
    """
    is_open: bool
    is_trading_day: bool
    current_time: datetime
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None
    
    def __str__(self):
        status = "OPEN" if self.is_open else "CLOSED"
        return f"Market: {status} at {self.current_time.strftime('%Y-%m-%d %H:%M:%S')}"

@dataclass
class FetchResult:
    """
    Represents the result of a data fetch operation
    """
    success: bool
    symbol: str
    data: Optional[StockCandle] = None
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class AppStatus:
    """
    Represents the current status of the application
    """
    is_running: bool
    last_fetch_time: Optional[datetime]
    total_records: int
    active_symbols: list
    market_status: Optional[MarketStatus] = None
    errors_count: int = 0
    
    def __str__(self):
        status = "RUNNING" if self.is_running else "STOPPED"
        last_fetch = self.last_fetch_time.strftime('%H:%M:%S') if self.last_fetch_time else "Never"
        return f"App: {status} | Last Fetch: {last_fetch} | Records: {self.total_records}"
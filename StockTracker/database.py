# database.py
# SQLite database operations for Stock Tracker

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from config import Config
from models import StockCandle, AppStatus

class StockDatabase:
    """
    Handles all database operations for stock data
    """
    
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        Config.ensure_data_directory()
        self.init_database()
        
    def init_database(self):
        """Initialize the database and create tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                #cursor.execute('DROP TABLE IF EXISTS stock_candles')
                # Create stock_candles table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS stock_candles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        open_price REAL NOT NULL,
                        high_price REAL NOT NULL,
                        low_price REAL NOT NULL,
                        close_price REAL NOT NULL,
                        volume INTEGER NOT NULL,
                        avg_price REAL NOT NULL,
                        money_flow REAL NOT NULL,
                        net_mf REAL NOT NULL,
                        created_at TEXT NOT NULL,
                        UNIQUE(symbol, timestamp)
                    )
                ''')
                
                # Create index for faster queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
                    ON stock_candles(symbol, timestamp)
                ''')
                
                # Create app_status table for tracking application state
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS app_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        last_update TEXT NOT NULL,
                        total_records INTEGER DEFAULT 0,
                        last_fetch_time TEXT,
                        errors_count INTEGER DEFAULT 0
                    )
                ''')
                
                conn.commit()
                logging.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
            raise
    
    def save_candle(self, candle: StockCandle) -> bool:
        """
        Save a stock candle to the database
        Returns True if saved successfully, False if already exists
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                vol = int(candle.volume/1000)
                # Calculate avg_price
                avg_price = int(round((candle.high_price + candle.low_price) / 2, 2))
            
                # Calculate money_flow
                money_flow = int(round((avg_price * vol) / 1000, 2))
                
                # Calculate net_mf - need to check previous entries
                net_mf = self._calculate_net_mf(cursor, candle, avg_price, money_flow)
                net_mf = int(round(net_mf, 2))
                
                logging.info(f"Final calculated values - Avg: {avg_price}, MF: {money_flow}, NetMF: {net_mf}")
            

                cursor.execute('''
                    INSERT OR IGNORE INTO stock_candles 
                    (symbol, timestamp, open_price, high_price, low_price, 
                    close_price, volume, avg_price, money_flow, net_mf, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    candle.symbol,
                    candle.timestamp.isoformat(),
                    candle.open_price,
                    candle.high_price,
                    candle.low_price,
                    candle.close_price,
                    vol,
                    avg_price,
                    money_flow,
                    net_mf,
                    candle.created_at.isoformat()
                ))
                
                success = cursor.rowcount > 0
                conn.commit()
                
                if success:
                    logging.info(f"Saved candle: {candle}")
                else:
                    logging.debug(f"Candle already exists: {candle.symbol} {candle.timestamp}")
                    
                return success
                
        except sqlite3.Error as e:
            logging.error(f"Error saving candle: {e}")
            return False

    def _calculate_net_mf(self, cursor, candle: StockCandle, avg_price: float, money_flow: float) -> float:
        """
        Calculate Net MF based on the rules:
        1. First entry of day: Compare Close vs Open
        2. Subsequent entries: Compare current avg_price vs previous avg_price
        3. Equal avg_prices: Use previous Net MF sign
        """
        try:
            # Get the date from timestamp
            candle_date = candle.timestamp.date()
            
            # Check if this is the first entry of the day
            cursor.execute('''
                SELECT COUNT(*) FROM stock_candles 
                WHERE symbol = ? AND DATE(timestamp) = ?
            ''', (candle.symbol, candle_date.isoformat()))
            
            day_entry_count = cursor.fetchone()[0]
            
            if day_entry_count == 0:
                # First entry of the day - compare close vs open
                if candle.close_price < candle.open_price:
                    return -money_flow
                else:
                    return money_flow
            else:
                # Get the most recent entry for this symbol on the same day
                cursor.execute('''
                    SELECT avg_price, net_mf FROM stock_candles 
                    WHERE symbol = ? AND DATE(timestamp) = ?
                    ORDER BY timestamp DESC LIMIT 1
                ''', (candle.symbol, candle_date.isoformat()))
                
                result = cursor.fetchone()
                if result:
                    previous_avg_price, previous_net_mf = result
                    
                    if avg_price > previous_avg_price:
                        return money_flow + previous_net_mf
                    elif avg_price < previous_avg_price:
                        return -money_flow + previous_net_mf
                    else:
                        # Equal avg prices - use previous Net MF sign
                        if previous_net_mf >= 0:
                            return money_flow + previous_net_mf
                        else:
                            return -money_flow + previous_net_mf
                else:
                    # Fallback - shouldn't happen but just in case
                    return money_flow
                    
        except Exception as e:
            logging.error(f"Error calculating Net MF: {e}")
            # Fallback calculation
            if candle.close_price < candle.open_price:
                return -money_flow
            else:
                return money_flow
    
    def get_latest_candle(self, symbol: str) -> Optional[StockCandle]:
        """Get the latest candle for a symbol"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT symbol, timestamp, open_price, high_price, low_price,
                       close_price, volume, avg_price, money_flow, net_mf, created_at
                    FROM stock_candles 
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (symbol,))
                
                row = cursor.fetchone()
                if row:
                    return StockCandle(
                        symbol=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        open_price=row[2],
                        high_price=row[3],
                        low_price=row[4],
                        close_price=row[5],
                        volume=row[6],
                        avg_price = row[7],
                        money_flow = row[8],
                        net_mf = row[9],
                        created_at=datetime.fromisoformat(row[10])
                    )
                return None
                
        except sqlite3.Error as e:
            logging.error(f"Error getting latest candle: {e}")
            return None
    
    def get_candles_for_symbol(self, symbol: str, limit: int = 100) -> List[StockCandle]:
        """Get recent candles for a symbol"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT symbol, timestamp, open_price, high_price, low_price,
                       close_price, volume, avg_price, money_flow, net_mf, created_at
                    FROM stock_candles 
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (symbol, limit))
                
                candles = []
                for row in cursor.fetchall():
                    candles.append(StockCandle(
                        symbol=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        open_price=row[2],
                        high_price=row[3],
                        low_price=row[4],
                        close_price=row[5],
                        volume=row[6],
                        avg_price = row[7],
                        money_flow = row[8],
                        net_mf = row[9],
                        created_at=datetime.fromisoformat(row[10])
                    ))
                
                return candles
                
        except sqlite3.Error as e:
            logging.error(f"Error getting candles for symbol: {e}")
            return []
    
    def get_all_symbols(self) -> List[str]:
        """Get all symbols in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT DISTINCT symbol FROM stock_candles ORDER BY symbol')
                return [row[0] for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logging.error(f"Error getting symbols: {e}")
            return []
    
    def get_total_records(self) -> int:
        """Get total number of records in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM stock_candles')
                return cursor.fetchone()[0]
                
        except sqlite3.Error as e:
            logging.error(f"Error getting total records: {e}")
            return 0
    
    def cleanup_old_data(self, days_to_keep: int = None) -> int:
        """Remove old data beyond specified days"""
        if days_to_keep is None:
            days_to_keep = Config.KEEP_DATA_DAYS
            
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM stock_candles 
                    WHERE timestamp < ?
                ''', (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logging.info(f"Cleaned up {deleted_count} old records")
                return deleted_count
                
        except sqlite3.Error as e:
            logging.error(f"Error cleaning up old data: {e}")
            return 0
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total records
                cursor.execute('SELECT COUNT(*) FROM stock_candles')
                total_records = cursor.fetchone()[0]
                
                # Records per symbol
                cursor.execute('''
                    SELECT symbol, COUNT(*) 
                    FROM stock_candles 
                    GROUP BY symbol 
                    ORDER BY COUNT(*) DESC
                ''')
                symbol_counts = dict(cursor.fetchall())
                
                # Date range
                cursor.execute('''
                    SELECT MIN(timestamp), MAX(timestamp) 
                    FROM stock_candles
                ''')
                date_range = cursor.fetchone()
                
                return {
                    'total_records': total_records,
                    'symbol_counts': symbol_counts,
                    'date_range': date_range,
                    'database_size': self._get_database_size()
                }
                
        except sqlite3.Error as e:
            logging.error(f"Error getting database stats: {e}")
            return {}
    
    def _get_database_size(self) -> str:
        """Get database file size in MB"""
        try:
            import os
            size_bytes = os.path.getsize(self.db_path)
            size_mb = size_bytes / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        except:
            return "Unknown"
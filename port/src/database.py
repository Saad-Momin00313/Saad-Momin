import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List
import os

class Database:
    def __init__(self, db_path="data/portfolio.db"):
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.initialize_db()
    
    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def initialize_db(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create assets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    name TEXT,
                    type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    purchase_price REAL NOT NULL,
                    purchase_date TEXT NOT NULL,
                    sector TEXT,
                    metadata TEXT
                )
            ''')
            
            # Create cache table for API responses
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            ''')
            
            conn.commit()
    
    def add_asset(self, asset_data: Dict[str, Any]) -> bool:
        """Add a new asset to the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO assets (
                        id, symbol, name, type, quantity, 
                        purchase_price, purchase_date, sector, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    asset_data['id'],
                    asset_data['symbol'],
                    asset_data.get('name'),
                    asset_data['type'],
                    asset_data['quantity'],
                    asset_data['purchase_price'],
                    asset_data['purchase_date'],
                    asset_data.get('sector'),
                    json.dumps(asset_data.get('metadata', {}))
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding asset: {e}")
            return False
    
    def get_all_assets(self) -> Dict[str, Dict[str, Any]]:
        """Get all assets from the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM assets')
            rows = cursor.fetchall()
            
            assets = {}
            for row in rows:
                asset_dict = dict(row)
                asset_dict['metadata'] = json.loads(asset_dict['metadata'])
                assets[asset_dict['id']] = asset_dict
            
            return assets
    
    def remove_asset(self, asset_id: str) -> bool:
        """Remove an asset from the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM assets WHERE id = ?', (asset_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error removing asset: {e}")
            return False
    
    def update_asset(self, asset_id: str, asset_data: Dict[str, Any]) -> bool:
        """Update an existing asset"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE assets 
                    SET symbol=?, name=?, type=?, quantity=?, 
                        purchase_price=?, purchase_date=?, sector=?, metadata=?
                    WHERE id=?
                ''', (
                    asset_data['symbol'],
                    asset_data.get('name'),
                    asset_data['type'],
                    asset_data['quantity'],
                    asset_data['purchase_price'],
                    asset_data['purchase_date'],
                    asset_data.get('sector'),
                    json.dumps(asset_data.get('metadata', {})),
                    asset_id
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating asset: {e}")
            return False
    
    def get_cache(self, key: str) -> Dict[str, Any]:
        """Get cached data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT value, timestamp FROM cache WHERE key = ?',
                (key,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    'value': json.loads(row['value']),
                    'timestamp': row['timestamp']
                }
            return None
    
    def set_cache(self, key: str, value: Any, timestamp: float) -> bool:
        """Set cache data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO cache (key, value, timestamp)
                    VALUES (?, ?, ?)
                ''', (key, json.dumps(value), timestamp))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error setting cache: {e}")
            return False
    
    def clear_expired_cache(self, max_age: float) -> bool:
        """Clear expired cache entries"""
        try:
            current_time = datetime.now().timestamp()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM cache WHERE ? - timestamp > ?',
                    (current_time, max_age)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return False 
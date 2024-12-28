import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

class ExpenseDatabase:
    def __init__(self, db_name='expenses.db'):
        """
        Initialize database connection and create tables if not exists
        """
        self.db_name = db_name
        self._setup_logging()
        self._init_database()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_name)
        try:
            yield conn
        except Exception as e:
            self.logger.error(f"Database error: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database tables and indices"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if we need to migrate the budgets table
            cursor.execute("PRAGMA table_info(budgets)")
            columns = {col[1] for col in cursor.fetchall()}
            
            # If old table exists but needs migration
            if 'category' in columns and 'created_at' not in columns:
                self.logger.info("Migrating budgets table to new schema")
                # Rename old table
                cursor.execute("ALTER TABLE budgets RENAME TO budgets_old")
                
                # Create new table with updated schema
                cursor.execute('''
                    CREATE TABLE budgets (
                        id INTEGER PRIMARY KEY,
                        category TEXT UNIQUE NOT NULL,
                        monthly_limit REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Copy data from old table
                cursor.execute('''
                    INSERT INTO budgets (category, monthly_limit)
                    SELECT category, monthly_limit FROM budgets_old
                ''')
                
                # Drop old table
                cursor.execute("DROP TABLE budgets_old")
                
                conn.commit()
                self.logger.info("Budget table migration completed")
            elif 'category' not in columns:
                # Create new table if it doesn't exist
                self.logger.info("Creating new budgets table")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS budgets (
                        id INTEGER PRIMARY KEY,
                        category TEXT UNIQUE NOT NULL,
                        monthly_limit REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            
            # Create or update expenses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indices for better query performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_budgets_category ON budgets(category)')
            
            conn.commit()
            self.logger.info("Database initialization completed")
    
    def add_expense(self, category: str, amount: float, description: Optional[str] = None, date: Optional[str] = None) -> bool:
        """
        Add a new expense to the database with validation
        """
        try:
            if amount <= 0:
                raise ValueError("Amount must be positive")
                
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            else:
                # Validate date format
                datetime.strptime(date, "%Y-%m-%d")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO expenses (date, category, amount, description)
                    VALUES (?, ?, ?, ?)
                ''', (date, category, amount, description))
                conn.commit()
                self.logger.info(f"Added expense: {amount} in {category} on {date}")
                return True
        except Exception as e:
            self.logger.error(f"Error adding expense: {str(e)}")
            return False
    
    def set_budget(self, category: str, monthly_limit: float) -> bool:
        """
        Set or update budget for a specific category with validation
        """
        try:
            self.logger.info(f"Attempting to set budget - Category: {category}, Type: {type(category)}, "
                            f"Monthly Limit: {monthly_limit}, Type: {type(monthly_limit)}")
            
            if not category:
                self.logger.error("Category cannot be empty")
                raise ValueError("Category cannot be empty")
                
            if monthly_limit <= 0:
                self.logger.error(f"Invalid monthly limit: {monthly_limit}")
                raise ValueError("Monthly limit must be positive")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First check if the category exists
                self.logger.debug(f"Checking if category exists: {category}")
                cursor.execute('SELECT category FROM budgets WHERE category = ?', (category,))
                exists = cursor.fetchone()
                
                if exists:
                    self.logger.info(f"Updating existing budget for {category}")
                    try:
                        cursor.execute('''
                            UPDATE budgets 
                            SET monthly_limit = ?
                            WHERE category = ?
                        ''', (monthly_limit, category))
                        self.logger.debug(f"Update query executed. Rows affected: {cursor.rowcount}")
                    except sqlite3.Error as e:
                        self.logger.error(f"Error during UPDATE: {str(e)}")
                        raise
                else:
                    self.logger.info(f"Creating new budget for {category}")
                    try:
                        cursor.execute('''
                            INSERT INTO budgets (category, monthly_limit)
                            VALUES (?, ?)
                        ''', (category, monthly_limit))
                        self.logger.debug(f"Insert query executed. Rows affected: {cursor.rowcount}")
                    except sqlite3.Error as e:
                        self.logger.error(f"Error during INSERT: {str(e)}")
                        raise
                
                conn.commit()
                self.logger.debug("Transaction committed")
                
                # Verify the update
                cursor.execute('SELECT monthly_limit FROM budgets WHERE category = ?', (category,))
                result = cursor.fetchone()
                self.logger.debug(f"Verification query result: {result}")
                
                if result and abs(result[0] - monthly_limit) < 0.01:  # Using float comparison with tolerance
                    self.logger.info(f"Successfully set budget for {category} to {monthly_limit}")
                    return True
                else:
                    self.logger.error(f"Failed to verify budget update for {category}. "
                                    f"Expected: {monthly_limit}, Got: {result[0] if result else None}")
                    return False
                    
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error setting budget: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error setting budget: {str(e)}")
            return False
    
    def get_expenses(self, start_date: Optional[str] = None, end_date: Optional[str] = None,
                    category: Optional[str] = None) -> pd.DataFrame:
        """
        Retrieve expenses with flexible filtering
        """
        try:
            query = "SELECT * FROM expenses WHERE 1=1"
            params = []
            
            if start_date and end_date:
                query += " AND date BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            query += " ORDER BY date DESC"
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                return df
        except Exception as e:
            self.logger.error(f"Error retrieving expenses: {str(e)}")
            return pd.DataFrame()
    
    def get_budget_summary(self) -> pd.DataFrame:
        """
        Get detailed budget summary with current spending and trends
        """
        try:
            query = '''
                WITH monthly_spending AS (
                    SELECT 
                        category,
                        SUM(amount) as current_spend,
                        COUNT(*) as transaction_count
                    FROM expenses
                    WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
                    GROUP BY category
                )
                SELECT 
                    b.category, 
                    b.monthly_limit,
                    COALESCE(ms.current_spend, 0) as current_spend,
                    COALESCE(ms.transaction_count, 0) as transaction_count,
                    (b.monthly_limit - COALESCE(ms.current_spend, 0)) as remaining,
                    ROUND(COALESCE(ms.current_spend * 100.0 / b.monthly_limit, 0), 1) as usage_percentage
                FROM budgets b
                LEFT JOIN monthly_spending ms ON b.category = ms.category
                WHERE b.monthly_limit > 0
                ORDER BY usage_percentage DESC
            '''
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn)
                return df
        except Exception as e:
            self.logger.error(f"Error generating budget summary: {str(e)}")
            return pd.DataFrame()
    
    def get_spending_trends(self, months: int = 6) -> Dict[str, Any]:
        """
        Get spending trends over the specified number of months
        """
        try:
            start_date = (datetime.now() - timedelta(days=30 * months)).strftime("%Y-%m-%d")
            
            query = '''
                WITH RECURSIVE dates(date) AS (
                    SELECT date('now', 'start of month', '-5 months')
                    UNION ALL
                    SELECT date(date, '+1 month')
                    FROM dates
                    WHERE date < date('now', 'start of month')
                ),
                monthly_totals AS (
                    SELECT 
                        strftime('%Y-%m', date) as month,
                        category,
                        COALESCE(SUM(amount), 0) as total_amount,
                        COUNT(*) as transaction_count,
                        COALESCE(AVG(amount), 0) as avg_transaction
                    FROM expenses
                    WHERE date >= ?
                    GROUP BY month, category
                )
                SELECT 
                    strftime('%Y-%m', dates.date) as month,
                    COALESCE(mt.category, 'No Data') as category,
                    COALESCE(mt.total_amount, 0) as total_amount,
                    COALESCE(mt.transaction_count, 0) as transaction_count,
                    COALESCE(mt.avg_transaction, 0) as avg_transaction
                FROM dates
                LEFT JOIN monthly_totals mt ON strftime('%Y-%m', dates.date) = mt.month
                ORDER BY dates.date DESC
            '''
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=[start_date])
                
                trends = {
                    'monthly_totals': df.groupby('month')['total_amount'].sum().to_dict(),
                    'category_trends': df.groupby('category')['total_amount'].sum().to_dict(),
                    'transaction_counts': df.groupby('month')['transaction_count'].sum().to_dict(),
                    'average_transaction': float(df['avg_transaction'].mean() if not df.empty else 0)
                }
                return trends
        except Exception as e:
            self.logger.error(f"Error analyzing spending trends: {str(e)}")
            return {}
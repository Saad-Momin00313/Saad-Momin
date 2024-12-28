import sqlite3
from datetime import datetime, timedelta
import json
import pandas as pd
from typing import Dict, List
from config import logger

class Database:
    def __init__(self):
        """Initialize database and create tables if they don't exist."""
        try:
            # Connect to database without deleting it
            self.conn = sqlite3.connect('mindfulness.db', check_same_thread=False)
            self.create_tables()
            
            # Initialize default user only if users table is empty
            cursor = self.conn.execute('SELECT COUNT(*) FROM users')
            if cursor.fetchone()[0] == 0:
                self._initialize_default_data()
                
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise

    def _initialize_default_data(self):
        """Initialize default user and sample data."""
        try:
            with self.conn:
                # Create default user if not exists
                self.conn.execute('''
                    INSERT OR IGNORE INTO users (id, name, age, stress_level, interests)
                    VALUES (1, 'Guest', 25, 'Moderate', '["Meditation"]')
                ''')
        except Exception as e:
            logger.error(f"Error initializing default data: {str(e)}")
            raise

    def create_tables(self):
        """Create necessary database tables if they don't exist."""
        try:
            with self.conn:
                # Users table with enhanced settings and goals
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        age INTEGER,
                        stress_level TEXT,
                        interests TEXT,
                        daily_goal_minutes INTEGER DEFAULT 10,
                        weekly_goal_minutes INTEGER DEFAULT 70,
                        theme TEXT DEFAULT 'Dark',
                        accent_color TEXT DEFAULT '#64B5F6',
                        reminder_time TEXT,
                        enable_notifications BOOLEAN DEFAULT FALSE,
                        preferred_times TEXT,
                        focus_areas TEXT,
                        difficulty_level TEXT DEFAULT 'Beginner',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP
                    )
                ''')
                
                # Add any missing columns to existing users table
                for column in [
                    ('weekly_goal_minutes', 'INTEGER DEFAULT 70'),
                    ('preferred_times', 'TEXT'),
                    ('focus_areas', 'TEXT'),
                    ('difficulty_level', 'TEXT DEFAULT "Beginner"')
                ]:
                    try:
                        self.conn.execute(f'ALTER TABLE users ADD COLUMN {column[0]} {column[1]}')
                    except sqlite3.OperationalError:
                        pass  # Column already exists
                
                # Activities table with enhanced tracking
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS activities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        activity_text TEXT,
                        category TEXT,
                        duration INTEGER,
                        rating INTEGER,
                        mood_before TEXT,
                        mood_after TEXT,
                        feedback TEXT,
                        completed BOOLEAN DEFAULT FALSE,
                        completed_at TIMESTAMP,
                        scheduled_for TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        routine_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (routine_id) REFERENCES user_routines (id)
                    )
                ''')
                
                # Mood tracking table
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS mood_tracker (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        mood TEXT,
                        energy_level INTEGER,
                        stress_level INTEGER,
                        notes TEXT,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Achievements table
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS achievements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        achievement_type TEXT,
                        description TEXT,
                        achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Enhanced practice routines table
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS user_routines (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        name TEXT NOT NULL,
                        steps TEXT NOT NULL,
                        duration INTEGER,
                        category TEXT,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_practiced TIMESTAMP,
                        practice_count INTEGER DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                ''')
                
                # Session state table for recovery
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS session_states (
                        user_id INTEGER PRIMARY KEY,
                        current_activity TEXT,
                        timer_state TEXT,
                        time_left INTEGER,
                        start_time TIMESTAMP,
                        is_paused BOOLEAN DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                ''')
                
                # Goal tracking table
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS goal_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        goal_type TEXT,
                        target_minutes INTEGER,
                        start_date TIMESTAMP,
                        end_date TIMESTAMP,
                        completed_minutes INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'in_progress',
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                ''')
                
                # Practice history with enhanced tracking
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS practice_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        activity_id INTEGER,
                        routine_id INTEGER,
                        duration INTEGER,
                        completed_at TIMESTAMP,
                        mood_before TEXT,
                        mood_after TEXT,
                        notes TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (activity_id) REFERENCES activities(id),
                        FOREIGN KEY (routine_id) REFERENCES user_routines(id)
                    )
                ''')
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise

    def get_user_stats(self, user_id: int) -> Dict:
        """Get user's statistics and progress."""
        try:
            # Get previous total minutes (before today)
            previous_total = self.conn.execute('''
                SELECT COALESCE(SUM(duration), 0)
                FROM activities
                WHERE user_id = ? 
                AND completed = 1
                AND date(created_at) < date('now')
                AND duration > 0
            ''', (user_id,)).fetchone()[0]

            # Get today's total minutes
            today_total = self.conn.execute('''
                SELECT COALESCE(SUM(duration), 0)
                FROM activities
                WHERE user_id = ? 
                AND completed = 1
                AND date(created_at) = date('now')
                AND duration > 0
            ''', (user_id,)).fetchone()[0]

            # Calculate total minutes
            total_minutes = previous_total + today_total
            
            # Current streak
            streak = self.calculate_streak(user_id)
            
            # Monthly progress
            monthly_progress = self.get_monthly_progress(user_id)
            
            return {
                "total_minutes": total_minutes or 0,
                "previous_total": previous_total or 0,
                "today_total": today_total or 0,
                "current_streak": streak or 0,
                "monthly_progress": monthly_progress or []
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return {
                "total_minutes": 0,
                "previous_total": 0,
                "today_total": 0,
                "current_streak": 0,
                "monthly_progress": []
            }

    def calculate_streak(self, user_id: int) -> int:
        """Calculate current streak of consecutive days with completed activities."""
        try:
            today = datetime.now().date()
            streak = 0
            
            while True:
                check_date = today - timedelta(days=streak)
                has_activity = self.conn.execute('''
                    SELECT EXISTS (
                        SELECT 1 FROM activities
                        WHERE user_id = ?
                        AND date(created_at) = date(?)
                        AND completed = 1
                    )
                ''', (user_id, check_date)).fetchone()[0]
                
                if not has_activity:
                    break
                streak += 1
            
            return streak
        except Exception as e:
            logger.error(f"Error calculating streak: {str(e)}")
            return 0

    def get_monthly_progress(self, user_id: int) -> List[Dict]:
        """Get daily progress for the current month."""
        try:
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            return self.conn.execute('''
                SELECT date(created_at) as date,
                       SUM(duration) as total_minutes
                FROM activities
                WHERE user_id = ?
                AND strftime('%m', created_at) = ?
                AND strftime('%Y', created_at) = ?
                AND completed = 1
                GROUP BY date(created_at)
                ORDER BY date(created_at)
            ''', (user_id, str(current_month).zfill(2), str(current_year))).fetchall()
        except Exception as e:
            logger.error(f"Error getting monthly progress: {str(e)}")
            return []

    def save_activity(self, user_id: int, activity_data: Dict) -> int:
        """Save a new activity."""
        try:
            cursor = self.conn.execute('''
                INSERT INTO activities (
                    user_id, activity_text, category, duration,
                    mood_before, completed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                activity_data['text'],
                activity_data['category'],
                activity_data.get('actual_duration', 0),
                activity_data.get('mood_before', 'Neutral'),
                False,
                datetime.now()
            ))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving activity: {str(e)}")
            self.conn.rollback()
            return None

    def update_activity_completion(self, activity_id: int, duration: int, mood_after: str, rating: int, feedback: str):
        """Update activity with completion details."""
        try:
            if duration <= 0:
                logger.warning(f"Invalid duration ({duration}) for activity {activity_id}")
                duration = 1
            
            self.conn.execute('''
                UPDATE activities
                SET completed = 1,
                    duration = ?,
                    mood_after = ?,
                    rating = ?,
                    feedback = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (duration, mood_after, rating, feedback, activity_id))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating activity completion: {str(e)}")
            self.conn.rollback()
            raise

    def get_mood_data(self, user_id: int, days: int = 30) -> Dict:
        """Get mood and energy data for the specified number of days."""
        try:
            data = self.conn.execute('''
                SELECT 
                    date(recorded_at) as date,
                    AVG(CASE 
                        WHEN mood = 'Very Low' THEN 1
                        WHEN mood = 'Low' THEN 2
                        WHEN mood = 'Neutral' THEN 3
                        WHEN mood = 'Good' THEN 4
                        WHEN mood = 'Excellent' THEN 5
                    END) as mood_score,
                    AVG(energy_level) as energy_level
                FROM mood_tracker
                WHERE user_id = ?
                AND recorded_at >= date('now', ?)
                GROUP BY date(recorded_at)
                ORDER BY date(recorded_at)
            ''', (user_id, f'-{days} days')).fetchall()
            
            return {
                'dates': [row[0] for row in data],
                'mood': [row[1] for row in data],
                'energy': [row[2] for row in data]
            }
        except Exception as e:
            logger.error(f"Error getting mood data: {str(e)}")
            return {'dates': [], 'mood': [], 'energy': []}

    def update_user_settings(self, user_id: int, settings: Dict):
        """Update user settings in the database."""
        try:
            user_exists = self.conn.execute(
                'SELECT 1 FROM users WHERE id = ?', (user_id,)
            ).fetchone()
            
            if not user_exists:
                raise ValueError(f"User {user_id} not found")
            
            self.conn.execute('''
                UPDATE users
                SET daily_goal_minutes = ?,
                    theme = ?,
                    accent_color = ?,
                    reminder_time = ?,
                    enable_notifications = ?
                WHERE id = ?
            ''', (
                settings.get('daily_goal', 10),
                settings.get('theme', 'Dark'),
                settings.get('accent_color', '#64B5F6'),
                settings.get('reminder_time', None),
                settings.get('enable_notifications', False),
                user_id
            ))
            self.conn.commit()
            logger.info(f"Settings updated successfully for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating user settings: {str(e)}")
            self.conn.rollback()
            raise

    def get_user_settings(self, user_id: int) -> Dict:
        """Get user settings from the database."""
        try:
            result = self.conn.execute('''
                SELECT 
                    daily_goal_minutes,
                    theme,
                    accent_color,
                    reminder_time,
                    enable_notifications,
                    interests
                FROM users
                WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if result:
                return {
                    'daily_goal': result[0] or 10,
                    'theme': result[1] or 'Dark',
                    'accent_color': result[2] or '#64B5F6',
                    'reminder_time': result[3],
                    'enable_notifications': bool(result[4]),
                    'interests': json.loads(result[5]) if result[5] else ["Meditation"]
                }
            
            default_settings = {
                'daily_goal': 10,
                'theme': 'Dark',
                'accent_color': '#64B5F6',
                'reminder_time': None,
                'enable_notifications': False,
                'interests': ["Meditation"]
            }
            self.update_user_settings(user_id, default_settings)
            return default_settings
            
        except Exception as e:
            logger.error(f"Error getting user settings: {str(e)}")
            return {
                'daily_goal': 10,
                'theme': 'Dark',
                'accent_color': '#64B5F6',
                'reminder_time': None,
                'enable_notifications': False,
                'interests': ["Meditation"]
            }

    def export_user_progress(self, user_id: int) -> pd.DataFrame:
        """Export user's progress data as a DataFrame."""
        try:
            # Get practice data
            practice_data = self.conn.execute('''
                SELECT 
                    date(created_at) as date,
                    category,
                    duration,
                    mood_before,
                    mood_after,
                    rating,
                    feedback
                FROM activities
                WHERE user_id = ?
                AND completed = 1
                ORDER BY created_at
            ''', (user_id,)).fetchall()
            
            # Get mood tracking data
            mood_data = self.conn.execute('''
                SELECT 
                    date(recorded_at) as date,
                    mood,
                    energy_level,
                    stress_level,
                    notes
                FROM mood_tracker
                WHERE user_id = ?
                ORDER BY recorded_at
            ''', (user_id,)).fetchall()
            
            # Create DataFrames
            practice_df = pd.DataFrame(practice_data, columns=[
                'Date', 'Category', 'Duration (minutes)', 
                'Mood Before', 'Mood After', 'Rating', 'Feedback'
            ])
            
            mood_df = pd.DataFrame(mood_data, columns=[
                'Date', 'Mood', 'Energy Level', 
                'Stress Level', 'Notes'
            ])
            
            # Merge the DataFrames
            merged_df = pd.merge(
                practice_df, 
                mood_df, 
                on='Date', 
                how='outer'
            ).sort_values('Date')
            
            return merged_df
            
        except Exception as e:
            logger.error(f"Error exporting user progress: {str(e)}")
            return pd.DataFrame() 

    def save_routine(self, user_id: int, routine: Dict):
        """Save a custom routine to the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO user_routines (
                    user_id, name, steps, duration, category,
                    description, created_at, last_practiced, practice_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                routine['name'],
                json.dumps(routine['steps']),
                routine['duration'],
                routine['category'],
                routine['description'],
                routine['created_at'],
                routine['last_practiced'],
                routine['practice_count']
            ))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving routine: {str(e)}")
            self.conn.rollback()
            raise

    def get_user_routines(self, user_id: int) -> List[Dict]:
        """Get all custom routines for a user."""
        try:
            cursor = self.conn.execute('''
                SELECT * FROM user_routines
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            
            routines = []
            for row in cursor.fetchall():
                routine = {
                    'id': row[0],
                    'name': row[2],
                    'steps': json.loads(row[3]),
                    'duration': row[4],
                    'category': row[5],
                    'description': row[6],
                    'created_at': row[7],
                    'last_practiced': row[8],
                    'practice_count': row[9]
                }
                routines.append(routine)
            return routines
        except Exception as e:
            logger.error(f"Error getting user routines: {str(e)}")
            return []

    def update_routine(self, routine_id: int, routine: Dict):
        """Update an existing routine."""
        try:
            self.conn.execute('''
                UPDATE user_routines
                SET name = ?,
                    steps = ?,
                    duration = ?,
                    category = ?,
                    description = ?,
                    last_practiced = ?,
                    practice_count = ?
                WHERE id = ?
            ''', (
                routine['name'],
                json.dumps(routine['steps']),
                routine['duration'],
                routine['category'],
                routine['description'],
                routine['last_practiced'],
                routine['practice_count'],
                routine_id
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating routine: {str(e)}")
            self.conn.rollback()
            raise

    def delete_routine(self, routine_id: int):
        """Delete a custom routine."""
        try:
            self.conn.execute('DELETE FROM user_routines WHERE id = ?', (routine_id,))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error deleting routine: {str(e)}")
            self.conn.rollback()
            raise

    def save_session_state(self, user_id: int, session_data: Dict):
        """Save session state for recovery."""
        try:
            self.conn.execute('''
                INSERT OR REPLACE INTO session_states (
                    user_id, current_activity, timer_state, 
                    time_left, start_time, is_paused
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                json.dumps(session_data.get('current_activity')),
                session_data.get('timer_state', 'stopped'),
                session_data.get('time_left', 0),
                session_data.get('start_time'),
                session_data.get('is_paused', False)
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error saving session state: {str(e)}")
            self.conn.rollback()

    def get_session_state(self, user_id: int) -> Dict:
        """Retrieve saved session state."""
        try:
            result = self.conn.execute('''
                SELECT current_activity, timer_state, time_left, 
                       start_time, is_paused
                FROM session_states
                WHERE user_id = ?
            ''', (user_id,)).fetchone()
            
            if result:
                return {
                    'current_activity': json.loads(result[0]) if result[0] else None,
                    'timer_state': result[1],
                    'time_left': result[2],
                    'start_time': result[3],
                    'is_paused': bool(result[4])
                }
            return None
        except Exception as e:
            logger.error(f"Error getting session state: {str(e)}")
            return None

    def update_practice_goals(self, user_id: int, goals: Dict):
        """Update user's practice goals and preferences."""
        try:
            self.conn.execute('''
                UPDATE users
                SET daily_goal_minutes = ?,
                    weekly_goal_minutes = ?,
                    preferred_times = ?,
                    focus_areas = ?,
                    difficulty_level = ?
                WHERE id = ?
            ''', (
                goals.get('daily_goal', 10),
                goals.get('weekly_goal', 70),
                json.dumps(goals.get('preferred_times', [])),
                json.dumps(goals.get('focus_areas', [])),
                goals.get('difficulty_level', 'Beginner'),
                user_id
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating practice goals: {str(e)}")
            self.conn.rollback()
            raise

    def get_practice_goals(self, user_id: int) -> Dict:
        """Get user's practice goals and preferences."""
        try:
            result = self.conn.execute('''
                SELECT daily_goal_minutes, weekly_goal_minutes,
                       preferred_times, focus_areas, difficulty_level
                FROM users
                WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if result:
                return {
                    'daily_goal': result[0] or 10,
                    'weekly_goal': result[1] or 70,
                    'preferred_times': json.loads(result[2]) if result[2] else [],
                    'focus_areas': json.loads(result[3]) if result[3] else [],
                    'difficulty_level': result[4] or 'Beginner'
                }
            return None
        except Exception as e:
            logger.error(f"Error getting practice goals: {str(e)}")
            return None 
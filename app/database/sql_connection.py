"""
SQLite Database Connection Manager
Handles database connection, initialization, and query execution
"""
import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from app.config import SQLITE_DB_PATH


class SQLiteConnection:
    """SQLite connection manager with connection pooling simulation"""
    
    _instance: Optional['SQLiteConnection'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Ensure data directory exists
        os.makedirs(SQLITE_DB_PATH.parent, exist_ok=True)
        
        self.db_path = str(SQLITE_DB_PATH)
        self._initialized = True
        
        # Initialize database schema
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema from SQL file"""
        schema_path = Path(__file__).parent / "schema.sql"
        
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            with self.get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with context manager"""
        # Add timeout to handle potential concurrency
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        # Enable WAL mode for better concurrency (Write-Ahead Logging)
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
        finally:
            conn.close()
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single query"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor
    
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute a query with multiple parameter sets"""
        with self.get_connection() as conn:
            conn.executemany(query, params_list)
            conn.commit()
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def search_fts(self, table: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Full-text search on FTS tables"""
        fts_query = f"""
            SELECT * FROM {table}
            WHERE {table} MATCH ?
            LIMIT ?
        """
        return self.fetch_all(fts_query, (query, limit))


# Singleton instance
db = SQLiteConnection()


def get_db() -> SQLiteConnection:
    """Get database instance (for dependency injection)"""
    return db

"""
Database Migration Script
Updates entity_relations table to support new relation types
"""
import sqlite3
import os
from pathlib import Path

# Get database path
db_path = Path(__file__).parent / "data" / "memory.db"

if not db_path.exists():
    print(f"Database not found at {db_path}")
    print("The database will be created with the correct schema on first run.")
    exit(0)

print(f"Migrating database: {db_path}")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    # SQLite doesn't support modifying CHECK constraints directly
    # We need to recreate the table
    
    # Step 1: Create new table with updated schema
    print("Creating new table with updated schema...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entity_relations_new (
            relation_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            entity_1 TEXT NOT NULL,
            entity_2 TEXT NOT NULL,
            relation_type TEXT NOT NULL CHECK (relation_type IN (
                'associated_with', 'depends_on', 'overrides', 'similar_to', 
                'opposite_of', 'part_of', 'likes', 'knows', 'uses', 'prefers', 
                'has', 'lives_in', 'works_with', 'related_to'
            )),
            confidence_score REAL DEFAULT 0.5 CHECK (confidence_score >= 0 AND confidence_score <= 1),
            source_message_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (source_message_id) REFERENCES conversation_logs(message_id) ON DELETE SET NULL
        )
    """)
    
    # Step 2: Copy data from old table (if it exists)
    print("Copying existing data...")
    cursor.execute("""
        INSERT INTO entity_relations_new 
        SELECT * FROM entity_relations
    """)
    
    # Step 3: Drop old table
    print("Dropping old table...")
    cursor.execute("DROP TABLE entity_relations")
    
    # Step 4: Rename new table
    print("Renaming new table...")
    cursor.execute("ALTER TABLE entity_relations_new RENAME TO entity_relations")
    
    # Step 5: Recreate indexes
    print("Recreating indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_relations_user_id ON entity_relations(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_relations_entity_1 ON entity_relations(entity_1)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_relations_entity_2 ON entity_relations(entity_2)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_relations_type ON entity_relations(relation_type)")
    
    conn.commit()
    print("[SUCCESS] Migration completed successfully!")
    print("  Updated relation_type constraint to include: likes, knows, uses, prefers, has, lives_in, works_with, related_to")
    
except sqlite3.OperationalError as e:
    if "no such table" in str(e).lower():
        print("Table doesn't exist yet. It will be created with correct schema on first run.")
    else:
        print(f"Error during migration: {e}")
        conn.rollback()
except Exception as e:
    print(f"Unexpected error: {e}")
    conn.rollback()
finally:
    conn.close()

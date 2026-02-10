-- ============================================
-- LLM Memory Management System - SQL Schema
-- SQLite Database Schema (Normalized to 3NF)
-- ============================================

-- Enable foreign key support
PRAGMA foreign_keys = ON;

-- ============================================
-- TABLE: users
-- Stores user identity and personalization data
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preferences_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- ============================================
-- TABLE: sessions
-- Represents individual interaction sessions
-- ============================================
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at);

-- ============================================
-- TABLE: conversation_logs
-- Stores complete conversational history
-- ============================================
CREATE TABLE IF NOT EXISTS conversation_logs (
    message_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    message_text TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conversation_user_id ON conversation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_session_id ON conversation_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_timestamp ON conversation_logs(timestamp);

-- ============================================
-- TABLE: memory_items
-- Stores extracted long-term memory (facts, preferences, skills)
-- ============================================
CREATE TABLE IF NOT EXISTS memory_items (
    memory_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    memory_type TEXT NOT NULL CHECK (memory_type IN ('fact', 'preference', 'rule', 'skill', 'context')),
    content TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.5 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    source_message_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    importance_weight REAL DEFAULT 0.5 CHECK (importance_weight >= 0 AND importance_weight <= 1),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (source_message_id) REFERENCES conversation_logs(message_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_user_id ON memory_items(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_items(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_confidence ON memory_items(confidence_score);
CREATE INDEX IF NOT EXISTS idx_memory_importance ON memory_items(importance_weight);

-- ============================================
-- TABLE: entity_relations
-- Represents semantic relationships between entities
-- ============================================
CREATE TABLE IF NOT EXISTS entity_relations (
    relation_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    entity_1 TEXT NOT NULL,
    entity_2 TEXT NOT NULL,
    relation_type TEXT NOT NULL CHECK (relation_type IN ('associated_with', 'depends_on', 'overrides', 'similar_to', 'opposite_of', 'part_of', 'likes', 'knows', 'uses', 'prefers', 'has', 'lives_in', 'works_with', 'related_to')),
    confidence_score REAL DEFAULT 0.5 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    source_message_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (source_message_id) REFERENCES conversation_logs(message_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_entity_relations_user_id ON entity_relations(user_id);
CREATE INDEX IF NOT EXISTS idx_entity_relations_entity_1 ON entity_relations(entity_1);
CREATE INDEX IF NOT EXISTS idx_entity_relations_entity_2 ON entity_relations(entity_2);
CREATE INDEX IF NOT EXISTS idx_entity_relations_type ON entity_relations(relation_type);

-- ============================================
-- TABLE: memory_access_logs
-- Tracks memory access patterns for optimization
-- ============================================
CREATE TABLE IF NOT EXISTS memory_access_logs (
    access_id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usage_context TEXT,
    FOREIGN KEY (memory_id) REFERENCES memory_items(memory_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memory_access_memory_id ON memory_access_logs(memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_access_time ON memory_access_logs(access_time);

-- ============================================
-- FULL-TEXT SEARCH (FTS5)
-- For efficient memory content search
-- ============================================
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    memory_id,
    content,
    content='memory_items',
    content_rowid='rowid'
);

-- Triggers to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS memory_fts_insert AFTER INSERT ON memory_items BEGIN
    INSERT INTO memory_fts(memory_id, content) VALUES (new.memory_id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS memory_fts_delete AFTER DELETE ON memory_items BEGIN
    INSERT INTO memory_fts(memory_fts, memory_id, content) VALUES ('delete', old.memory_id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS memory_fts_update AFTER UPDATE ON memory_items BEGIN
    INSERT INTO memory_fts(memory_fts, memory_id, content) VALUES ('delete', old.memory_id, old.content);
    INSERT INTO memory_fts(memory_id, content) VALUES (new.memory_id, new.content);
END;

-- ============================================
-- CONVERSATION FTS (Full-text search on messages)
-- ============================================
CREATE VIRTUAL TABLE IF NOT EXISTS conversation_fts USING fts5(
    message_id,
    message_text,
    content='conversation_logs',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS conversation_fts_insert AFTER INSERT ON conversation_logs BEGIN
    INSERT INTO conversation_fts(message_id, message_text) VALUES (new.message_id, new.message_text);
END;

CREATE TRIGGER IF NOT EXISTS conversation_fts_delete AFTER DELETE ON conversation_logs BEGIN
    INSERT INTO conversation_fts(conversation_fts, message_id, message_text) VALUES ('delete', old.message_id, old.message_text);
END;

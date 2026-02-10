"""
MongoDB Connection Manager
Handles NoSQL database connection for unstructured NLP metadata
"""
import logging
import os
import sys

# Configure logging
logger = logging.getLogger(__name__)

# Fix Windows encoding issue before importing pymongo
from typing import Optional, Dict, Any, List
from datetime import datetime

# Fix Windows encoding issue before importing pymongo
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.database import Database
    PYMONGO_AVAILABLE = True
except Exception as e:
    PYMONGO_AVAILABLE = False
    MongoClient = None
    Collection = None
    Database = None
    logger.warning(f"Note: pymongo not available ({e}). MongoDB features disabled.")

from app.config import MONGODB_URI, MONGODB_DB_NAME


class MongoDBConnection:
    """Singleton MongoDB connection manager"""
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._client: Optional[Any] = None
        self._db: Optional[Any] = None
        self._connected = False
        self._initialized = True
        
        # Try to connect
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection"""
        if not PYMONGO_AVAILABLE:
            logger.warning("Note: pymongo not installed. MongoDB features disabled.")
            return
        
        try:
            # Use short timeout to avoid blocking startup
            self._client = MongoClient(
                MONGODB_URI, 
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
                socketTimeoutMS=5000
            )
            # Test connection
            self._client.admin.command('ping')
            self._db = self._client[MONGODB_DB_NAME]
            self._connected = True
            
            # Create indexes
            self._create_indexes()
            logger.info(f"Connected to MongoDB: {MONGODB_DB_NAME}")
        except Exception as e:
            logger.warning(f"Could not connect to MongoDB: {e}")
            logger.info("NLP metadata will not be stored in MongoDB.")
            self._connected = False
    
    def _create_indexes(self):
        """Create indexes for better query performance"""
        if not self._connected:
            return
        
        try:
            # NLP Processing Logs indexes
            self._db["nlp_processing_logs"].create_index("message_id")
            self._db["nlp_processing_logs"].create_index("user_id")
            self._db["nlp_processing_logs"].create_index("created_at")
            self._db["nlp_processing_logs"].create_index("memory_type")
            self._db["nlp_processing_logs"].create_index("extracted_entities.label")
            
            # Embedding cache indexes
            self._db["embedding_cache"].create_index("text_hash", unique=True)
            
            # Raw extractions indexes
            self._db["raw_extractions"].create_index("message_id")
        except Exception as e:
            logger.warning(f"Note: Could not create MongoDB indexes: {e}")
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def db(self) -> Optional[Any]:
        """Get database instance"""
        return self._db if self._connected else None
    
    @property
    def nlp_logs(self) -> Optional[Any]:
        """NLP Processing Logs collection"""
        return self._db["nlp_processing_logs"] if self._connected else None
    
    @property
    def embeddings(self) -> Optional[Any]:
        """Embedding cache collection"""
        return self._db["embedding_cache"] if self._connected else None
    
    @property
    def raw_extractions(self) -> Optional[Any]:
        """Raw NLP extractions collection"""
        return self._db["raw_extractions"] if self._connected else None
    
    # CRUD Operations
    def insert_nlp_log(self, log_data: Dict[str, Any]) -> Optional[str]:
        """Insert NLP processing log"""
        if not self._connected:
            return None
        
        try:
            log_data["created_at"] = datetime.utcnow()
            result = self.nlp_logs.insert_one(log_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error inserting NLP log: {e}")
            return None
    
    def get_nlp_log(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get NLP log by message ID"""
        if not self._connected:
            return None
        
        try:
            log = self.nlp_logs.find_one({"message_id": message_id})
            if log:
                log["_id"] = str(log["_id"])
            return log
        except Exception as e:
            logger.error(f"Error getting NLP log: {e}")
            return None
    
    def get_user_nlp_logs(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get NLP logs for a user"""
        if not self._connected:
            return []
        
        try:
            logs = list(self.nlp_logs.find(
                {"user_id": user_id}
            ).sort("created_at", -1).limit(limit))
            
            for log in logs:
                log["_id"] = str(log["_id"])
            return logs
        except Exception as e:
            logger.error(f"Error getting user NLP logs: {e}")
            return []
    
    def store_embedding(self, text_hash: str, embedding: List[float], metadata: Dict = None) -> bool:
        """Store embedding in cache"""
        if not self._connected:
            return False
        
        try:
            doc = {
                "text_hash": text_hash,
                "embedding": embedding,
                "metadata": metadata or {},
                "created_at": datetime.utcnow()
            }
            self.embeddings.update_one(
                {"text_hash": text_hash},
                {"$set": doc},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error storing embedding: {e}")
            return False
    
    def get_embedding(self, text_hash: str) -> Optional[List[float]]:
        """Get cached embedding"""
        if not self._connected:
            return None
        
        try:
            doc = self.embeddings.find_one({"text_hash": text_hash})
            return doc["embedding"] if doc else None
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return None
    
    def store_raw_extraction(self, message_id: str, raw_data: Dict[str, Any]) -> bool:
        """Store raw NLP extraction data"""
        if not self._connected:
            return False
        
        try:
            doc = {
                "message_id": message_id,
                "raw_data": raw_data,
                "created_at": datetime.utcnow()
            }
            self.raw_extractions.insert_one(doc)
            return True
        except Exception as e:
            logger.error(f"Error storing raw extraction: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about all collections, trying to reconnect if not connected"""
        if not self._connected:
            # Try once more to connect if we weren't initially
            self._connect()
            if not self._connected:
                return {"connected": False}
        
        try:
            return {
                "connected": True,
                "database": MONGODB_DB_NAME,
                "collections": {
                    "nlp_processing_logs": self.nlp_logs.count_documents({}),
                    "embedding_cache": self.embeddings.count_documents({}),
                    "raw_extractions": self.raw_extractions.count_documents({})
                }
            }
        except Exception as e:
            # If a query fails, we might have lost connection
            self._connected = False
            return {"connected": False, "error": str(e)}

    def reconnect(self) -> bool:
        """Manually trigger a reconnection attempt"""
        self._connect()
        return self._connected
    
    def get_all_documents(self, collection_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all documents from a collection"""
        if not self._connected:
            return []
        
        try:
            collection = self._db[collection_name]
            docs = list(collection.find().sort("created_at", -1).limit(limit))
            for doc in docs:
                doc["_id"] = str(doc["_id"])
            return docs
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return []


# Singleton instance
mongo_db = MongoDBConnection()


def get_mongo_db() -> MongoDBConnection:
    return mongo_db

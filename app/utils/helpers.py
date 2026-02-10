"""
Helper utilities for the LLM Memory System
"""
import hashlib
import re
from typing import List, Optional
from datetime import datetime


def generate_text_hash(text: str) -> str:
    """Generate a SHA256 hash for text (used for embedding caching)"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def count_tokens(text: str) -> int:
    """Estimate token count (rough approximation)"""
    # Average: 1 token ≈ 4 characters for English text
    return len(text) // 4


def format_timestamp(timestamp: datetime) -> str:
    """Format timestamp for display"""
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse ISO format timestamp string"""
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def extract_sentences(text: str) -> List[str]:
    """Split text into sentences"""
    # Simple sentence splitting
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]


def calculate_similarity_score(text1: str, text2: str) -> float:
    """Calculate simple Jaccard similarity between two texts"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)


def is_question(text: str) -> bool:
    """Check if text is a question"""
    text = text.strip().lower()
    
    # Check for question mark
    if text.endswith('?'):
        return True
    
    # Check for question words at start
    question_words = ['what', 'where', 'when', 'why', 'how', 'who', 'which', 
                      'whose', 'whom', 'is', 'are', 'was', 'were', 'do', 'does',
                      'did', 'can', 'could', 'would', 'should', 'will']
    
    first_word = text.split()[0] if text.split() else ''
    return first_word in question_words


def extract_quoted_text(text: str) -> List[str]:
    """Extract text within quotes"""
    # Match both single and double quotes
    pattern = r'["\']([^"\']+)["\']'
    return re.findall(pattern, text)


def normalize_entity(entity: str) -> str:
    """Normalize entity text for comparison"""
    # Convert to lowercase and remove extra spaces
    entity = entity.lower().strip()
    # Remove common articles
    entity = re.sub(r'^(the|a|an)\s+', '', entity)
    return entity

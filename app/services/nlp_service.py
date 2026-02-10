"""
NLP Service
Handles entity extraction, memory classification, and NLP processing
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re
import time

from app.database.nosql_connection import get_mongo_db
from app.database.models import (
    ExtractedEntity, NLPProcessingLog,
    MemoryItemCreate, EntityRelationCreate
)
from app.config import SPACY_MODEL
from app.services.gemini_service import get_gemini_service
import logging

logger = logging.getLogger(__name__)

# Try to import spaCy
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not installed. NLP features will use basic extraction.")


class NLPService:
    """Service for NLP processing and memory extraction"""
    
    def __init__(self):
        self.nlp = None
        self.mongo = get_mongo_db()
        self.gemini_service = get_gemini_service()
        self._load_model()
        
        # Common words that should NOT be extracted as entities
        self.entity_stopwords = {
            "the", "a", "an", "our", "we", "i", "you", "he", "she", "they",
            "this", "that", "these", "those", "my", "your", "his", "her",
            "their", "its", "it", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "must", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "but", "and", "or", "if", "when", "where", "why", "how",
            "what", "which", "who", "whom", "whose", "while", "during",
            "before", "after", "about", "above", "below", "up", "down",
            "out", "off", "over", "under", "again", "further", "then", "once"
        }
        
        # Memory type keywords - Expanded for better detection
        self.preference_keywords = [
            "like", "likes", "prefer", "prefers", "love", "loves", "enjoy", "enjoys", 
            "favorite", "favourite", "hate", "hates", "dislike", "dislikes",
            "want", "wants", "wish", "wishes", "hope", "hopes", 
            "better", "best", "rather", "fond of", "into", "interested in",
            "enjoy doing", "love doing", "prefer to", "would rather"
        ]
        
        self.fact_keywords = [
            "is", "are", "was", "were", "have", "has", "born", "work", 
            "live", "study", "from", "name", "called", "works at", "studies at",
            "lives in", "born in", "from", "originally from"
        ]
        
        self.skill_keywords = [
            "can", "know", "knows", "learn", "learned", "learnt", "use", "uses",
            "good at", "great at", "expert", "expert in", "expert at", 
            "experience", "experienced", "experienced in", "years of experience",
            "familiar", "familiar with", "proficient", "proficient in", "proficient at",
            "skilled", "skilled in", "skilled at", "able", "able to",
            "master", "mastered", "know how to", "knows how to",
            "specialize", "specializes", "specialized", "specialized in",
            "work with", "works with", "using", "use", "uses",
            "programming", "coding", "develop", "develops", "developer"
        ]
        
        # Common technology/skill terms to help label SKILL entities (expandable)
        self.tech_terms = {
            "python", "java", "javascript", "node", "node.js", "react", "vue", "angular",
            "django", "flask", "fastapi", "sql", "postgresql", "mysql", "mongodb",
            "redis", "docker", "kubernetes", "aws", "azure", "gcp", "tensorflow",
            "pandas", "numpy", "scikit-learn", "scikit", "tailwind", "tailwindcss",
            "typescript", "express", "django", "redis", "kubernetes", "docker",
            "code", "coding", "programming", "developing", "designing"
        }

        self.rule_keywords = [
            "always", "never", "must", "should", "need", "require",
            "important", "remember", "don't", "do not"
        ]
    
    def _load_model(self):
        """Load spaCy model"""
        if not SPACY_AVAILABLE:
            return
        
        try:
            self.nlp = spacy.load(SPACY_MODEL)
            logger.info(f"Loaded spaCy model: {SPACY_MODEL}")
        except OSError:
            logger.warning(f"spaCy model '{SPACY_MODEL}' not found. Using basic extraction.")
            self.nlp = None
    
    def process_message(
        self, 
        message_text: str, 
        user_id: str,
        message_id: str
    ) -> Dict[str, Any]:
        """
        Process a message to extract entities, intents, and memory items.
        Returns extracted data and stores NLP log in MongoDB.
        """
        start_time = time.time()
        
        # Extract entities and relations using LLM
        llm_entities, llm_relations = self.gemini_service.extract_entities_and_relations(message_text)
        
        # Fallback to local extraction if LLM fails or returns nothing
        if not llm_entities:
            logger.info("[NLP] LLM extraction returned 0 entities. Falling back to local extraction.")
            local_entities = self._extract_entities(message_text)
            # Convert local entities to dicts for consistent processing
            llm_entities = [{"text": e.text, "label": e.label, "confidence": 0.7} for e in local_entities]
            
            # For relations, fallback to local extraction too
            if not llm_relations:
                local_relations = self._extract_relations(local_entities, user_id, message_id, message_text)
                llm_relations = [
                    {"entity_1": r.entity_1, "entity_2": r.entity_2, "relation_type": r.relation_type, "reason": "local_extraction"} 
                    for r in local_relations
                ]
        
        logger.debug(f"[NLP] Final entity count: {len(llm_entities)}, Relation count: {len(llm_relations)}")
        
        # Convert LLM entities to ExtractedEntity objects
        entities = []
        text_lower = message_text.lower()
        
        for i, ent in enumerate(llm_entities):
            ent_text = ent.get("text", "").strip()
            if not ent_text:
                logger.debug(f"[NLP] Skipping empty entity at index {i}")
                continue
            
            # Capitalize first letter for consistency
            ent_text = ent_text[0].upper() + ent_text[1:] if len(ent_text) > 1 else ent_text.upper()
            
            # Find start position (case-insensitive, try multiple variations)
            start_pos = text_lower.find(ent_text.lower())
            if start_pos == -1:
                # Try without capitalization
                start_pos = text_lower.find(ent_text.lower())
            if start_pos == -1:
                # Try finding partial matches
                words = ent_text.split()
                if words:
                    start_pos = text_lower.find(words[0].lower())
            if start_pos == -1:
                # Fallback: approximate position
                start_pos = min(i * 15, len(message_text) - len(ent_text))
            
            end_pos = start_pos + len(ent_text)
            
            label = ent.get("label", "OTHER").upper()
            # Ensure PERSON label for names
            if label in ("PERSON", "NAME"):
                label = "PERSON"
            
            entities.append(ExtractedEntity(
                text=ent_text,
                label=label,
                start=start_pos,
                end=end_pos,
                confidence=ent.get("confidence", 0.85)
            ))
            logger.debug(f"[NLP] Added entity: {ent_text} ({label})")
        
        logger.debug(f"[NLP] Extracted {len(entities)} entities using LLM:")
        for e in entities:
             logger.debug(f" - {e.text} ({e.label}) [{e.start}:{e.end}] conf={e.confidence}")
        
        # Extract potential memory items
        memory_items = self._classify_memory_items(message_text, user_id, message_id)
        
        # Convert LLM relations to EntityRelationCreate objects
        entity_relations = []
        entity_texts = {e.text.lower(): e.text for e in entities}  # Map for case-insensitive lookup
        
        for rel in llm_relations:
            entity_1_raw = rel.get("entity_1", "").strip()
            entity_2_raw = rel.get("entity_2", "").strip()
            relation_type = rel.get("relation_type", "associated_with").lower()
            reason = rel.get("reason", "")
            
            if not entity_1_raw or not entity_2_raw:
                logger.debug(f"[NLP] Skipping incomplete relation: {entity_1_raw} -> {entity_2_raw}")
                continue
            
            # Normalize entity names (capitalize first letter)
            entity_1 = entity_1_raw[0].upper() + entity_1_raw[1:] if len(entity_1_raw) > 1 else entity_1_raw.upper()
            entity_2 = entity_2_raw[0].upper() + entity_2_raw[1:] if len(entity_2_raw) > 1 else entity_2_raw.upper()
            
            # Try to match with extracted entities (case-insensitive)
            entity_1_matched = entity_texts.get(entity_1.lower(), entity_1)
            entity_2_matched = entity_texts.get(entity_2.lower(), entity_2)
            
            # Map relation types to valid ones
            valid_relation_types = [
                "associated_with", "likes", "knows", "uses", "prefers", "has", 
                "lives_in", "works_with", "related_to", "depends_on", "overrides", 
                "similar_to", "opposite_of", "part_of"
            ]
            if relation_type not in valid_relation_types:
                relation_type = "associated_with"
            
            # Determine confidence based on reason/explicitness
            confidence = 0.85
            if reason and len(reason) > 5:
                confidence = 0.9
            
            entity_relations.append(EntityRelationCreate(
                user_id=user_id,
                entity_1=entity_1_matched,
                entity_2=entity_2_matched,
                relation_type=relation_type,
                confidence_score=confidence,
                source_message_id=message_id
            ))
            logger.debug(f"[NLP] Added relation: {entity_1_matched} ({relation_type}) {entity_2_matched}")
        
        logger.debug(f"[NLP] Extracted {len(entity_relations)} relations using LLM:")
        for r in entity_relations:
            logger.debug(f" - {r.entity_1} ({r.relation_type}) {r.entity_2} conf={r.confidence_score}")
        
        # Extract keywords
        keywords = self._extract_keywords(message_text)
        
        # Simple intent detection
        intents = self._detect_intents(message_text)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Create NLP log
        # Determine primary memory type for the log
        primary_memory_type = memory_items[0].memory_type if memory_items else "none"
        
        nlp_log = NLPProcessingLog(
            message_id=message_id,
            user_id=user_id,
            memory_type=primary_memory_type,
            extracted_entities=entities,
            extracted_intents=intents,
            keywords=keywords,
            processing_time_ms=processing_time_ms,
            nlp_model_version=SPACY_MODEL if self.nlp else "basic"
        )
        
        # Store in MongoDB if available
        if self.mongo.is_connected:
            self.mongo.insert_nlp_log(nlp_log.model_dump())
        
        return {
            "entities": entities,
            "memory_items": memory_items,
            "entity_relations": entity_relations,
            "keywords": keywords,
            "intents": intents,
            "processing_time_ms": processing_time_ms
        }
    
    def _extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract named entities from text"""
        entities = []
        
        if self.nlp:
            # Use spaCy NER
            doc = self.nlp(text)
            for ent in doc.ents:
                # Filter out common words and short entities
                entity_text = ent.text.strip()
                if self._is_valid_entity(entity_text):
                    entities.append(ExtractedEntity(
                        text=entity_text,
                        label=ent.label_,
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=1.0
                    ))
        else:
            # Basic pattern matching fallback
            entities = self._basic_entity_extraction(text)
        
        # Normalize labels (e.g., mark technologies as SKILL, names as PERSON when appropriate)
        entities = self._normalize_entity_labels(entities, text)

        # Final filter to remove invalid entities
        entities = [e for e in entities if self._is_valid_entity(e.text)]
        
        return entities
    
    def _is_valid_entity(self, entity_text: str) -> bool:
        """Check if an entity should be kept (not a common word)"""
        if not entity_text:
            return False
        
        # Remove whitespace and convert to lowercase for comparison
        entity_lower = entity_text.strip().lower()
        
        # Filter out very short entities (1-2 characters) unless they're acronyms
        if len(entity_lower) <= 2 and not entity_lower.isupper():
            return False
        
        # Filter out common stopwords
        if entity_lower in self.entity_stopwords:
            return False
        
        # Filter out entities that are just common words (even if capitalized)
        # Check if it's a single word that's a stopword
        words = entity_lower.split()
        if len(words) == 1 and words[0] in self.entity_stopwords:
            return False
        
        # Keep entities that are:
        # - Multi-word (likely proper nouns)
        # - Known technology/framework names (we'll allow these)
        # - Person names (usually capitalized)
        # - Organization names
        
        return True
    
    def _basic_entity_extraction(self, text: str) -> List[ExtractedEntity]:
        """Basic entity extraction without spaCy"""
        entities = []
        seen_entities = set()  # Avoid duplicates
        
        # Capitalized words (potential proper nouns)
        # Match: Single capitalized word or multiple capitalized words (like "New York")
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        for match in re.finditer(pattern, text):
            entity_text = match.group().strip()
            # Filter out common words
            if self._is_valid_entity(entity_text) and entity_text.lower() not in seen_entities:
                entities.append(ExtractedEntity(
                    text=entity_text,
                    label="PROPER_NOUN",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.7
                ))
                seen_entities.add(entity_text.lower())
        
        # Also catch names mentioned after "name is", "I am", "call me", etc.
        # This catches cases where names might be mentioned in lowercase contexts
        # Use case-insensitive matching and extract lowercase names too
        name_intro_patterns = [
            r'\b(?:my\s+name\s+is|i\s+am|i\'m|im\s+|call\s+me|this\s+is)\s+([a-zA-Z][a-zA-Z0-9]*(?:\s+[a-zA-Z][a-zA-Z0-9]*)?)',
            r'\b([a-zA-Z][a-zA-Z0-9]*(?:\s+[a-zA-Z][a-zA-Z0-9]*)?)\s+(?:here|speaking|is\s+my\s+name)',
        ]
        for pattern in name_intro_patterns:
            for match in re.finditer(pattern, text, re.I):
                entity_text = match.group(1).strip()
                # Capitalize first letter of each word for proper formatting
                entity_text = ' '.join(word.capitalize() for word in entity_text.split())
                
                # Skip if it's a common word or too short
                if len(entity_text) < 2 or entity_text.lower() in self.entity_stopwords:
                    continue
                    
                if self._is_valid_entity(entity_text) and entity_text.lower() not in seen_entities:
                    entities.append(ExtractedEntity(
                        text=entity_text,
                        label="PROPER_NOUN",
                        start=match.start(1),
                        end=match.end(1),
                        confidence=0.8  # Higher confidence for explicit name introductions
                    ))
                    seen_entities.add(entity_text.lower())
        
        # Extract activity/skill words mentioned in context (like "code", "programming", etc.)
        # Look for patterns like "I like to X", "I enjoy X", "I do X"
        activity_patterns = [
            r'\b(?:i\s+(?:like|love|enjoy|do|practice)\s+(?:to\s+)?|i\s+(?:am|m)\s+(?:good\s+at|skilled\s+in|interested\s+in)\s+)([a-z]{3,})',
            r'\b(?:i\s+)?(code|coding|programming|developing|designing|writing|reading|drawing|painting|singing|dancing|playing|gaming)\b',
        ]
        activity_skills = {"code", "coding", "programming", "developing", "designing", "writing", "reading", 
                           "drawing", "painting", "singing", "dancing", "playing", "gaming", "photography",
                           "cooking", "baking", "sports", "running", "swimming", "cycling"}
        
        for pattern in activity_patterns:
            for match in re.finditer(pattern, text, re.I):
                activity_text = match.group(1 if match.lastindex else 0).strip().lower()
                if activity_text in activity_skills and activity_text not in seen_entities:
                    # Capitalize for display
                    activity_capitalized = activity_text.capitalize()
                    entities.append(ExtractedEntity(
                        text=activity_capitalized,
                        label="SKILL",  # Mark as SKILL since it's an activity/skill
                        start=match.start(1 if match.lastindex else 0),
                        end=match.end(1 if match.lastindex else 0),
                        confidence=0.7
                    ))
                    seen_entities.add(activity_text)
        
        # Emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append(ExtractedEntity(
                text=match.group(),
                label="EMAIL",
                start=match.start(),
                end=match.end(),
                confidence=1.0
            ))
        
        # Numbers/Dates
        number_pattern = r'\b\d+(?:\.\d+)?(?:\s*(?:years?|months?|days?|hours?|%|dollars?|rupees?))?\b'
        for match in re.finditer(number_pattern, text):
            entities.append(ExtractedEntity(
                text=match.group(),
                label="QUANTITY",
                start=match.start(),
                end=match.end(),
                confidence=0.8
            ))
        
        return entities

    def _normalize_entity_labels(self, entities: List[ExtractedEntity], text: str) -> List[ExtractedEntity]:
        """Heuristics to normalize and improve entity labels.
        - Mark known technologies as SKILL
        - Mark likely person names as PERSON when context suggests it
        """
        if not entities:
            return entities

        text_lower = text.lower()
        sentences = self._split_sentences(text)
        
        for e in entities:
            e_text = e.text.strip()
            e_lower = e_text.lower()

            # Known technology terms - mark as SKILL
            if e_lower in self.tech_terms or re.search(r'\b(' + '|'.join(re.escape(t) for t in self.tech_terms) + r')\b', e_lower):
                e.label = "SKILL"
                continue

            # Check if entity appears near name-indicating phrases
            # More flexible patterns: "I am X", "My name is X", "call me X", "I'm X", etc.
            # Use case-insensitive matching
            name_patterns = [
                r'\b(?:my\s+name\s+is|i\s+am|i\'m|im\s+|call\s+me|this\s+is)\s+' + re.escape(e_lower),
                re.escape(e_lower) + r'\s+(?:here|speaking|is\s+my\s+name)',
            ]
            
            # Check sentence context for person indicators
            for sent in sentences:
                sent_lower = sent.lower()
                # Check case-insensitively
                if e_text.lower() in sent_lower or e_text in sent:
                    # Check for name introduction patterns (case-insensitive)
                    if any(re.search(pattern, sent_lower) for pattern in name_patterns):
                        e.label = "PERSON"
                        break
                    
                    # Check for role/relationship words that suggest a person
                    if re.search(r'\b(colleague|manager|friend|engineer|developer|team|lead|person|someone|anyone)\b', sent_lower):
                        if len(e_text.split()) <= 3:
                            e.label = "PERSON"
                            break
                    
                    # If entity appears after "I" or "me" in a personal context
                    if re.search(r'\b(i|me|my)\s+[^.!?]{0,50}' + re.escape(e_lower), sent_lower):
                        if len(e_text.split()) <= 2 and e_lower not in self.tech_terms:
                            e.label = "PERSON"
                            break

            # Fallback: if entity appears after "my name is" or similar, mark as PERSON
            # This catches lowercase names that were capitalized during extraction
            if e.label in (None, "", "PROPER_NOUN"):
                # Check if it appears in name introduction context (case-insensitive)
                if re.search(r'\b(?:my\s+name\s+is|i\s+am|i\'m|im\s+|call\s+me)\s+' + re.escape(e_lower), text_lower):
                    e.label = "PERSON"
                elif len(e_text.split()) == 1 and e_lower not in self.tech_terms:
                    # Single word that's not a tech term - could be a name
                    # Check if it appears in personal context
                    if re.search(r'\b(i|me|my|hi|hello|hey)\s+[^.!?]{0,20}' + re.escape(e_lower), text_lower):
                        e.label = "PERSON"
                elif len(e_text.split()) == 2 and all(w[0].isupper() for w in e_text.split()):  # "John Smith" style
                    if e_lower not in self.tech_terms:
                        e.label = "PERSON"

        return entities

    def _classify_memory_items(
        self, 
        text: str, 
        user_id: str,
        message_id: str
    ) -> List[MemoryItemCreate]:
        """Classify and extract memory items from text"""
        memories = []
        text_lower = text.lower()
        sentences = self._split_sentences(text)
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check for compound sentences with "and", "also", ","
            # Split on conjunctions to extract multiple memories
            parts = re.split(r'\s+(and|also|,)\s+', sentence, flags=re.IGNORECASE)
            
            for part in parts:
                part = part.strip()
                if not part or len(part) < 3:
                    continue
                    
                part_lower = part.lower()
                memory_type = self._detect_memory_type(part_lower)
                
                if memory_type:
                    confidence = self._calculate_confidence(part_lower, memory_type)
                    
                    if confidence > 0.3:  # Minimum threshold
                        # Check if this is a name statement - give it high importance
                        is_name_statement = any(phrase in part_lower for phrase in [
                            "my name is", "i'm", "im ", "i am", "name is", "call me"
                        ])
                        
                        importance = self._calculate_importance(part_lower, memory_type)
                        if is_name_statement:
                            importance = min(1.0, importance + 0.3)  # Boost importance for names
                            confidence = min(1.0, confidence + 0.2)  # Boost confidence for names
                        
                        # Check for skills in the part
                        is_skill_statement = memory_type == "skill" or any(kw in part_lower for kw in [
                            "can", "know", "use", "good at", "expert", "programming", "coding"
                        ])
                        if is_skill_statement and memory_type != "skill":
                            # Re-check as skill might be more specific
                            if any(kw in part_lower for kw in self.skill_keywords):
                                memory_type = "skill"
                                confidence += 0.1
                        
                        # Check for preferences in the part
                        is_preference_statement = memory_type == "preference" or any(kw in part_lower for kw in [
                            "like", "love", "prefer", "enjoy", "favorite"
                        ])
                        if is_preference_statement and memory_type != "preference":
                            # Re-check as preference might be more specific
                            if any(kw in part_lower for kw in self.preference_keywords):
                                memory_type = "preference"
                                confidence += 0.1
                        
                        # Final clamp to ensure valid range
                        confidence = min(1.0, max(0.0, confidence))
                        importance = min(1.0, max(0.0, importance))

                        memories.append(MemoryItemCreate(
                            user_id=user_id,
                            memory_type=memory_type,
                            content=part.strip(),
                            confidence_score=confidence,
                            source_message_id=message_id,
                            importance_weight=importance
                        ))
        
        return memories
    
    def _detect_memory_type(self, text: str) -> Optional[str]:
        """Detect the type of memory from text patterns"""
        text_lower = text.lower()
        
        # Check for preferences first (most specific)
        # Look for preference patterns: "I like X", "I prefer X", "I love X"
        preference_patterns = [
            r'\bi\s+(like|love|enjoy|prefer|hate|dislike)\s+',
            r'\bi\s+(am|m)\s+(into|fond of|interested in)\s+',
            r'\bmy\s+(favorite|favourite)\s+',
            r'\bi\s+(want|wish|hope)\s+',
            r'\bi\s+(would\s+)?rather\s+'
        ]
        if any(re.search(pattern, text_lower) for pattern in preference_patterns):
            return "preference"
        if any(kw in text_lower for kw in self.preference_keywords):
            return "preference"
        
        # Check for skills (before facts, as skills are more specific)
        # Look for skill patterns: "I can X", "I know X", "I'm good at X", "I use X"
        skill_patterns = [
            r'\bi\s+(can|know|knows|use|uses|learn|learned)\s+',
            r'\bi\s+(am|m)\s+(good|great|expert|proficient|skilled|familiar)\s+(at|in|with)\s+',
            r'\bi\s+(have|has)\s+\d+\s+years?\s+(of\s+)?experience',
            r'\bi\s+(specialize|specialized|master|mastered)\s+(in|at)?\s*',
            r'\bi\s+(work|works)\s+with\s+',
            r'\bi\s+(am|m)\s+a\s+(developer|programmer|coder|engineer)',
            r'\b(programming|coding|developing)\s+in\s+',
            r'\busing\s+\w+',  # "using Python", "using React"
        ]
        if any(re.search(pattern, text_lower) for pattern in skill_patterns):
            return "skill"
        if any(kw in text_lower for kw in self.skill_keywords):
            return "skill"
        
        # Check for rules
        if any(kw in text_lower for kw in self.rule_keywords):
            return "rule"
        
        # Check for facts (broader category)
        if any(kw in text_lower for kw in self.fact_keywords):
            return "fact"
        
        # If contains named entities, likely a fact
        if re.search(r'\b[A-Z][a-z]+\b', text):
            return "fact"
        
        return None
    
    def _calculate_confidence(self, text: str, memory_type: str) -> float:
        """Calculate confidence score for memory extraction"""
        text_lower = text.lower()
        confidence = 0.5
        
        # Higher confidence for more explicit statements
        if any(phrase in text_lower for phrase in ["my ", "i am", "i'm", "im ", "i "]):
            confidence += 0.2
        
        # Increase for specific patterns based on memory type
        if memory_type == "preference":
            # Strong preference indicators
            if any(kw in text_lower for kw in ["favorite", "favourite", "love", "loves", "hate", "hates"]):
                confidence += 0.2
            elif any(kw in text_lower for kw in ["like", "prefer", "enjoy"]):
                confidence += 0.15
            # Pattern: "I like X" is very confident
            if re.search(r'\bi\s+(like|love|enjoy|prefer)\s+', text_lower):
                confidence += 0.15
        
        elif memory_type == "skill":
            # Strong skill indicators
            if any(kw in text_lower for kw in ["expert", "proficient", "years of experience", "experienced"]):
                confidence += 0.2
            elif any(kw in text_lower for kw in ["can", "know", "use", "good at", "familiar"]):
                confidence += 0.15
            # Pattern: "I can X", "I know X", "I use X" are confident
            if re.search(r'\bi\s+(can|know|use|knows|uses)\s+', text_lower):
                confidence += 0.15
            # Technology names increase confidence (Python, React, etc.)
            if re.search(r'\b(python|java|javascript|react|node|sql|mongodb|docker|kubernetes|aws|azure|gcp)\b', text_lower):
                confidence += 0.1
        
        elif memory_type == "fact":
            # Name statements are very confident
            if any(phrase in text_lower for phrase in ["my name is", "i'm", "im ", "i am", "name is"]):
                confidence += 0.25
        
        # Longer, more detailed statements get slightly higher confidence
        word_count = len(text.split())
        if word_count > 5:
            confidence += min(0.1, word_count * 0.01)
        
        return min(1.0, confidence)
    
    def _calculate_importance(self, text: str, memory_type: str) -> float:
        """Calculate importance weight for a memory"""
        text_lower = text.lower()
        importance = 0.5
        
        # Rules are generally important
        if memory_type == "rule":
            importance += 0.2
        
        # Strong preferences are important
        if any(kw in text_lower for kw in ["always", "never", "must", "hate", "hates", "love", "loves", "favorite", "favourite"]):
            importance += 0.15
        
        # Personal facts about the user (names, identity)
        if any(phrase in text_lower for phrase in ["my name", "i am", "i'm", "im ", "name is"]):
            importance += 0.3
        
        # Skills are important for context
        if memory_type == "skill":
            importance += 0.1
            # Technology skills are more important
            if re.search(r'\b(python|java|javascript|react|node|sql|mongodb|docker|kubernetes|aws|azure|gcp|typescript|vue|angular)\b', text_lower):
                importance += 0.1
        
        # Preferences are important for personalization
        if memory_type == "preference":
            importance += 0.1
            # Strong preferences are more important
            if any(kw in text_lower for kw in ["love", "loves", "hate", "hates", "favorite", "favourite"]):
                importance += 0.15
        
        return min(1.0, importance)
    
    def _extract_relations(
        self,
        entities: List[ExtractedEntity],
        user_id: str,
        message_id: str,
        text: str
    ) -> List[EntityRelationCreate]:
        """Extract relations between entities using sentence-level, label-aware heuristics."""
        relations: List[EntityRelationCreate] = []
        if len(entities) < 2:
            return relations

        # Track global PERSON and SKILL entities so we can add
        # sensible cross-sentence fallbacks (e.g. Ram <-> Python)
        person_entities: List[ExtractedEntity] = []
        skill_entities: List[ExtractedEntity] = []
        person_skill_links_added = False

        for e in entities:
            if e.label == "PERSON":
                person_entities.append(e)
            elif e.label == "SKILL":
                skill_entities.append(e)

        # Build sentence spans (with offsets) using regex so we can map entities to sentences
        sentence_spans = []
        for m in re.finditer(r'[^.!?]+[.!?]*', text):
            sent = m.group().strip()
            if sent:
                sentence_spans.append((sent, m.start(), m.end()))

        for sent, s_start, s_end in sentence_spans:
            # Entities inside this sentence
            sent_entities = [e for e in entities if e.start >= s_start and e.end <= s_end]
            if len(sent_entities) < 2:
                continue

            sent_type = self._detect_memory_type(sent)

            for i, e1 in enumerate(sent_entities):
                for e2 in sent_entities[i+1:]:
                    # Basic filters
                    if not self._is_valid_entity(e1.text) or not self._is_valid_entity(e2.text):
                        continue
                    if e1.text.lower() == e2.text.lower():
                        continue
                    if e1.label in ("QUANTITY", "EMAIL") or e2.label in ("QUANTITY", "EMAIL"):
                        # Avoid relating to quantities or emails
                        continue

                    # PERSON <-> SKILL (more permissive - if they appear together, create relation)
                    if (e1.label == "PERSON" and e2.label == "SKILL") or (e1.label == "SKILL" and e2.label == "PERSON"):
                        # More permissive: create relation if:
                        # 1. Sentence is skill-related, OR
                        # 2. Contains skill verbs, OR
                        # 3. Just co-occur in same sentence (they're likely related)
                        if (sent_type == "skill" or 
                            re.search(r'\b(use|uses|using|proficient|expert|work|works|familiar|know|knows|learn|learned|good\s+at|skilled|can)\b', sent, re.I) or
                            True):  # Always create if PERSON and SKILL in same sentence
                            relations.append(EntityRelationCreate(
                                user_id=user_id,
                                entity_1=e1.text,
                                entity_2=e2.text,
                                relation_type="associated_with",
                                confidence_score=0.85 if sent_type == "skill" else 0.7,
                                source_message_id=message_id
                            ))
                            logger.debug(f"[NLP][REL] PERSON<->SKILL relation added: {e1.text} - associated_with - {e2.text}")
                            person_skill_links_added = True
                            continue

                    # SKILL <-> SKILL (co-occurrence in skill context)
                    if e1.label == "SKILL" and e2.label == "SKILL":
                        relations.append(EntityRelationCreate(
                            user_id=user_id,
                            entity_1=e1.text,
                            entity_2=e2.text,
                            relation_type="associated_with",
                            confidence_score=0.8,
                            source_message_id=message_id
                        ))
                        logger.debug(f"[NLP][REL] SKILL<->SKILL relation added: {e1.text} - associated_with - {e2.text}")
                        continue

                    # Fallback: sentence-level co-occurrence with lower confidence
                    sent_len = max(1, s_end - s_start)
                    distance = abs(e2.start - e1.end)
                    confidence = max(0.3, 1 - (distance / sent_len))
                    relations.append(EntityRelationCreate(
                        user_id=user_id,
                        entity_1=e1.text,
                        entity_2=e2.text,
                        relation_type="associated_with",
                        confidence_score=confidence,
                        source_message_id=message_id
                    ))

        # Cross-sentence fallback: ALWAYS connect PERSON entities to SKILL entities
        # if they appear in the same message, regardless of sentence boundaries.
        # This is more permissive and works for natural language variations.
        # We create these links even if some sentence-level links were already created,
        # but we'll deduplicate based on entity pairs later.
        if person_entities and skill_entities:
            # Track existing relations to avoid duplicates
            existing_pairs = set()
            for rel in relations:
                pair = tuple(sorted([rel.entity_1.lower(), rel.entity_2.lower()]))
                existing_pairs.add(pair)
            
            for p in person_entities:
                for s in skill_entities:
                    if p.text.lower() == s.text.lower():
                        continue
                    # Check if this relation already exists
                    pair = tuple(sorted([p.text.lower(), s.text.lower()]))
                    if pair in existing_pairs:
                        continue
                    
                    # Determine confidence based on context
                    confidence = 0.6
                    # Higher confidence if message contains skill-related verbs
                    if re.search(r'\b(use|uses|using|work|works|know|knows|learn|learned|good\s+at|expert|proficient)\b', text, re.I):
                        confidence = 0.75
                    # Even higher if name appears near "I" or personal pronouns
                    if re.search(r'\b(i|my|me)\s+[^.!?]{0,50}' + re.escape(p.text), text, re.I):
                        confidence = 0.8
                    
                    relations.append(EntityRelationCreate(
                        user_id=user_id,
                        entity_1=p.text,
                        entity_2=s.text,
                        relation_type="associated_with",
                        confidence_score=confidence,
                        source_message_id=message_id
                    ))
                    logger.debug(f"[NLP][REL] CROSS-SENTENCE PERSON<->SKILL: {p.text} - associated_with - {s.text} (conf={confidence})")

        return relations
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        if self.nlp:
            doc = self.nlp(text)
            # Get nouns and proper nouns
            keywords = [
                token.text.lower() for token in doc 
                if token.pos_ in ("NOUN", "PROPN") and len(token.text) > 2
            ]
            return list(set(keywords))[:10]  # Deduplicate and limit
        else:
            # Basic extraction
            words = text.lower().split()
            # Filter common words
            stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been", 
                        "have", "has", "had", "do", "does", "did", "will", "would",
                        "could", "should", "may", "might", "can", "to", "of", "in",
                        "for", "on", "with", "at", "by", "from", "as", "it", "that",
                        "this", "but", "and", "or", "if", "i", "you", "he", "she",
                        "they", "we", "my", "your", "his", "her", "their", "our"}
            
            keywords = [w for w in words if w not in stopwords and len(w) > 2]
            return list(set(keywords))[:10]
    
    def _detect_intents(self, text: str) -> List[str]:
        """Detect user intents from text"""
        intents = []
        text_lower = text.lower()
        
        # Question intent
        if "?" in text or text_lower.startswith(("what", "where", "when", "why", "how", "who", "which")):
            intents.append("question")
        
        # Request intent
        if any(kw in text_lower for kw in ["please", "can you", "could you", "help me", "i need"]):
            intents.append("request")
        
        # Information sharing
        if any(kw in text_lower for kw in ["i am", "my name", "i have", "i work", "i live"]):
            intents.append("inform")
        
        # Preference sharing
        if any(kw in text_lower for kw in ["i like", "i prefer", "i love", "i hate"]):
            intents.append("preference_share")
        
        # Command
        if text_lower.startswith(("show", "list", "get", "find", "search", "create", "delete")):
            intents.append("command")
        
        if not intents:
            intents.append("general")
        
        return intents
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        if self.nlp:
            doc = self.nlp(text)
            return [sent.text for sent in doc.sents]
        else:
            # Basic sentence splitting
            sentences = re.split(r'[.!?]+', text)
            return [s.strip() for s in sentences if s.strip()]


# Singleton instance
nlp_service = NLPService()


def get_nlp_service() -> NLPService:
    return nlp_service

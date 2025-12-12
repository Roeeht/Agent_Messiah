"""
Redis client for session management and caching.
Used to store conversation state during active voice calls.
"""

import redis
import json
from typing import Optional, Dict, Any
from app.config import config

# Initialize Redis client
try:
    redis_client = redis.from_url(
        config.REDIS_URL,
        decode_responses=True,  # Automatically decode bytes to strings
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test connection
    redis_client.ping()
    REDIS_AVAILABLE = True
except (redis.ConnectionError, redis.TimeoutError):
    redis_client = None
    REDIS_AVAILABLE = False


class SessionManager:
    """
    Manages conversation sessions in Redis.
    Each voice call gets a session keyed by call_sid.
    """
    
    SESSION_PREFIX = "call_session:"
    
    @classmethod
    def get_session(cls, call_sid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data for a call.
        
        Args:
            call_sid: Twilio Call SID
            
        Returns:
            Session data dict or None if not found
        """
        if not REDIS_AVAILABLE:
            return None
        
        key = f"{cls.SESSION_PREFIX}{call_sid}"
        data = redis_client.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    @classmethod
    def save_session(cls, call_sid: str, session_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Save session data for a call.
        
        Args:
            call_sid: Twilio Call SID
            session_data: Dictionary of session data
            ttl: Time to live in seconds (default: config.REDIS_SESSION_TTL)
            
        Returns:
            True if saved successfully
        """
        if not REDIS_AVAILABLE:
            return False
        
        key = f"{cls.SESSION_PREFIX}{call_sid}"
        ttl = ttl or config.REDIS_SESSION_TTL
        
        try:
            redis_client.setex(
                key,
                ttl,
                json.dumps(session_data)
            )
            return True
        except redis.RedisError:
            return False
    
    @classmethod
    def update_session(cls, call_sid: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific fields in a session.
        
        Args:
            call_sid: Twilio Call SID
            updates: Dictionary of fields to update
            
        Returns:
            True if updated successfully
        """
        session = cls.get_session(call_sid)
        if session is None:
            return False
        
        session.update(updates)
        return cls.save_session(call_sid, session)
    
    @classmethod
    def delete_session(cls, call_sid: str) -> bool:
        """
        Delete a session (e.g., after call ends).
        
        Args:
            call_sid: Twilio Call SID
            
        Returns:
            True if deleted successfully
        """
        if not REDIS_AVAILABLE:
            return False
        
        key = f"{cls.SESSION_PREFIX}{call_sid}"
        try:
            redis_client.delete(key)
            return True
        except redis.RedisError:
            return False
    
    @classmethod
    def add_conversation_turn(cls, call_sid: str, role: str, message: str) -> bool:
        """
        Add a conversation turn to the session history.
        
        Args:
            call_sid: Twilio Call SID
            role: "user" or "assistant"
            message: The message content
            
        Returns:
            True if added successfully
        """
        session = cls.get_session(call_sid)
        if session is None:
            # Create new session
            session = {
                "conversation_history": [],
                "lead_id": None,
                "call_start": None
            }
        
        if "conversation_history" not in session:
            session["conversation_history"] = []
        
        session["conversation_history"].append({
            "role": role,
            "content": message
        })
        
        return cls.save_session(call_sid, session)


class CacheManager:
    """
    General purpose caching using Redis.
    """
    
    CACHE_PREFIX = "cache:"
    
    @classmethod
    def get(cls, key: str) -> Optional[str]:
        """Get value from cache."""
        if not REDIS_AVAILABLE:
            return None
        
        cache_key = f"{cls.CACHE_PREFIX}{key}"
        return redis_client.get(cache_key)
    
    @classmethod
    def set(cls, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""
        if not REDIS_AVAILABLE:
            return False
        
        cache_key = f"{cls.CACHE_PREFIX}{key}"
        try:
            redis_client.setex(cache_key, ttl, value)
            return True
        except redis.RedisError:
            return False
    
    @classmethod
    def delete(cls, key: str) -> bool:
        """Delete value from cache."""
        if not REDIS_AVAILABLE:
            return False
        
        cache_key = f"{cls.CACHE_PREFIX}{key}"
        try:
            redis_client.delete(cache_key)
            return True
        except redis.RedisError:
            return False

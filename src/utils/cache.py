from typing import Dict, Optional
import time
from collections import OrderedDict

class LRUCache:
    """Simple LRU (Least Recently Used) cache."""
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of items in cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
    
    def get(self, key: str) -> Optional[any]:
        """Get item from cache if it exists and hasn't expired."""
        if key not in self.cache:
            return None
        
        # Check if expired
        if time.time() - self.timestamps[key] > self.ttl:
            del self.cache[key]
            del self.timestamps[key]
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def set(self, key: str, value: any) -> None:
        """Add or update item in cache."""
        if key in self.cache:
            # Update existing
            self.cache.move_to_end(key)
        else:
            # Add new
            if len(self.cache) >= self.max_size:
                # Remove oldest
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all items from cache."""
        self.cache.clear()
        self.timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)

# Global cache instance
_path_cache = LRUCache(max_size=200, ttl=1800)  # 30 minutes TTL

def get_cached_folder_listing(path: str):
    """Get folder listing from cache if available."""
    return _path_cache.get(path)

def cache_folder_listing(path: str, listing: dict) -> None:
    """Cache folder listing."""
    _path_cache.set(path, listing)

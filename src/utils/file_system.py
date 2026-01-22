"""
File system utility functions.
"""

import os
import string
from typing import List, Dict, Any
from pathlib import Path

from src.config.settings import SYSTEM_CONFIG, AGENT_CONFIG
from src.utils.cache import get_cached_folder_listing, cache_folder_listing

def get_available_partitions() -> List[str]:
    """Get list of available disk partitions (drives)."""
    partitions = []
    for drive in string.ascii_uppercase:
        drive_path = f"{drive}:\\"
        if os.path.exists(drive_path):
            partitions.append(drive_path)
    return partitions

def list_folder_items(path: str, max_items: int = None, use_cache: bool = True) -> Dict[str, Any]:
    """
    List all folders and important files in a directory.
    Returns structured data for the model to analyze.
    
    Args:
        path: Path to list
        max_items: Maximum items to return
        use_cache: Whether to use cache
        
    Returns:
        Dictionary with folders, executables, and other files
    """
    if max_items is None:
        max_items = AGENT_CONFIG["max_items_per_folder"]
    
    if not os.path.exists(path):
        return {"error": f"Path does not exist: {path}"}
    
    # Check cache first
    if use_cache:
        cached = get_cached_folder_listing(path)
        if cached:
            return cached
    
    try:
        folders = []
        executables = []
        other_files = []
        
        setup_keywords = SYSTEM_CONFIG["setup_keywords"]
        executable_exts = SYSTEM_CONFIG["executable_extensions"]
        other_exts = SYSTEM_CONFIG["other_file_extensions"]
        skip_folders = SYSTEM_CONFIG["skip_folders"]
        
        items_found = 0
        items_skipped = 0
        
        for item in os.listdir(path):
            items_found += 1
            item_path = os.path.join(path, item)
            full_path = os.path.abspath(item_path)
            item_lower = item.lower()
            
            # Skip system/hidden items
            if any(skip in item_lower for skip in skip_folders) or item.startswith('.'):
                items_skipped += 1
                continue
            
            try:
                if os.path.isdir(item_path):
                    folders.append({
                        "name": item,
                        "path": full_path
                    })
                elif os.path.isfile(item_path):
                    ext = os.path.splitext(item)[1].lower()
                    if ext in executable_exts:
                        is_setup = any(kw in item_lower for kw in setup_keywords)
                        if not is_setup:
                            executables.append({
                                "name": item,
                                "path": full_path
                            })
                    elif ext in other_exts:
                        other_files.append({
                            "name": item,
                            "path": full_path
                        })
            except (PermissionError, OSError) as e:
                items_skipped += 1
                continue
        
        # Log if we found items but they were all skipped
        if items_found > 0 and len(folders) == 0 and len(executables) == 0:
            import logging
            logger = logging.getLogger("FileSystemAgent")
            logger.debug(f"Found {items_found} items in {path}, but {items_skipped} were skipped")
        
        result = {
            "folders": folders[:max_items],
            "executables": executables[:max_items],
            "other_files": other_files[:max_items],
            "total_folders": len(folders),
            "total_executables": len(executables),
            "path": path
        }
        
        # Cache the result
        if use_cache and "error" not in result:
            cache_folder_listing(path, result)
        
        return result
    except PermissionError:
        return {"error": f"Access denied: {path}"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

def format_folder_listing(data: Dict[str, Any]) -> str:
    """Format folder listing data into readable text for the model."""
    if "error" in data:
        return f"❌ {data['error']}"
    
    parts = []
    
    if data.get("folders"):
        parts.append("📁 FOLDERS:")
        for folder in data["folders"]:
            parts.append(f"  - {folder['name']} -> {folder['path']}")
    
    if data.get("executables"):
        parts.append("\n📄 EXECUTABLES:")
        for exe in data["executables"]:
            parts.append(f"  - {exe['name']} -> {exe['path']}")
    
    if data.get("other_files"):
        parts.append("\n📄 OTHER FILES:")
        for file in data["other_files"][:10]:  # Limit other files
            parts.append(f"  - {file['name']} -> {file['path']}")
    
    if not parts:
        return "📂 Folder is empty or contains no accessible items."
    
    summary = f"Total: {data.get('total_folders', 0)} folders, {data.get('total_executables', 0)} executables"
    return "\n".join(parts) + f"\n\n{summary}"

def extract_keywords(query: str) -> List[str]:
    """Extract meaningful keywords from query, removing common verbs and stop words."""
    stop_words = {
        'open', 'find', 'launch', 'search', 'locate', 'get', 'show', 'run', 'start',
        'the', 'a', 'an', 'in', 'on', 'at', 'for', 'to', 'of', 'and', 'or', 'but',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might'
    }
    words = [w.lower().strip() for w in query.split() 
             if w.lower().strip() not in stop_words and len(w.strip()) > 1]
    # If all words were filtered, return the original query (split)
    return words if words else [w.lower() for w in query.split() if len(w.strip()) > 0]

def open_path(path: str) -> bool:
    """Open a file or folder using the system default application."""
    import sys
    import subprocess
    
    if not os.path.exists(path):
        return False
    
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
        return True
    except Exception:
        return False

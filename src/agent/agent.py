import os
import json
import re
import logging
from typing import List, Dict, Any, Optional

from ..config.settings import AGENT_CONFIG, validate_config, LLM_PROVIDER
from ..utils.file_system import (
    get_available_partitions,
    list_folder_items,
    format_folder_listing,
    extract_keywords,
    open_path
)
from src.utils.google_search import check_and_open_search

logger = logging.getLogger("FileSystemAgent")


class SmartFileSystemAgent:
    """Intelligent file system navigator using Ollama or Gemini."""
    
    def __init__(self):
        """Initialize the agent with selected LLM provider."""
        # Validate configuration
        validate_config()
        
        # Initialize LLM client based on provider
        if LLM_PROVIDER == "ollama":
            from ..utils.ollama_client import OllamaClient
            from ..config.settings import OLLAMA_CONFIG
            self.llm = OllamaClient()
            logger.info(f"✅ Using Ollama: {OLLAMA_CONFIG['model_name']}")
        elif LLM_PROVIDER == "gemini":
            from ..utils.gemini_client import GeminiClient
            from ..config.settings import GEMINI_MODELS
            self.llm = GeminiClient()
            logger.info(f"✅ Using Gemini: {GEMINI_MODELS[0] if GEMINI_MODELS else 'default'}")
        else:
            raise ValueError(f"Invalid LLM_PROVIDER: {LLM_PROVIDER}")
        
        # Initialize components
        self.partitions = get_available_partitions()
        self.max_depth = AGENT_CONFIG["max_depth"]
        self.skip_c_drive = AGENT_CONFIG["skip_c_drive_initially"]
        
        logger.info(f"✅ Agent initialized with {len(self.partitions)} partitions: {', '.join(self.partitions)}")
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the model."""
        partitions_str = ", ".join(self.partitions)
        
        return f"""You are an intelligent file system navigator. Your job is to help users find and open files/folders on their Windows PC.

AVAILABLE PARTITIONS: {partitions_str}

YOUR WORKFLOW:
1. When the user asks for something, I will show you the contents of a folder
2. Analyze the folder listing CAREFULLY and find the EXACT match for the user's query
3. Respond with ONLY a JSON object in this exact format:
   {{"action": "explore", "path": "full_path_to_folder"}}
   OR
   {{"action": "open", "path": "full_path_to_file_or_folder"}}
   OR
   {{"action": "not_found", "reason": "explanation"}}

CRITICAL RULES:
- MATCH THE QUERY: Look for folders/files that contain keywords from the user's query
- Be SMART: Match partial words, handle common variations, and be flexible with spelling
- DO NOT choose folders that don't contain any keywords from the query
- SMART FOLDER DETECTION: If a folder contains multiple items (files/folders) that match the query, that folder itself is likely the target - open it directly
- If you see a folder that might contain what the user wants, choose "explore" with that folder's path
- If you find the exact file/folder the user wants, choose "open" with its path
- If the current folder has matching items, consider opening the current folder itself
- If nothing matches after reasonable exploration, choose "not_found"
- Prefer folders over setup/install files (unless user explicitly asks for setup)
- Always use full absolute paths with DOUBLE backslashes (e.g., "D:\\\\Program Files\\\\Application")
- IMPORTANT: Escape backslashes in paths - use \\\\ instead of \\ in JSON strings
- USE ONLY PATHS FROM THE LISTING: Copy the EXACT path shown after "->" in the folder listing, don't create new paths
- Be flexible with spelling mistakes and variations in the query

IMPORTANT: Respond ONLY with valid JSON, no other text."""
    
    def _parse_model_response(self, response: str) -> Dict[str, Any]:
        """Parse the model's JSON response."""
        if not response:
            return {"action": "error", "reason": "Empty response"}
        
        try:
            # Extract JSON from response (might have markdown code blocks)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # Fix Windows paths with backslashes before JSON parsing
            # JSON requires backslashes to be escaped, but the model returns them unescaped
            # Pattern: "path": "D:\Riot Games" -> "path": "D:\\Riot Games"
            import re
            
            # More robust approach: Find all Windows paths in quoted strings and escape backslashes
            # Also handle forward slashes and convert them to backslashes
            def escape_backslashes_in_paths(text):
                # First, try to find all quoted strings that might contain paths
                # Pattern 1: "path": "E:\c# projects\..." (with backslashes)
                # Pattern 2: "path": "E:/c# projects/..." (with forward slashes)
                # Pattern 3: Any string containing drive letters
                
                # Find all quoted strings that contain Windows paths
                # This regex is more permissive and handles paths with special characters
                pattern = r'("path"\s*:\s*")([^"]*?)([A-Z]:[/\\][^"]*?)(")'
                
                def escape_path(match):
                    key_part = match.group(1)  # "path": "
                    prefix = match.group(2)  # Any text before the path
                    path_value = match.group(3)  # The path value
                    suffix = match.group(4)  # Any text after (should be closing quote)
                    
                    # Combine prefix and path
                    full_value = prefix + path_value
                    
                    # Check if it's a Windows path (contains drive letter)
                    if re.search(r'[A-Z]:[/\\]', full_value, re.IGNORECASE):
                        # Convert forward slashes to backslashes first
                        full_value = full_value.replace('/', '\\')
                        # Then escape all backslashes for JSON (but be careful with already escaped ones)
                        # Replace \ with \\, but avoid double-escaping
                        full_value = re.sub(r'\\(?!\\)', r'\\\\', full_value)
                        # Fix any double backslashes that should be single escaped
                        full_value = full_value.replace('\\\\\\\\', '\\\\')
                    
                    return key_part + full_value + suffix
                
                result = re.sub(pattern, escape_path, text, flags=re.IGNORECASE)
                
                # Also handle simpler case: any string value containing backslashes after "path":
                # This catches cases where the regex above might miss
                simple_pattern = r'("path"\s*:\s*")([^"]*[A-Z]:\\[^"]*?)(")'
                
                def simple_escape(match):
                    key = match.group(1)
                    value = match.group(2)
                    quote = match.group(3)
                    # Escape backslashes
                    value = value.replace('\\', '\\\\')
                    return key + value + quote
                
                result = re.sub(simple_pattern, simple_escape, result, flags=re.IGNORECASE)
                
                return result
            
            response = escape_backslashes_in_paths(response)
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Failed to parse JSON: {e}\nResponse: {response[:200]}")
            
            # Try to extract path manually even if JSON parsing fails
            # First, try to find the original response before our fixes
            original_response = response
            
            # Try multiple patterns to extract path and action
            patterns = [
                (r'"path"\s*:\s*"([^"]+)"', r'"action"\s*:\s*"([^"]+)"'),
                (r'"path"\s*:\s*"([^"]*[A-Z]:\\[^"]*)"', r'"action"\s*:\s*"([^"]+)"'),
                (r'path["\']?\s*:\s*["\']([^"\']+[A-Z]:\\[^"\']+)["\']', r'action["\']?\s*:\s*["\']([^"\']+)["\']'),
            ]
            
            for path_pattern, action_pattern in patterns:
                path_match = re.search(path_pattern, original_response, re.IGNORECASE)
                action_match = re.search(action_pattern, original_response, re.IGNORECASE)
                
                if path_match and action_match:
                    path = path_match.group(1)
                    action = action_match.group(1)
                    # Normalize backslashes (remove extra escaping)
                    path = path.replace('\\\\', '\\').replace('\\', '\\')
                    logger.info(f"📋 Extracted from failed JSON: action={action}, path={path}")
                    return {"action": action, "path": path}
            
            # If we still can't parse, try to extract just the path (handle both backslashes and forward slashes)
            # But be more careful - don't extract partial paths
            path_patterns = [
                r'[A-Z]:\\[^\s"\'<>\)]+',  # Backslashes - stop at closing parens too
                r'[A-Z]:/[^\s"\'<>\)]+',  # Forward slashes
            ]
            
            for pattern in path_patterns:
                path_matches = re.findall(pattern, original_response, re.IGNORECASE)
                # Prefer longer paths (more complete)
                if path_matches:
                    path_matches = sorted(set(path_matches), key=len, reverse=True)
                    for path in path_matches:
                        path = path.strip().rstrip('.,;:)')
                        # Convert forward slashes to backslashes
                        path = path.replace('/', '\\')
                        # Validate - must be a reasonable path length and exist
                        if len(path) > 3 and os.path.exists(path):
                            logger.info(f"📋 Extracted valid path: {path}")
                            return {"action": "open", "path": path}
                        # If path doesn't exist, try parent directory
                        elif len(path) > 3:
                            parent = os.path.dirname(path)
                            if os.path.exists(parent) and len(parent) > 3:
                                logger.info(f"📋 Extracted path, using parent: {parent}")
                                return {"action": "open", "path": parent}
            
            return {"action": "error", "reason": f"Invalid JSON: {str(e)}"}
    
    def _explore_partition(self, partition: str, user_query: str) -> Optional[str]:
        """Explore a partition to find the user's requested item."""
        logger.info(f"🔍 Exploring partition: {partition}")
        
        # Get folder listing
        listing_data = list_folder_items(partition)
        if "error" in listing_data:
            logger.error(f"Error listing partition: {listing_data['error']}")
            return None
        
        # Quick pre-check: find best matching folder before asking AI
        query_lower = user_query.lower()
        query_words = extract_keywords(user_query)
        folders = listing_data.get("folders", [])
        executables = listing_data.get("executables", [])
        
        # SMART CHECK: If partition contains matching items, check if we should open partition or explore folders
        query_variations = set(query_words)
        matching_executables = [e for e in executables if any(word in e["name"].lower() for word in query_variations)]
        matching_folders = [f for f in folders if any(word in f["name"].lower() for word in query_variations)]
        matching_items_count = len(matching_executables) + len(matching_folders)
        
        # If partition has matching folders, prefer exploring them over opening partition
        # Only open partition if:
        # 1. No matching folders found (only executables)
        # 2. OR user explicitly asked for partition/drive
        if matching_items_count >= 2:
            # Check if user asked for partition/drive explicitly
            query_lower = user_query.lower()
            partition_keywords = ["drive", "partition", "disk", "volume"]
            user_wants_partition = any(kw in query_lower for kw in partition_keywords) or any(
                f"{p[0]}:" in query_lower for p in [partition] if partition
            )
            
            # If we have matching folders, explore them instead of opening partition
            if matching_folders and not user_wants_partition:
                # If there's a clear best match folder, use it
                if len(matching_folders) == 1:
                    logger.info(f"✅ Found single matching folder: {matching_folders[0]['name']}")
                    return matching_folders[0]["path"]
                # Otherwise, let the model decide which folder to explore
                logger.info(f"✅ Partition contains {len(matching_folders)} matching folders - letting model decide")
            elif not matching_folders and matching_executables and not user_wants_partition:
                # Only executables found, but user didn't ask for partition - continue to model decision
                logger.info(
                    f"✅ Partition contains {len(matching_executables)} matching executables - letting model decide")
            else:
                # User wants partition or no clear folder match
                logger.info(
                    f"✅ Partition contains {matching_items_count} matching items - opening partition: {partition}")
                return partition
        
        # Score folders by keyword match - prioritize exact/simple matches
        scored_folders = []
        # Filter out common/weak words that don't help distinguish
        weak_words = {"the", "my", "open", "find", "launch", "games", "game", "app", "application", "program",
                      "software", "folder", "folders"}
        important_words = [w for w in query_words if w not in weak_words and len(w) > 2]
        
        # Define synonyms for better matching
        synonyms_map = {
            "cv": ["resume", "resumes", "curriculum", "vitae"],
            "resume": ["cv", "curriculum", "vitae"],
            "certificate": ["cert", "certs", "certificates"],
            "cert": ["certificate", "certificates", "certs"],
            "document": ["doc", "docs", "documents"],
            "photo": ["picture", "pictures", "image", "images"],
            "movie": ["film", "films", "video", "videos"],
            "music": ["song", "songs", "audio", "tracks"],
        }
        
        # Expand important words with synonyms
        expanded_important_words = set(important_words)
        for word in important_words:
            word_lower = word.lower()
            if word_lower in synonyms_map:
                expanded_important_words.update(synonyms_map[word_lower])
        
        # Build query phrase (without weak words) for exact matching
        query_phrase = " ".join(important_words).lower()
        
        for folder in folders:
            folder_name_lower = folder["name"].lower()
            # Calculate score: important words count more
            score = 0
            # Check direct matches
            important_matches = sum(1 for word in important_words if word in folder_name_lower)
            # Check synonym matches
            synonym_matches = sum(
                1 for word in expanded_important_words if word in folder_name_lower and word not in important_words)
            weak_matches = sum(1 for word in query_words if word in folder_name_lower and word in weak_words)
            
            # Prioritize important word matches (synonyms get bonus too)
            score = (important_matches * 3) + (synonym_matches * 2) + weak_matches
            
            # BONUS: Exact or near-exact match gets huge boost
            # If folder name is exactly the query phrase (or very close), prioritize it
            exact_match = False
            if query_phrase and query_phrase in folder_name_lower:
                # Check if folder name is close to query phrase
                if folder_name_lower == query_phrase or folder_name_lower.startswith(
                        query_phrase) or folder_name_lower.endswith(query_phrase):
                    exact_match = True
                    score += 10  # Big bonus for exact/simple match
            
            # Also check if folder name matches any synonym
            for word in expanded_important_words:
                if word in folder_name_lower:
                    # Check if it's a synonym match (not direct)
                    if word not in important_words:
                        score += 5  # Bonus for synonym match
                        if word in folder_name_lower.split() or any(
                                part == word for part in folder_name_lower.split("-") + folder_name_lower.split("_")):
                            exact_match = True
                            score += 5  # Extra bonus for exact synonym match
            
            # Also check if folder name is simpler/shorter (prefer "projects" over "data science projects")
            is_simple = len(folder_name_lower.split()) <= len(important_words) + 1
            if is_simple and important_matches > 0:
                score += 5  # Bonus for simpler names
            
            if score > 0:
                scored_folders.append((score, important_matches, exact_match, is_simple, folder))
        
        # If we have a clear winner (high score with important matches), use it directly
        if scored_folders:
            # Sort by: exact match first, then score, then important matches, then simplicity
            scored_folders.sort(key=lambda x: (x[2], x[0], x[1], x[3]), reverse=True)
            best_score, best_important, best_exact, best_simple, best_folder = scored_folders[0]
            
            # Only use quick match if:
            # 1. Has important word matches (not just weak words)
            # 2. Score is high enough (>= 3) OR exact match OR significantly better than others
            if best_important > 0 and (best_exact or best_score >= 3 or (len(scored_folders) == 1) or (
                    len(scored_folders) > 1 and best_score > scored_folders[1][0] * 2)):
                logger.info(
                    f"📋 Quick match found: {best_folder['name']} (score: {best_score}, important: {best_important}, exact: {best_exact})")
                return best_folder["path"]
        
        formatted_listing = format_folder_listing(listing_data)
        
        # Build prompt for model
        system_context = self._get_system_prompt()
        prompt = f"""{system_context}

User Query: "{user_query}"

Current Location: {partition}

Folder Contents:
{formatted_listing}

Analyze the folders above CAREFULLY. Which folder do you think contains what the user is looking for?

SMART DECISION RULES:
1. If the CURRENT PARTITION (Current Location: {partition}) contains multiple items (files/folders) that match the user's query,
   the partition itself is likely the target - choose "open" with the partition path: "{partition}"
2. Match the MAIN keywords from the user's query to folder names
3. Look for folders that contain keywords from the query (e.g., if query has "davinci" and "resolve", look for folders with those words)
4. DO NOT choose folders that don't contain any keywords from the query
5. Prioritize folders that match MORE keywords from the query
6. If you see a folder that matches, explore it. If you see the exact item, open it.
7. USE ONLY PATHS FROM THE LISTING ABOVE - copy the path exactly as shown after "->"
8. Be precise: only choose folders that actually match the query keywords
9. IMPORTANT: If the current partition has matching items, prefer opening the partition over exploring subfolders
10. If the user didn't mention setup and the folder you found contains a setup file, continue scanning to find the exact item the user is looking for
11. Only return the setup if the user asked for it or there is nothing else"""
        
        # Get model decision
        response_text = self.llm.generate_content(prompt)
        if not response_text:
            return None
        
        decision = self._parse_model_response(response_text)
        
        logger.info(f"🤖 Model decision: {decision.get('action')} - {decision.get('path', 'N/A')}")
        
        # If model chose to open the partition itself, return it
        if decision.get("action") == "open":
            path = decision.get("path")
            if path:
                # Normalize paths for comparison
                normalized_partition = os.path.normpath(partition).lower()
                normalized_path = os.path.normpath(path).lower()
                if normalized_partition == normalized_path:
                    logger.info(f"✅ Model chose to open partition: {partition}")
                    return partition
        
        if decision.get("action") == "explore":
            path = decision.get("path")
            if path:
                # Normalize path (convert forward slashes, fix backslashes)
                path = path.replace('/', '\\').replace('\\\\', '\\')
                if os.path.exists(path):
                    return path
                else:
                    logger.warning(f"⚠️ Path from model doesn't exist: {path}")
        elif decision.get("action") == "open":
            path = decision.get("path")
            if path:
                # Normalize path
                path = path.replace('/', '\\').replace('\\\\', '\\')
                if os.path.exists(path):
                    return path
                else:
                    logger.warning(f"⚠️ Path from model doesn't exist: {path}")
        elif decision.get("action") == "not_found":
            return None
        
        # Fallback: try to extract path from response (handle both slash types)
        path_patterns = [
            r'([A-Z]:\\[^\s"\'<>\)]+)',  # Backslashes
            r'([A-Z]:/[^\s"\'<>\)]+)',  # Forward slashes
        ]
        
        all_paths = []
        for pattern in path_patterns:
            path_matches = re.findall(pattern, response_text, re.IGNORECASE)
            all_paths.extend(path_matches)
        
        # Sort by length (prefer longer, more complete paths)
        all_paths = sorted(set(all_paths), key=len, reverse=True)
        
        for potential_path in all_paths:
            potential_path = potential_path.strip().rstrip('.,;:)')
            # Normalize path
            potential_path = potential_path.replace('/', '\\')
            # Validate path exists and is reasonable (not just a drive letter)
            if len(potential_path) > 3 and os.path.exists(potential_path):
                return potential_path
        
        return None
    
    def _navigate_to_target(self, start_path: str, user_query: str, depth: int = 0,
                            visited_paths: Optional[set] = None) -> Optional[str]:
        """Recursively navigate through folders to find the target."""
        if depth >= self.max_depth:
            logger.warning(f"⚠️ Maximum depth reached: {depth}")
            return None
        
        # Prevent infinite loops by tracking visited paths
        if visited_paths is None:
            visited_paths = set()
        
        # Normalize path for comparison
        normalized_path = os.path.normpath(start_path).lower()
        if normalized_path in visited_paths:
            logger.warning(f"⚠️ Already visited: {start_path}, skipping to prevent loop")
            return None
        visited_paths.add(normalized_path)
        
        logger.info(f"📂 Navigating: {start_path} (depth: {depth})")
        
        # Get folder listing
        listing_data = list_folder_items(start_path)
        if "error" in listing_data:
            logger.error(f"Error: {listing_data['error']}")
            return None
        
        # Check if folder is empty
        folders = listing_data.get("folders", [])
        executables = listing_data.get("executables", [])
        if not folders and not executables:
            logger.warning(f"⚠️ Folder appears empty: {start_path}")
            # Try direct listing as fallback
            try:
                direct_items = os.listdir(start_path)
                if direct_items:
                    logger.info(f"📋 Direct listing found {len(direct_items)} items, but list_folder_items found none")
            except:
                pass
        
        formatted_listing = format_folder_listing(listing_data)
        
        # Quick check: if we found executables that might match directly
        executables = listing_data.get("executables", [])
        query_lower = user_query.lower()
        query_words = extract_keywords(user_query)
        
        # Check if user explicitly asked for setup/install
        setup_keywords = ['setup', 'install', 'installer', 'uninstall']
        user_wants_setup = any(keyword in query_lower for keyword in setup_keywords)
        
        # Generate variations for better matching (common program-related terms)
        query_variations = set(query_words)
        # Add common program folder variations
        common_program_terms = ["prog", "program", "app", "application", "bin", "exe"]
        for term in common_program_terms:
            if any(word in query_lower for word in ["program", "app", "application", "software"]):
                query_variations.add(term)
        
        # Separate setup files from main executables
        main_executables = []
        setup_files = []
        
        for exe in executables:
            exe_name_lower = exe["name"].lower()
            is_setup = any(keyword in exe_name_lower for keyword in setup_keywords)
            
            if is_setup:
                setup_files.append(exe)
            else:
                main_executables.append(exe)
        
        # First, check main executables (not setup files)
        for exe in main_executables:
            exe_name_lower = exe["name"].lower()
            # Check if executable name matches query or variations
            if query_variations and any(word in exe_name_lower for word in query_variations):
                logger.info(f"✅ Found direct executable match: {exe['path']}")
                return exe["path"]
            # Also check if query is in executable name
            if query_lower in exe_name_lower or exe_name_lower in query_lower:
                logger.info(f"✅ Found executable name match: {exe['path']}")
                return exe["path"]
        
        # Only check setup files if user explicitly asked for them
        if user_wants_setup:
            for exe in setup_files:
                exe_name_lower = exe["name"].lower()
                if query_variations and any(word in exe_name_lower for word in query_variations):
                    logger.info(f"✅ Found setup file match: {exe['path']}")
                    return exe["path"]
        
        # Check folders with variations
        folders = listing_data.get("folders", [])
        for folder in folders:
            folder_name_lower = folder["name"].lower()
            if query_variations and any(word in folder_name_lower for word in query_variations):
                # If we're in a parent folder and found a subfolder, check if it's a program folder
                if depth > 0 or any(term in folder_name_lower for term in common_program_terms):
                    logger.info(f"✅ Found folder match with variations: {folder['path']}")
                    return folder["path"]
        
        # SMART CHECK: If current folder contains multiple matching items, it's likely the target folder
        # Count how many items in current folder match the query
        matching_items_count = 0
        matching_executables = [e for e in main_executables if
                                any(word in e["name"].lower() for word in query_variations)]
        matching_folders = [f for f in folders if any(word in f["name"].lower() for word in query_variations)]
        matching_items_count = len(matching_executables) + len(matching_folders)
        
        # If we have multiple matching items in current folder, this folder is likely the target
        if matching_items_count >= 2:
            logger.info(
                f"✅ Current folder contains {matching_items_count} matching items - opening parent folder: {start_path}")
            return start_path
        
        # If we have at least one strong match (executable or program folder), consider opening parent
        if matching_executables and len(matching_executables) >= 1:
            # Check if the executable name strongly matches (contains main keywords)
            strong_match = any(
                all(word in exe["name"].lower() for word in query_words if len(word) > 3)
                for exe in matching_executables
            )
            if strong_match:
                logger.info(f"✅ Current folder contains strong executable match - opening parent folder: {start_path}")
                return start_path
        
        # Build prompt for model
        system_context = self._get_system_prompt()
        prompt = f"""{system_context}

User Query: "{user_query}"

Current Location: {start_path}

Folder Contents:
{formatted_listing}

Analyze the contents CAREFULLY. Which folder should I explore next to find what the user wants?

SMART DECISION RULES:
1. If the CURRENT FOLDER (Current Location) contains multiple items (files/folders) that match the user's query, 
   the current folder itself is likely the target - choose "open" with the current folder path: "{start_path}"
2. If you see a specific file/folder that exactly matches the query, choose "open" with that item's path
3. If you see a folder that might contain what the user wants, choose "explore" with that folder's path
4. Match keywords from the user's query to folder/file names
5. Look for folders containing the main keywords from the query
6. Be flexible with spelling mistakes and variations
7. USE ONLY PATHS FROM THE LISTING ABOVE - copy the path exactly as shown after "->"
8. IMPORTANT: If the current folder has matching items, prefer opening the current folder over exploring subfolders
9. Only choose "not_found" if you're absolutely certain nothing matches
10. You can pick synomous folders names that contain the query keywords"""
        
        # Get model decision
        response_text = self.llm.generate_content(prompt)
        if not response_text:
            return None
        
        decision = self._parse_model_response(response_text)
        
        action = decision.get("action")
        path = decision.get("path")
        
        logger.info(f"🤖 Decision: {action} -> {path}")
        
        # If model chose to open the current folder itself, return it
        if action == "open" and path:
            # Normalize paths for comparison
            normalized_current = os.path.normpath(start_path).lower()
            normalized_path = os.path.normpath(path).lower()
            if normalized_current == normalized_path:
                logger.info(f"✅ Model chose to open current folder: {start_path}")
                return start_path
        
        # Check if user wants setup files
        query_lower = user_query.lower()
        setup_keywords = ['setup', 'install', 'installer', 'uninstall']
        user_wants_setup = any(keyword in query_lower for keyword in setup_keywords)
        
        if action == "open":
            if path and os.path.exists(path):
                # Check if it's a setup file and user didn't ask for it
                path_lower = path.lower()
                is_setup_file = any(keyword in path_lower for keyword in setup_keywords)
                
                if is_setup_file and not user_wants_setup:
                    # It's a setup file but user didn't ask for it - continue searching
                    logger.info(f"⚠️ Found setup file but user didn't ask for it, continuing search...")
                    # Try to find non-setup alternatives in the same directory
                    parent_dir = os.path.dirname(path) if os.path.isfile(path) else path
                    if os.path.isdir(parent_dir):
                        # Continue searching in parent directory
                        return self._navigate_to_target(parent_dir, user_query, depth + 1, visited_paths)
                    return None
                
                return path
            else:
                logger.warning(f"⚠️ Path doesn't exist: {path}")
                # Try parent directory
                if path:
                    parent = os.path.dirname(path)
                    if os.path.exists(parent):
                        return parent
                return None
        
        elif action == "explore":
            if path and os.path.exists(path):
                # Check if the folder contains only setup files
                path_lower = path.lower()
                is_setup_folder = any(keyword in path_lower for keyword in setup_keywords)
                
                if is_setup_folder and not user_wants_setup:
                    # Check if there are non-setup items in this folder
                    folder_listing = list_folder_items(path, max_items=20)
                    if "error" not in folder_listing:
                        # Check if there are main executables or folders (not just setup files)
                        has_main_items = (
                                len(folder_listing.get("executables", [])) > 0 or
                                len(folder_listing.get("folders", [])) > 0
                        )
                        if has_main_items:
                            # Continue exploring - there might be the actual program
                            logger.info(f"📂 Setup folder contains other items, continuing search...")
                            return self._navigate_to_target(path, user_query, depth + 1, visited_paths)
                        else:
                            # Only setup files, skip this folder
                            logger.info(f"⚠️ Folder contains only setup files, skipping...")
                            return None
                
                # Recursively explore
                return self._navigate_to_target(path, user_query, depth + 1, visited_paths)
            else:
                logger.warning(f"⚠️ Invalid path for exploration: {path}")
                return None
        
        elif action == "not_found":
            # Even if model says not_found, ALWAYS try to find best match from listing
            # This handles cases where model is too strict or misses obvious matches
            query_lower = user_query.lower()
            query_words = extract_keywords(user_query)
            query_variations = set(query_words)
            
            # Check if user wants setup
            setup_keywords = ['setup', 'install', 'installer', 'uninstall']
            user_wants_setup = any(keyword in query_lower for keyword in setup_keywords)
            
            # Add common program-related terms for better matching
            common_program_terms = ["prog", "program", "app", "application", "bin"]
            # Always add program terms if we're looking for a program
            query_variations.update(common_program_terms)
            
            folders = listing_data.get("folders", [])
            executables = listing_data.get("executables", [])
            
            # Get other files too
            other_files = listing_data.get("other_files", [])
            logger.info(
                f"📋 Model said not_found, but checking {len(folders)} folders, {len(executables)} executables, and {len(other_files)} other files in {start_path}...")
            
            # Check if current folder contains files matching the query
            query_lower = user_query.lower()
            query_words = extract_keywords(user_query)
            
            # Check if files in folder match query keywords
            matching_files = []
            for file in other_files:
                file_name_lower = file["name"].lower()
                # Check if file name contains query keywords
                if any(word in file_name_lower for word in query_words if len(word) > 2):
                    matching_files.append(file)
            
            # If we have multiple matching files, this folder is likely the target
            if len(matching_files) >= 2:
                logger.info(f"📋 Found {len(matching_files)} matching files in current folder - opening: {start_path}")
                return start_path
            
            # If no folders or executables found, try direct listing
            if not folders and not executables and not other_files:
                logger.warning(f"⚠️ No items found via list_folder_items in {start_path} - trying direct listing...")
                try:
                    direct_items = os.listdir(start_path)
                    logger.info(f"📋 Direct listing shows {len(direct_items)} items")
                    # Try to find folders and files manually
                    found_items = False
                    for item in direct_items:
                        if item.startswith('.'):
                            continue
                        item_path = os.path.join(start_path, item)
                        try:
                            if os.path.isdir(item_path):
                                folders.append({
                                    "name": item,
                                    "path": item_path
                                })
                                logger.info(f"📋 Found folder via direct listing: {item}")
                                found_items = True
                            elif os.path.isfile(item_path):
                                # Check if it's a relevant file type (use config)
                                from ..config.settings import SYSTEM_CONFIG
                                ext = os.path.splitext(item)[1].lower()
                                if ext in SYSTEM_CONFIG["other_file_extensions"] or ext in SYSTEM_CONFIG[
                                    "executable_extensions"]:
                                    other_files.append({
                                        "name": item,
                                        "path": item_path
                                    })
                                    logger.info(f"📋 Found file via direct listing: {item}")
                                    found_items = True
                        except (PermissionError, OSError):
                            continue
                    if found_items:
                        logger.info(f"📋 Found {len(folders)} folders and {len(other_files)} files via direct listing")
                        # After direct listing, immediately check if this folder matches the query
                        if other_files:
                            folder_name_lower = os.path.basename(start_path).lower()
                            query_lower = user_query.lower()
                            
                            # Extract keywords from query
                            query_keywords = extract_keywords(user_query)
                            
                            # Define synonyms for better matching
                            synonyms_map = {
                                "cv": ["resume", "resumes", "curriculum", "vitae"],
                                "resume": ["cv", "curriculum", "vitae"],
                                "certificate": ["cert", "certs", "certificates"],
                                "cert": ["certificate", "certificates", "certs"],
                                "document": ["doc", "docs", "documents"],
                                "photo": ["picture", "pictures", "image", "images"],
                                "movie": ["film", "films", "video", "videos"],
                                "music": ["song", "songs", "audio", "tracks"],
                            }
                            
                            # Expand query keywords with synonyms
                            expanded_keywords = set(query_keywords)
                            for keyword in query_keywords:
                                keyword_lower = keyword.lower()
                                if keyword_lower in synonyms_map:
                                    expanded_keywords.update(synonyms_map[keyword_lower])
                            
                            # Check if folder name matches query keywords (flexible matching with synonyms)
                            folder_matches = False
                            for keyword in expanded_keywords:
                                if len(keyword) > 2:
                                    keyword_lower = keyword.lower()
                                    # Check if keyword is in folder name or vice versa
                                    if keyword_lower in folder_name_lower or folder_name_lower in keyword_lower or any(
                                            part in folder_name_lower for part in keyword_lower.split() if
                                            len(part) > 2):
                                        folder_matches = True
                                        break
                            
                            # Check if query mentions folder name or related terms
                            query_mentions_folder = False
                            folder_parts = folder_name_lower.split()
                            for part in folder_parts:
                                if len(part) > 2:
                                    # Check direct match
                                    if part in query_lower:
                                        query_mentions_folder = True
                                        break
                                    # Check synonyms
                                    for keyword in expanded_keywords:
                                        if len(keyword) > 2 and (part in keyword.lower() or keyword.lower() in part):
                                            query_mentions_folder = True
                                            break
                                if query_mentions_folder:
                                    break
                            
                            # If folder name matches query or query mentions folder, and we have files - this is the target
                            if (folder_matches or query_mentions_folder) and len(other_files) >= 1:
                                logger.info(
                                    f"📋 Folder '{os.path.basename(start_path)}' matches query and contains {len(other_files)} files - opening: {start_path}")
                                return start_path
                            
                            # If we have multiple files and folder name is short/simple, likely the target folder
                            if len(other_files) >= 2:
                                # Check if folder name could be related to query (e.g., "certs" -> "certificates")
                                folder_short = folder_name_lower.replace(" ", "").replace("_", "").replace("-", "")
                                query_short = query_lower.replace(" ", "").replace("_", "").replace("-", "")
                                if any(part in query_short for part in folder_short.split() if len(part) > 3) or len(
                                        folder_name_lower.split()) <= 2:
                                    logger.info(
                                        f"📋 Found {len(other_files)} files in folder matching query context - opening: {start_path}")
                                    return start_path
                except Exception as e:
                    logger.error(f"Error in direct listing: {e}")
            
            # Separate setup files from main executables
            main_executables = [e for e in executables if not any(kw in e["name"].lower() for kw in setup_keywords)]
            setup_files = [e for e in executables if any(kw in e["name"].lower() for kw in setup_keywords)]
            
            # Check other files that might match the query
            if other_files:
                # If we have multiple matching files, this folder is likely the target
                matching_other_files = [f for f in other_files if
                                        any(word in f["name"].lower() for word in query_words if len(word) > 2)]
                if len(matching_other_files) >= 2:
                    logger.info(f"📋 Found {len(matching_other_files)} matching files - opening: {start_path}")
                    return start_path
                # If we have files and query matches folder name, likely the target
                folder_name_lower = os.path.basename(start_path).lower()
                if len(matching_other_files) >= 1 and any(
                        word in folder_name_lower for word in query_words if len(word) > 2):
                    logger.info(f"📋 Found matching files in folder matching query - opening: {start_path}")
                    return start_path
                # If folder name matches query and we have any files, likely the target
                if any(word in folder_name_lower for word in query_words if len(word) > 2) and len(other_files) >= 1:
                    logger.info(
                        f"📋 Found {len(other_files)} files in folder matching query name - opening: {start_path}")
                    return start_path
            
            # Check main executables first (prioritize non-setup)
            for exe in main_executables:
                exe_name_lower = exe["name"].lower()
                # More lenient matching - check if any query word or variation matches
                if query_variations and any(word in exe_name_lower for word in query_variations):
                    logger.info(f"📋 Found executable match despite not_found: {exe['path']}")
                    return exe["path"]
                # Also check partial matches
                if any(word in exe_name_lower for word in query_words if len(word) > 3):
                    logger.info(f"📋 Found partial executable match: {exe['path']}")
                    return exe["path"]
            
            # Only check setup files if user wants them or no other options
            if user_wants_setup or len(main_executables) == 0:
                for exe in setup_files:
                    exe_name_lower = exe["name"].lower()
                    if query_variations and any(word in exe_name_lower for word in query_variations):
                        logger.info(f"📋 Found setup file match: {exe['path']}")
                        return exe["path"]
            
            # Check folders - be more lenient here
            best_match = None
            best_score = 0
            for folder in folders:
                folder_name_lower = folder["name"].lower()
                is_setup_folder = any(kw in folder_name_lower for kw in setup_keywords)
                
                # Skip setup folders unless user wants them
                if is_setup_folder and not user_wants_setup:
                    continue
                
                score = 0
                # Score by keyword matches
                for word in query_variations:
                    if word in folder_name_lower:
                        score += 2  # Higher weight for variations
                for word in query_words:
                    if word in folder_name_lower:
                        score += 3  # Even higher for actual query words
                
                # Bonus for common program folder names
                if any(term in folder_name_lower for term in common_program_terms):
                    score += 5  # Strong bonus for program folders
                
                # Bonus if we're in a parent folder (e.g., "Davinci") and found subfolder (e.g., "prog")
                if depth > 0:
                    # Check if parent folder name is in query (e.g., "davinci" in query and we're in "Davinci" folder)
                    parent_name = os.path.basename(start_path).lower()
                    if any(word in parent_name for word in query_words):
                        score += 3  # Bonus for subfolders of matching parent
                
                # Penalty for setup folders if user didn't ask
                if is_setup_folder:
                    score -= 1
                
                if score > best_score:
                    best_score = score
                    best_match = folder["path"]
            
            # If we found a match with any score, use it (be more lenient)
            if best_match and best_score > 0:
                logger.info(f"📋 Using best match despite not_found: {best_match} (score: {best_score})")
                # Recursively explore the best match
                result = self._navigate_to_target(best_match, user_query, depth + 1, visited_paths)
                if result:
                    return result
                # If exploration didn't find anything, return the folder itself
                return best_match
            
            # Last resort: if nothing else found and there are setup files, return the best setup file
            if not user_wants_setup and len(setup_files) > 0 and len(main_executables) == 0:
                logger.info(f"📋 No main items found, using setup file as last resort")
                return setup_files[0]["path"]
            
            # Even if score is 0, if we're in a matching parent folder, try exploring ALL non-setup folders
            if depth > 0:
                parent_name = os.path.basename(start_path).lower()
                if any(word in parent_name for word in query_words):
                    # We're in a matching parent folder (e.g., "Davinci"), try all non-setup folders
                    logger.info(f"📋 In matching parent folder '{parent_name}', checking all subfolders...")
                    non_setup_folders = [f for f in folders if
                                         not any(kw in f["name"].lower() for kw in setup_keywords)]
                    
                    # Prioritize folders with program-related terms
                    program_folders = [f for f in non_setup_folders if
                                       any(term in f["name"].lower() for term in common_program_terms)]
                    if program_folders:
                        # Try program folders first
                        for folder in program_folders:
                            logger.info(f"📋 Exploring program folder: {folder['path']}")
                            result = self._navigate_to_target(folder["path"], user_query, depth + 1, visited_paths)
                            if result:
                                return result
                    
                    # Try other non-setup folders
                    for folder in non_setup_folders:
                        if folder not in program_folders:  # Skip already tried
                            logger.info(f"📋 Exploring folder: {folder['path']}")
                            result = self._navigate_to_target(folder["path"], user_query, depth + 1, visited_paths)
                            if result:
                                return result
                    
                    # If we found folders but nothing matched, return the first program folder or first folder
                    if program_folders:
                        logger.info(f"📋 No match found, returning program folder: {program_folders[0]['path']}")
                        return program_folders[0]["path"]
                    elif non_setup_folders:
                        logger.info(f"📋 No match found, returning folder: {non_setup_folders[0]['path']}")
                        return non_setup_folders[0]["path"]
            
            return None
        
        else:
            # Fallback: try to extract path from response
            path_matches = re.findall(r'([A-Z]:[\\/][^\s"\'<>\)]+)', response_text, re.IGNORECASE)
            # Sort by length (prefer longer, more complete paths)
            path_matches = sorted(set(path_matches), key=len, reverse=True)
            for path_match in path_matches:
                path_match = path_match.strip().rstrip('.,;:)')
                # Validate path exists and is reasonable
                if len(path_match) > 3 and os.path.exists(path_match):
                    logger.info(f"📋 Extracted path from response: {path_match}")
                    return path_match
                # Try parent if path doesn't exist
                elif len(path_match) > 3:
                    parent = os.path.dirname(path_match)
                    if os.path.exists(parent) and len(parent) > 3:
                        logger.info(f"📋 Extracted path, using parent: {parent}")
                        return parent
            
            # If still no path, find best matching folder with variations
            query_lower = user_query.lower()
            query_words = extract_keywords(user_query)
            query_variations = set(query_words)
            
            # Add common program-related terms
            common_program_terms = ["prog", "program", "app", "application", "bin"]
            if any(word in query_lower for word in ["program", "app", "application", "software"]):
                query_variations.update(common_program_terms)
            
            folders = listing_data.get("folders", [])
            best_match = None
            best_score = 0
            
            for folder in folders:
                folder_name_lower = folder["name"].lower()
                score = sum(1 for word in query_variations if word in folder_name_lower)
                # Bonus for program-related folders
                if any(term in folder_name_lower for term in common_program_terms):
                    score += 2
                if score > best_score:
                    best_score = score
                    best_match = folder["path"]
            
            if best_match and best_score > 0:
                logger.info(f"📋 Using best folder match: {best_match} (score: {best_score})")
                return best_match
            
            return None
    
    def _is_partition_request(self, query: str) -> Optional[str]:
        """Check if user wants to open a partition directly."""
        query_lower = query.lower().strip()
        
        # Patterns: "open D", "open D:", "open D drive", "D:", "D drive"
        for partition in self.partitions:
            partition_letter = partition[0].lower()
            
            # Direct partition requests
            if query_lower in [f"open {partition_letter}", f"open {partition_letter}:",
                               f"{partition_letter}:", f"{partition_letter} drive",
                               f"open {partition_letter} drive", f"{partition_letter}:\\"]:
                return partition
            
            # Check if query starts with partition letter
            if query_lower.startswith(partition_letter) and len(query_lower) <= 3:
                return partition
        
        return None
    
    def find_and_open(self, user_query: str) -> bool:
        """
        Main method to find and open the user's requested file/folder.
        Returns True if successful, False otherwise.
        """
        logger.info(f"🔍 Processing query: '{user_query}'")
        
        # Step 0: Check if user is requesting a Google search (using LLM for intelligent detection)
        is_search, search_query = check_and_open_search(user_query, llm=self.llm)
        if is_search:
            if search_query:
                logger.info(f"🌐 Google search detected: '{search_query}'")
                print(f"\n🌐 Opening Google search for: '{search_query}'")
                print("✅ Browser opened with search results")
                return True
            else:
                logger.warning("⚠️ Search detected but failed to open browser")
                print("\n⚠️ Failed to open browser for search")
                return False
        
        # Step 1: Check if user wants to open a partition directly
        direct_partition = self._is_partition_request(user_query)
        if direct_partition:
            logger.info(f"📍 Direct partition request: {direct_partition}")
            print(f"\n📂 Opening partition: {direct_partition}")
            return self._open_path(direct_partition)
        
        print(f"\n🔍 Searching for: '{user_query}'...")
        
        # Step 2: Check if user specified a partition in query
        query_lower = user_query.lower()
        target_partition = None
        
        for partition in self.partitions:
            partition_letter = partition[0].lower()
            if f"{partition_letter}:" in query_lower or f"{partition_letter} drive" in query_lower:
                target_partition = partition
                logger.info(f"📍 User specified partition: {partition}")
                break
        
        # Step 3: Determine partitions to search
        if target_partition:
            partitions_to_search = [target_partition]
        else:
            # Skip C: drive initially if configured
            if self.skip_c_drive:
                partitions_to_search = [p for p in self.partitions if not p.startswith("C:")]
                if "C:\\" in self.partitions:
                    partitions_to_search.append("C:\\")  # Add as fallback
            else:
                partitions_to_search = self.partitions
        
        # Step 4: Explore each partition with AI
        for partition in partitions_to_search:
            logger.info(f"🔍 Searching in partition: {partition}")
            print(f"   📂 Checking {partition}...")
            
            # Get model's decision on which folder to explore
            next_path = self._explore_partition(partition, user_query)
            
            if not next_path:
                logger.info(f"   ⚠️ No match found in {partition}")
                continue
            
            logger.info(f"   ✅ Found potential match: {next_path}")
            print(f"   ✅ Exploring: {os.path.basename(next_path)}...")
            
            # Navigate from this path
            result = self._navigate_to_target(next_path, user_query, depth=0, visited_paths=set())
            if result:
                return self._open_path(result)
        
        # Not found
        logger.warning("⚠️ Target not found after searching all partitions")
        print(f"\n❌ Could not find: '{user_query}'")
        print("💡 Suggestions:")
        print("   - Check the spelling")
        print("   - Try a more specific query")
        print("   - Make sure the item exists on your system")
        print("   - Try specifying a partition (e.g., 'open D: drive')")
        return False
    
    def _find_without_ai(self, user_query: str, partitions: List[str]) -> bool:
        """Fallback search without AI when API is unavailable."""
        from ..utils.file_system import list_folder_items, extract_keywords
        
        query_lower = user_query.lower()
        keywords = extract_keywords(user_query)
        
        # Minimum score threshold to consider a match
        MIN_SCORE_THRESHOLD = 30
        
        logger.info(f"🔍 Fallback search for: '{user_query}'")
        logger.info(f"   Keywords: {keywords}")
        
        # Collect all matches with scores
        all_matches = []
        
        for partition in partitions:
            print(f"   📂 Searching {partition}...")
            
            # List folders in partition
            listing = list_folder_items(partition, max_items=100)
            if "error" in listing:
                continue
            
            # Check folders and score them
            folders = listing.get("folders", [])
            for folder in folders:
                folder_name_lower = folder["name"].lower()
                score = self._calculate_match_score(folder_name_lower, query_lower, keywords)
                
                if score >= MIN_SCORE_THRESHOLD:
                    all_matches.append({
                        "path": folder["path"],
                        "name": folder["name"],
                        "score": score,
                        "type": "folder"
                    })
                    print(f"   ✅ Found: {folder['name']} (score: {score})")
            
            # Check executables and score them
            executables = listing.get("executables", [])
            for exe in executables:
                exe_name_lower = exe["name"].lower()
                score = self._calculate_match_score(exe_name_lower, query_lower, keywords)
                
                if score >= MIN_SCORE_THRESHOLD:
                    all_matches.append({
                        "path": exe["path"],
                        "name": exe["name"],
                        "score": score,
                        "type": "executable"
                    })
                    print(f"   ✅ Found: {exe['name']} (score: {score})")
        
        # Sort by score (highest first)
        all_matches.sort(key=lambda x: x["score"], reverse=True)
        
        if not all_matches:
            print(f"\n❌ Could not find: '{user_query}' (fallback mode)")
            print("💡 Try a more specific query or check spelling")
            return False
        
        # Filter to only show good matches (top 3)
        good_matches = [m for m in all_matches if m["score"] >= MIN_SCORE_THRESHOLD]
        
        if not good_matches:
            print(f"\n❌ No good matches found for: '{user_query}' (fallback mode)")
            return False
        
        # Try the best matches (top 3)
        print(f"\n📋 Found {len(good_matches)} good match(es)")
        best_match = good_matches[0]
        
        # If best match score is too low, don't open it
        if best_match["score"] < 50 and len(good_matches) > 1:
            # Check if second match is significantly better
            if good_matches[1]["score"] > best_match["score"] * 1.5:
                best_match = good_matches[1]
        
        logger.info(f"   Best match: {best_match['name']} (score: {best_match['score']})")
        
        # If it's a folder, try to find the actual app inside
        if best_match["type"] == "folder":
            result = self._search_folder_simple(best_match["path"], user_query, keywords)
            if result:
                return self._open_path(result)
        
        # Open the best match
        return self._open_path(best_match["path"])
    
    def _calculate_match_score(self, item_name: str, query: str, keywords: List[str]) -> int:
        """Calculate how well an item matches the query."""
        item_lower = item_name.lower()
        query_lower = query.lower()
        score = 0
        
        if not keywords:
            return 0
        
        # Extract important keywords (ignore very short ones unless they're important)
        important_keywords = [kw for kw in keywords if len(kw) > 3 or kw in ['vs', 'ng', 'ai']]
        if not important_keywords:
            important_keywords = keywords
        
        # Exact query match (highest priority)
        if query_lower == item_lower:
            score += 200
        elif query_lower in item_lower:
            score += 100
        elif item_lower in query_lower:
            score += 80
        
        # All important keywords match in order (big bonus)
        if len(important_keywords) > 1:
            query_phrase = " ".join(important_keywords)
            if query_phrase in item_lower:
                score += 80
            # Check if keywords appear in order (even with words in between)
            item_words = item_lower.split()
            query_words = important_keywords
            if all(any(qw in word for word in item_words) for qw in query_words):
                # Check if order is preserved
                indices = []
                for qw in query_words:
                    for i, word in enumerate(item_words):
                        if qw in word and i not in indices:
                            indices.append(i)
                            break
                if len(indices) == len(query_words) and indices == sorted(indices):
                    score += 50
        
        # All important keywords match (not necessarily in order)
        matched_important = sum(1 for kw in important_keywords if kw in item_lower)
        if matched_important == len(important_keywords):
            score += 60
        elif matched_important >= len(important_keywords) * 0.7:  # At least 70% match
            score += 30
        
        # Individual keyword matches
        matched_keywords = 0
        for kw in important_keywords:
            if kw in item_lower:
                matched_keywords += 1
                score += 20
                # Bonus for keyword at start
                if item_lower.startswith(kw):
                    score += 15
                # Bonus for exact keyword match (word boundary)
                import re
                if re.search(r'\b' + re.escape(kw) + r'\b', item_lower):
                    score += 10
        
        # Heavy penalty if important keywords are missing
        missing_important = len(important_keywords) - matched_important
        if missing_important > 0:
            score -= missing_important * 30
        
        # Penalty for extra unrelated words
        item_words = set(item_lower.split())
        query_words_set = set(query_lower.split())
        extra_words = item_words - query_words_set
        # Remove common words from penalty
        common_words = {'and', 'the', 'of', 'a', 'an', 'in', 'on', 'at', 'for', 'to', 'with'}
        extra_words = extra_words - common_words
        if len(extra_words) > len(query_words_set):
            score -= len(extra_words) * 5
        
        # Bonus for matching most/all keywords
        if keywords:
            match_ratio = matched_keywords / len(important_keywords) if important_keywords else 0
            score += int(match_ratio * 30)
        
        # Penalty for very long names (prefer shorter, more specific)
        item_word_count = len(item_lower.split())
        query_word_count = len(query_lower.split())
        if item_word_count > query_word_count * 3:
            score -= 20
        elif item_word_count == query_word_count:
            score += 15  # Bonus for same word count
        
        # Special handling for common app names
        if "code" in query_lower and "code" not in item_lower:
            score -= 40  # Heavy penalty if query has "code" but item doesn't
        if "code" in query_lower and "code" in item_lower:
            score += 25  # Bonus if both have "code"
        
        # Penalty for very low match ratio
        if important_keywords:
            match_ratio = matched_important / len(important_keywords)
            if match_ratio < 0.5:  # Less than 50% of important keywords match
                score -= 50
        
        return max(0, score)  # Ensure non-negative
    
    def _search_folder_simple(self, folder_path: str, query: str, keywords: List[str], depth: int = 0) -> Optional[str]:
        """Simple recursive search without AI."""
        if depth >= 4:  # Limit depth in fallback mode
            return None
        
        from ..utils.file_system import list_folder_items
        
        listing = list_folder_items(folder_path, max_items=50)
        if "error" in listing:
            return None
        
        query_lower = query.lower()
        best_match = None
        best_score = 0
        
        # Check executables first (they're usually what we want)
        for exe in listing.get("executables", []):
            exe_name_lower = exe["name"].lower()
            score = self._calculate_match_score(exe_name_lower, query_lower, keywords)
            if score > best_score:
                best_score = score
                best_match = exe["path"]
        
        # If we found a good executable match, return it
        if best_score > 30:
            return best_match
        
        # Check folders
        for folder in listing.get("folders", []):
            folder_name_lower = folder["name"].lower()
            score = self._calculate_match_score(folder_name_lower, query_lower, keywords)
            
            if score > 0:
                # Recursively search inside
                result = self._search_folder_simple(folder["path"], query, keywords, depth + 1)
                if result:
                    return result
                
                # If this folder matches well and we don't have a better match, use it
                if score > best_score:
                    best_score = score
                    best_match = folder["path"]
        
        return best_match
    
    def _open_path(self, path: str) -> bool:
        """Open a file or folder using the system default application."""
        if not os.path.exists(path):
            logger.error(f"Path does not exist: {path}")
            return False
        
        try:
            logger.info(f"🚀 Opening: {path}")
            print(f"\n✅ Found: {path}")
            print(f"🚀 Opening...")
            
            if open_path(path):
                print("✅ Opened successfully!")
                return True
            else:
                print("❌ Failed to open path")
                return False
        
        except Exception as e:
            logger.error(f"Error opening path: {e}")
            print(f"❌ Error opening: {e}")
            return False


if __name__ == "__main__":
    # Add parent directories to path for imports
    import sys
    from pathlib import Path
    
    # Get the project root (Alquad directory)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # Now import and run
    from ..utils.logger import setup_logger
    
    logger = setup_logger()
    
    try:
        agent = SmartFileSystemAgent()
        
        print("\n" + "=" * 60)
        print("🤖 Alquad - Smart File System Agent")
        print("   Powered by Ollama (deepseek-r1:7b-qwen-distill-q4_k_m)")
        print("=" * 60)
        print(f"\n📂 Available Partitions: {', '.join(agent.partitions)}")
        print("\n💡 Examples:")
        print("   - 'open league of legends'")
        print("   - 'find chrome'")
        print("   - 'launch steam'")
        print("   - 'open D: drive'")
        print("\nType 'q' to quit\n")
        
        while True:
            try:
                query = input("📂 Request: ").strip()
                if not query:
                    continue
                if query.lower() == 'q':
                    print("👋 Goodbye!")
                    break
                
                agent.find_and_open(query)
                print()  # Empty line for readability
            
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                print(f"❌ Error: {e}")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

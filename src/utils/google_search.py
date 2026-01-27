import webbrowser
import logging
import re
from typing import Optional, Tuple
from urllib.parse import quote_plus

logger = logging.getLogger("GoogleSearch")

# Keywords that indicate a search request
SEARCH_KEYWORDS = [
    "search",
    "google",
    "look up",
    "find information about",
    "what is",
    "who is",
    "where is",
    "how to",
    "explain",
    "tell me about",
    "information about",
    "search for",
    "search about",
    "google search",
    "web search",
    "internet search",
]

# Phrases that strongly indicate a search request
SEARCH_PHRASES = [
    r"search\s+(for|about|on)\s+",
    r"google\s+(search\s+)?(for|about|on)?\s*",
    r"look\s+up\s+",
    r"find\s+(information\s+)?(about|on)\s+",
    r"what\s+is\s+",
    r"who\s+is\s+",
    r"where\s+is\s+",
    r"how\s+to\s+",
    r"explain\s+",
    r"tell\s+me\s+about\s+",
    r"information\s+about\s+",
]


def is_search_request(query: str) -> bool:
    """
    Determine if the user query is requesting a Google/web search.
    
    Args:
        query: The user's input query
        
    Returns:
        True if the query appears to be a search request, False otherwise
    """
    if not query or len(query.strip()) < 3:
        return False
    
    query_lower = query.lower().strip()
    
    # Check for explicit search phrases
    for phrase in SEARCH_PHRASES:
        if re.search(phrase, query_lower, re.IGNORECASE):
            return True
    
    # Check if query starts with search keywords
    for keyword in SEARCH_KEYWORDS:
        if query_lower.startswith(keyword):
            return True
    
    # Check if query contains "search" or "google" followed by content
    if re.search(r"(search|google)\s+(for|about|on)?\s+.+", query_lower):
        return True
    
    # Check for question patterns that suggest information seeking
    question_patterns = [
        r"^(what|who|where|when|why|how)\s+",
        r"\?$",  # Ends with question mark
    ]
    
    for pattern in question_patterns:
        if re.search(pattern, query_lower):
            # Additional check: if it's a short question, likely a search
            if len(query_lower.split()) <= 10:
                return True
    
    return False


def extract_search_query(query: str) -> str:
    """
    Extract the actual search query from a user's request.
    
    Examples:
        "search for python tutorials" -> "python tutorials"
        "google machine learning" -> "machine learning"
        "what is artificial intelligence" -> "artificial intelligence"
        
    Args:
        query: The user's input query
        
    Returns:
        The extracted search query string
    """
    query_lower = query.lower().strip()
    
    # Remove common search prefixes
    prefixes_to_remove = [
        r"^(search\s+(for|about|on)\s+)",
        r"^(google\s+(search\s+)?(for|about|on)?\s*)",
        r"^(look\s+up\s+)",
        r"^(find\s+(information\s+)?(about|on)\s+)",
        r"^(what\s+is\s+)",
        r"^(who\s+is\s+)",
        r"^(where\s+is\s+)",
        r"^(how\s+to\s+)",
        r"^(explain\s+)",
        r"^(tell\s+me\s+about\s+)",
        r"^(information\s+about\s+)",
        r"^(web\s+search\s+(for|about)?\s*)",
        r"^(internet\s+search\s+(for|about)?\s*)",
    ]
    
    search_query = query
    for prefix_pattern in prefixes_to_remove:
        search_query = re.sub(prefix_pattern, "", search_query, flags=re.IGNORECASE)
    
    # Remove trailing question marks and whitespace
    search_query = search_query.strip().rstrip("?")
    
    # If nothing left or too short, use original query
    if not search_query or len(search_query.strip()) < 2:
        return query.strip()
    
    return search_query.strip()


def open_google_search(query: str, new_window: bool = True) -> bool:
    """
    Open Google search in the default browser with the given query.
    
    Args:
        query: The search query to execute
        new_window: If True, opens in a new browser window/tab
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract the actual search query
        search_query = extract_search_query(query)
        
        # URL encode the search query
        encoded_query = quote_plus(search_query)
        
        # Construct Google search URL
        google_url = f"https://www.google.com/search?q={encoded_query}"
        
        logger.info(f"🌐 Opening Google search: {search_query}")
        
        # Open in browser
        # new=2 opens in a new tab if possible
        webbrowser.open(google_url, new=2 if new_window else 0)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error opening Google search: {e}")
        return False


def is_search_request_with_llm(query: str, llm) -> bool:
    """
    Use LLM to intelligently determine if the user query is requesting a Google/web search.
    
    Args:
        query: The user's input query
        llm: The LLM client instance (OllamaClient or GeminiClient)
        
    Returns:
        True if the query appears to be a search request, False otherwise
    """
    if not query or len(query.strip()) < 3:
        return False
    
    # First do a quick pattern-based check - if it's clearly a search, return immediately
    if is_search_request(query):
        return True
    
    # Use LLM for ambiguous cases
    prompt = f"""Analyze the following user query and determine if the user is asking for a web/Google search to find information online, or if they are asking to find/open a file, folder, or application on their computer.

User Query: "{query}"

Respond with ONLY a JSON object in this exact format:
{{"is_search_request": true/false, "reason": "brief explanation"}}

Examples:
- "search for python tutorials" -> {{"is_search_request": true, "reason": "explicit search request"}}
- "what is machine learning" -> {{"is_search_request": true, "reason": "information-seeking question"}}
- "open chrome" -> {{"is_search_request": false, "reason": "requesting to open an application"}}
- "find my documents folder" -> {{"is_search_request": false, "reason": "requesting to find a local folder"}}
- "search for python" -> {{"is_search_request": true, "reason": "explicit search request"}}
- "open python" -> {{"is_search_request": false, "reason": "requesting to open an application"}}

IMPORTANT: Only return true for search requests if the user is clearly asking to search the web/Google for information. If they're asking to find or open something on their computer, return false."""

    try:
        response = llm.generate_content(prompt)
        if not response:
            # Fallback to pattern-based detection if LLM fails
            return is_search_request(query)
        
        # Parse JSON response
        import json
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        result = json.loads(response)
        is_search = result.get("is_search_request", False)
        
        logger.info(f"🤖 LLM search detection: {is_search} - {result.get('reason', 'N/A')}")
        return is_search
        
    except Exception as e:
        logger.warning(f"⚠️ LLM search detection failed: {e}, falling back to pattern-based detection")
        return is_search_request(query)


def check_and_open_search(query: str, llm=None) -> Tuple[bool, Optional[str]]:
    """
    Check if query is a search request and open browser if so.
    
    Args:
        query: The user's input query
        llm: Optional LLM client for intelligent detection (if None, uses pattern-based)
        
    Returns:
        Tuple of (is_search_request, search_query_if_applicable)
        - is_search_request: True if this was detected as a search request
        - search_query_if_applicable: The extracted search query, or None
    """
    # Use LLM if available, otherwise use pattern-based detection
    if llm:
        is_search = is_search_request_with_llm(query, llm)
    else:
        is_search = is_search_request(query)
    
    if is_search:
        search_query = extract_search_query(query)
        success = open_google_search(query)
        
        if success:
            return (True, search_query)
        else:
            return (True, None)  # Detected as search but failed to open
    
    return (False, None)

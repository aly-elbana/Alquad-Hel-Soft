"""
Ollama API client with retry logic and error handling.
"""

import time
import logging
from typing import Optional
import requests
import json

from src.config.settings import OLLAMA_CONFIG, AGENT_CONFIG

logger = logging.getLogger("FileSystemAgent")

class OllamaClient:
    """Client for interacting with Ollama local API."""
    
    def __init__(self):
        """Initialize Ollama client."""
        self.base_url = OLLAMA_CONFIG["base_url"]
        self.model_name = OLLAMA_CONFIG["model_name"]
        self.timeout = OLLAMA_CONFIG["timeout"]
        
        # Test connection
        if not self._test_connection():
            raise ValueError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running and the model '{self.model_name}' is available."
            )
        
        logger.info(f"✅ Initialized Ollama client: {self.model_name}")
    
    def _test_connection(self) -> bool:
        """Test connection to Ollama API."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if self.model_name in model_names:
                    logger.info(f"✅ Model '{self.model_name}' is available")
                    return True
                else:
                    logger.warning(f"⚠️ Model '{self.model_name}' not found. Available models: {model_names}")
                    return False
            return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to Ollama: {e}")
            return False
    
    def generate_content(self, prompt: str, retry: bool = True) -> Optional[str]:
        """
        Generate content using Ollama API with retry logic.
        
        Args:
            prompt: The prompt to send to the model
            retry: Whether to retry on failure
            
        Returns:
            Generated text or None on failure
        """
        retry_attempts = AGENT_CONFIG["retry_attempts"]
        retry_delay = AGENT_CONFIG["retry_delay"]
        
        for attempt in range(retry_attempts if retry else 1):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,  # Lower temperature for more consistent results
                            "top_p": 0.9,
                        }
                    },
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "response" in result:
                        return result["response"].strip()
                    else:
                        logger.warning("⚠️ Empty response from Ollama")
                        if not retry or attempt == retry_attempts - 1:
                            return None
                        time.sleep(retry_delay)
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"❌ Ollama API error: {error_msg}")
                    if not retry or attempt == retry_attempts - 1:
                        return None
                    time.sleep(retry_delay)
                    
            except requests.exceptions.Timeout:
                logger.error(f"❌ Request timeout (attempt {attempt + 1}/{retry_attempts})")
                if not retry or attempt == retry_attempts - 1:
                    return None
                time.sleep(retry_delay)
            except requests.exceptions.ConnectionError:
                logger.error(f"❌ Connection error - is Ollama running? (attempt {attempt + 1}/{retry_attempts})")
                if attempt == 0:
                    print("\n⚠️  Cannot connect to Ollama!")
                    print(f"   Make sure Ollama is running at {self.base_url}")
                    print("   Start Ollama or check your connection.")
                if not retry or attempt == retry_attempts - 1:
                    return None
                time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"❌ Error generating content (attempt {attempt + 1}/{retry_attempts}): {e}")
                if not retry or attempt == retry_attempts - 1:
                    return None
                time.sleep(retry_delay)
        
        return None
    
    def is_quota_exceeded(self) -> bool:
        """Ollama doesn't have quota limits, so always return False."""
        return False

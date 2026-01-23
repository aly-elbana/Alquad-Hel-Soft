import time
import logging
from typing import Optional, Dict, Any
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from src.config.settings import GEMINI_API_KEY, GEMINI_MODELS, AGENT_CONFIG

logger = logging.getLogger("FileSystemAgent")

class GeminiClient:
    """Client for interacting with Gemini API."""
    
    def __init__(self):
        """Initialize Gemini client."""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in configuration")
        
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Configure safety settings
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # Initialize model
        self.model = self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Gemini model with fallback."""
        retry_attempts = AGENT_CONFIG["retry_attempts"]
        retry_delay = AGENT_CONFIG["retry_delay"]
        
        for model_name in GEMINI_MODELS:
            for attempt in range(retry_attempts):
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        safety_settings=self.safety_settings
                    )
                    logger.info(f"✅ Initialized Gemini model: {model_name}")
                    return model
                except Exception as e:
                    if attempt < retry_attempts - 1:
                        logger.warning(f"⚠️ Failed to initialize {model_name}, retrying... ({attempt + 1}/{retry_attempts})")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"❌ Failed to initialize {model_name}: {e}")
        
        raise ValueError("Failed to initialize any Gemini model")
    
    def generate_content(self, prompt: str, retry: bool = True) -> Optional[str]:
        """
        Generate content using Gemini API with retry logic.
        
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
                response = self.model.generate_content(prompt)
                if response and response.text:
                    return response.text
                else:
                    logger.warning("⚠️ Empty response from Gemini")
                    if not retry or attempt == retry_attempts - 1:
                        return None
                    time.sleep(retry_delay)
            except Exception as e:
                error_str = str(e)
                
                # Check for quota/rate limit errors
                if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                    if attempt == 0:  # Only show message on first attempt
                        logger.error("❌ API Quota/Rate Limit Exceeded")
                        print("\n⚠️  API Quota Exceeded!")
                        print("   Your Gemini API quota has been exceeded.")
                        print("   The system will use fallback mode (without AI).")
                        print("   Please check: https://ai.google.dev/gemini-api/docs/rate-limits")
                    return None  # Don't retry on quota errors
                
                logger.error(f"❌ Error generating content (attempt {attempt + 1}/{retry_attempts}): {e}")
                if not retry or attempt == retry_attempts - 1:
                    return None
                time.sleep(retry_delay)
        
        return None
    
    def is_quota_exceeded(self) -> bool:
        """Check if quota is exceeded by making a test call."""
        try:
            test_response = self.model.generate_content("test")
            return False
        except Exception as e:
            error_str = str(e)
            return "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower()

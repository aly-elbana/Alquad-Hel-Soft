import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH, override=True)

# ==================== LLM PROVIDER SELECTION ====================

# Choose LLM provider: "ollama" or "gemini"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()  # Default to ollama

# ==================== OLLAMA CONFIG ====================

OLLAMA_CONFIG = {
    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),  # Default Ollama URL
    "model_name": os.getenv("OLLAMA_MODEL", "deepseek-r1:7b-qwen-distill-q4_k_m"),
    "timeout": 120,  # Timeout in seconds for API calls
}

# ==================== GEMINI CONFIG ====================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)  # Required if using Gemini
GEMINI_MODELS = [
    "gemini-2.5-flash",      # Alternative (if available)
]

# ==================== AGENT CONFIG ====================

AGENT_CONFIG = {
    "max_depth": 10,              # Maximum navigation depth
    "max_items_per_folder": 50,   # Max items to list per folder
    "skip_c_drive_initially": True,  # Skip C: drive for speed
    "retry_attempts": 3,           # Retry attempts for API calls
    "retry_delay": 1.0,            # Delay between retries (seconds)
}

# ==================== LOGGING CONFIG ====================

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "simple": {
            "format": "%(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": str(LOGS_DIR / "agent.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
    },
    "loggers": {
        "FileSystemAgent": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}

# ==================== FILE SYSTEM CONFIG ====================

SYSTEM_CONFIG = {
    "setup_keywords": ['setup', 'install', 'installer', 'uninstall'],
    "executable_extensions": ['.exe', '.lnk', '.bat', '.msi', '.appx'],
    "other_file_extensions": ['.py', '.sln', '.jar', '.app', '.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.mp4', '.mp3', '.ppt', '.pptx', '.xls', '.xlsx'],
    "skip_folders": ['.', 'system volume information', '$recycle.bin', 'node_modules', '__pycache__'],
}

# ==================== VALIDATION ====================

def validate_config() -> bool:
    """Validate that all required configuration is present."""
    if LLM_PROVIDER == "ollama":
        if not OLLAMA_CONFIG.get("model_name"):
            raise ValueError("OLLAMA_MODEL not configured")
    elif LLM_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured. Please set it in .env file or environment variables.")
    else:
        raise ValueError(f"Invalid LLM_PROVIDER: {LLM_PROVIDER}. Must be 'ollama' or 'gemini'")
    return True

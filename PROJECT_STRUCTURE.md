# 📁 Project Structure

## Overview

This project follows a clean, modular architecture with clear separation of concerns.

```
Alquad/
│
├── src/                          # Source code
│   ├── __init__.py              # Package initialization
│   │
│   ├── agent/                   # Agent module
│   │   ├── __init__.py
│   │   └── agent.py             # Main SmartFileSystemAgent class
│   │
│   ├── config/                  # Configuration module
│   │   ├── __init__.py
│   │   └── settings.py         # All configuration settings
│   │
│   └── utils/                    # Utility modules
│       ├── __init__.py
│       ├── cache.py             # LRU cache implementation
│       ├── file_system.py       # File system operations
│       ├── gemini_client.py     # Gemini API client with retry logic
│       └── logger.py            # Logging setup
│
├── logs/                         # Log files (auto-created)
│   └── agent.log                # Application logs
│
├── main.py                       # Application entry point
├── requirements.txt             # Python dependencies
├── .env                          # Environment variables (create this)
├── .gitignore                   # Git ignore rules
├── README.md                     # Main documentation
├── SETUP.md                      # Quick setup guide
└── PROJECT_STRUCTURE.md          # This file
```

## Module Descriptions

### `src/agent/agent.py`
The core agent class that:
- Initializes Gemini client
- Manages navigation logic
- Handles user queries
- Coordinates file system operations

### `src/config/settings.py`
Centralized configuration:
- Gemini API settings
- Agent behavior settings
- Logging configuration
- File system settings

### `src/utils/file_system.py`
File system utilities:
- Partition detection
- Folder listing
- Path formatting
- File opening

### `src/utils/gemini_client.py`
Gemini API client:
- Model initialization with fallback
- Retry logic
- Error handling
- Safety settings

### `src/utils/cache.py`
Caching system:
- LRU cache for folder listings
- TTL (Time To Live) support
- Automatic expiration

### `src/utils/logger.py`
Logging setup:
- Console and file logging
- Log rotation
- Configurable levels

## Data Flow

```
User Query
    ↓
main.py
    ↓
SmartFileSystemAgent.find_and_open()
    ↓
_explore_partition() → list_folder_items() → GeminiClient
    ↓
_navigate_to_target() → (recursive)
    ↓
_open_path() → open_path()
    ↓
File/Folder Opened
```

## Key Features

### 1. Modular Design
- Each module has a single responsibility
- Easy to test and maintain
- Clear dependencies

### 2. Error Handling
- Comprehensive try-catch blocks
- Retry logic for API calls
- Graceful degradation

### 3. Performance
- Caching for frequently accessed paths
- Smart partition skipping
- Efficient folder traversal

### 4. Logging
- Detailed logs for debugging
- Log rotation to prevent disk fill
- Multiple log levels

### 5. Configuration
- Centralized settings
- Environment variable support
- Easy customization

## Adding New Features

### To add a new utility function:
1. Add it to `src/utils/` in the appropriate module
2. Export it in `src/utils/__init__.py`
3. Use it in `src/agent/agent.py`

### To modify configuration:
1. Edit `src/config/settings.py`
2. Add new settings to appropriate config dict
3. Use in agent or utilities

### To add new AI model support:
1. Modify `src/utils/gemini_client.py`
2. Add model name to `GEMINI_MODELS` in settings
3. Update initialization logic

## Best Practices

1. **Always use logging** instead of print for debugging
2. **Handle errors gracefully** with try-catch blocks
3. **Use type hints** for better code clarity
4. **Follow PEP 8** style guidelines
5. **Document functions** with docstrings
6. **Cache expensive operations** when possible

---

**This structure makes the codebase maintainable, scalable, and easy to understand!** 🎯

#  Alquad - Smart File System Agent

Intelligent file system navigator powered by **Ollama** or **Gemini 2.5 Flash** that helps you find and open files/folders on your Windows PC using natural language.

##  Features

-  **AI-Powered Navigation**: Uses Ollama or Gemini to intelligently navigate your file system
-  **Dual LLM Support**: Choose between local Ollama model or cloud-based Gemini 2.5 Flash
-  **Voice Input Support**: Speech-to-text using Whisper with Arabic (Egyptian) and English support
-  **Smart Search**: Finds files and folders by understanding natural language queries
-  **Google Search Integration**: Automatically detects web search requests and opens Google in your browser
-  **Fast & Efficient**: Skips system drives initially for faster results
-  **Multi-Partition Support**: Searches across all available disk partitions
-  **Intelligent Matching**: Understands context and matches folder names to your queries
-  **Caching System**: LRU cache for improved performance
-  **Retry Logic**: Automatic retries for API calls with error handling
-  **Comprehensive Logging**: Detailed logs for debugging and monitoring
-  **UI Components**: Optional folder and icon popup interfaces

##  Requirements

- Python 3.8+
- Windows OS (Linux/macOS support available)
- **For Ollama**: Ollama installed and running locally with model `deepseek-r1:7b-qwen-distill-q4_k_m`
- **For Gemini**: Google API Key (get it from [Google AI Studio](https://aistudio.google.com/app/apikey))
- **For Voice Input (Optional)**: 
  - PyAudio for microphone access
  - Faster-Whisper for speech recognition
  - Supports Arabic (Egyptian) and English

##  Installation

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install and start Ollama:**
   - Download from [ollama.ai](https://ollama.ai)
   - Install and start Ollama service
   - The model will be pulled automatically on first use

4. **Optional: Create a `.env` file for custom settings:**
   ```env
   LLM_PROVIDER=gemini  # or "ollama"
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=deepseek-r1:7b-qwen-distill-q4_k_m
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

5. **For Voice Input (Optional):**
   - Install PyAudio (may require additional system dependencies)
   - Voice input will be automatically enabled if dependencies are available
   - Supports Arabic (Egyptian) and English speech recognition

##  Usage

Run the main script:

```bash
python main.py
```

### Input Methods

**Text Input:**
- Simply type your query and press Enter

**Voice Input (if available):**
- Type `v` or `voice` when prompted
- Speak your query in Arabic (Egyptian) or English
- The system will transcribe and process your request

### Example Queries

**File/Folder Search:**
- `open league of legends`
- `find chrome`
- `launch steam`
- `open D: drive`
- `find photoshop`

**Google Web Search:**
- `search for python tutorials`
- `google machine learning`
- `what is artificial intelligence`
- `how to install python`
- `search about deep learning`

The agent will:
1. **Check for search requests**: If you're asking for a web search, it opens Google in your browser
2. **Search across partitions**: For file/folder queries, searches across your partitions
3. **Navigate intelligently**: Uses AI to navigate through folders
4. **Find the target**: Locates the target file/folder
5. **Open automatically**: Opens the found file/folder or search results

##  Project Structure

```
Alquad/
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   └── agent.py          # Main agent class
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py        # Configuration settings
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_system.py    # File system utilities
│   │   ├── gemini_client.py  # Gemini API client
│   │   ├── ollama_client.py  # Ollama API client
│   │   ├── google_search.py  # Google search detection & browser opening
│   │   ├── whisper_transcriber.py  # Voice input with Whisper
│   │   ├── cache.py          # LRU cache implementation
│   │   └── logger.py         # Logging setup
│   └── __init__.py
├── ui/                        # UI components (optional)
│   ├── folder_popup.py       # Folder selection popup
│   └── icon_popup.py         # Icon-based popup interface
├── logs/                      # Log files
├── main.py                    # Entry point
├── requirements.txt           # Dependencies
├── .env                       # Environment variables (create this)
├── .env.example               # Example environment file
├── .gitignore
└── README.md
```

##  Configuration

Edit `src/config/settings.py` to customize:

- `max_depth`: Maximum navigation depth (default: 10)
- `max_items_per_folder`: Max items to list per folder (default: 50)
- `skip_c_drive_initially`: Skip C: drive for speed (default: True)
- `retry_attempts`: API retry attempts (default: 3)
- `retry_delay`: Delay between retries in seconds (default: 1.0)

##  How It Works

1. **Query Processing**: User enters a natural language query
2. **Search Detection**: Agent uses LLM to detect if query is a web search request
   - If search detected → Opens Google search in browser
   - If file/folder search → Continues to file system search
3. **Partition Detection**: Agent identifies target partition (if specified)
4. **Smart Navigation**: LLM analyzes folder contents and decides next step
5. **Recursive Exploration**: Agent navigates through folders until target is found
6. **Auto-Open**: Opens the found file/folder automatically

##  Voice Input

The application supports voice input using Faster-Whisper:

- **Automatic Detection**: Voice input is enabled automatically if dependencies are installed
- **Multi-language**: Supports Arabic (Egyptian) and English
- **Code-switching**: Can handle mixed Arabic-English queries
- **Model**: Uses Whisper medium model with CPU optimization
- **Usage**: Type `v` or `voice` when prompted to use voice input

If voice dependencies are not available, the application will run in text-only mode.

##  Caching

The application includes an LRU (Least Recently Used) cache system:

- **Performance**: Caches frequently accessed data for faster responses
- **TTL**: Configurable time-to-live for cache entries
- **Automatic Expiration**: Expired entries are automatically removed

##  Logging

Logs are stored in `logs/agent.log` with rotation (10MB max, 5 backups).

Log levels:
- **DEBUG**: Detailed information for debugging
- **INFO**: General information about operations
- **WARNING**: Warning messages
- **ERROR**: Error messages


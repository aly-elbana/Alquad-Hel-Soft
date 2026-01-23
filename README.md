#  Alquad - Smart File System Agent

Intelligent file system navigator powered by **Ollama** or **Gemini 2.5 Flash** that helps you find and open files/folders on your Windows PC using natural language.

##  Features

-  **AI-Powered Navigation**: Uses Ollama or Gemini to intelligently navigate your file system
-  **Dual LLM Support**: Choose between local Ollama model or cloud-based Gemini 2.5 Flash
-  **Smart Search**: Finds files and folders by understanding natural language queries
-  **Fast & Efficient**: Skips system drives initially for faster results
-  **Multi-Partition Support**: Searches across all available disk partitions
-  **Intelligent Matching**: Understands context and matches folder names to your queries
-  **Retry Logic**: Automatic retries for API calls with error handling
-  **Comprehensive Logging**: Detailed logs for debugging and monitoring

##  Requirements

- Python 3.8+
- Windows OS (Linux/macOS support available)
- **For Ollama**: Ollama installed and running locally with model `deepseek-r1:7b-qwen-distill-q4_k_m`
- **For Gemini**: Google API Key (get it from [Google AI Studio](https://aistudio.google.com/app/apikey))

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
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=deepseek-r1:7b-qwen-distill-q4_k_m
   ```

##  Usage

Run the main script:

```bash
python main.py
```

### Example Queries

- `open league of legends`
- `find chrome`
- `launch steam`
- `open D: drive`
- `find photoshop`

The agent will:
1. Search across your partitions
2. Navigate through folders intelligently
3. Find the target file/folder
4. Open it automatically

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
│   │   └── logger.py         # Logging setup
│   └── __init__.py
├── logs/                      # Log files
├── main.py                    # Entry point
├── requirements.txt           # Dependencies
├── .env                       # Environment variables (create this)
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
2. **Partition Detection**: Agent identifies target partition (if specified)
3. **Smart Navigation**: Gemini analyzes folder contents and decides next step
4. **Recursive Exploration**: Agent navigates through folders until target is found
5. **Auto-Open**: Opens the found file/folder automatically

##  Logging

Logs are stored in `logs/agent.log` with rotation (10MB max, 5 backups).

Log levels:
- **DEBUG**: Detailed information for debugging
- **INFO**: General information about operations
- **WARNING**: Warning messages
- **ERROR**: Error messages

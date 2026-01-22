# 📝 Changelog

## Version 2.0.0 - Ollama Integration

### 🚀 Major Changes

1. **Switched to Ollama Local Model**
   - Replaced Gemini API with Ollama local model
   - Using `deepseek-r1:7b-qwen-distill-q4_k_m` model
   - No API keys or quotas needed
   - Fully local and private

2. **New Ollama Client**
   - Created `ollama_client.py` for local AI inference
   - Automatic connection testing
   - Model availability checking
   - Better error handling for local API

3. **Updated Dependencies**
   - Removed `google-generativeai`
   - Added `requests` for Ollama API calls
   - Simplified requirements

### ✨ Benefits

- ✅ No API quotas or rate limits
- ✅ Fully private (runs locally)
- ✅ No internet required after model download
- ✅ Free to use
- ✅ Faster response times (local inference)

### 📋 Migration Notes

- No `.env` file needed (optional for custom settings)
- Requires Ollama installed locally
- Model will be pulled automatically on first use

---

## Version 1.1.0 - Quota Handling & Direct Partition Support

### ✨ New Features

1. **Direct Partition Opening**
   - Now supports direct partition requests like "open D", "open D:", "D drive"
   - Automatically detects and opens partitions without AI processing
   - Faster response for simple partition requests

2. **Quota Error Handling**
   - Intelligent detection of API quota/rate limit errors
   - Automatic fallback to simple search mode when quota is exceeded
   - Clear error messages for users
   - No more repeated failed API calls

3. **Fallback Mode**
   - Simple keyword-based search when AI is unavailable
   - Works without API calls
   - Still functional for basic file/folder finding

### 🐛 Bug Fixes

- Fixed issue where "open D" was treated as a search query instead of direct partition request
- Improved error messages for quota exceeded scenarios
- Better handling of API failures

### 🔧 Improvements

- Reduced unnecessary API calls
- Faster response for partition requests
- Better user experience with clear error messages
- More resilient to API issues

### 📋 Usage Examples

**Direct Partition:**
```
📂 Request: open D
📂 Opening partition: D:\
✅ Opened successfully!
```

**With Quota Error:**
```
⚠️  API Quota Exceeded - switching to fallback mode
   📂 Searching D:\...
   ✅ Found: D:\Games\League of Legends
```

---

## Version 1.0.0 - Initial Release

- AI-powered file system navigation
- Gemini 2.5 Flash integration
- Multi-partition support
- Intelligent folder matching
- Caching system
- Comprehensive logging

# 🚀 Quick Setup Guide

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Install Ollama

1. Download Ollama from [ollama.ai](https://ollama.ai)
2. Install Ollama on your system
3. Start Ollama service (it usually starts automatically)
4. Verify it's running by opening: http://localhost:11434

## Step 3: Pull the Model (Optional)

The model will be pulled automatically, but you can also pull it manually:

```bash
ollama pull deepseek-r1:7b-qwen-distill-q4_k_m
```

## Step 4: Optional .env File

Create a file named `.env` in the root directory (`e:\Alquad\.env`) for custom settings:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:7b-qwen-distill-q4_k_m
```

## Step 5: Run the Application

```bash
python main.py
```

## ✅ You're Ready!

The agent will:
- Detect all available partitions automatically
- Search intelligently using Gemini AI
- Open files/folders for you

## 🎯 Example Usage

```
📂 Request: open league of legends
🔍 Searching for: 'open league of legends'...
   📂 Checking D:\...
   ✅ Exploring: Games...
   ✅ Found: D:\Games\League of Legends
🚀 Opening...
✅ Opened successfully!
```

## ❓ Troubleshooting

**"Cannot connect to Ollama"**
- Make sure Ollama is installed and running
- Start Ollama: `ollama serve` or restart the Ollama service
- Check if Ollama is running: Open http://localhost:11434 in browser

**"Model not found"**
- Pull the model: `ollama pull deepseek-r1:7b-qwen-distill-q4_k_m`
- Check available models: `ollama list`
- Verify model name in settings

**Nothing found?**
- Try more specific queries
- Check spelling
- Make sure the item exists

---

Happy searching! 🎉

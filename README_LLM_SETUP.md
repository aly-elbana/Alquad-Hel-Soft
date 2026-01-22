# LLM Provider Setup Guide

يمكنك اختيار استخدام النموذج المحلي (Ollama) أو Gemini 2.5 Flash.

## الطريقة 1: استخدام Ollama (النموذج المحلي)

1. تأكد من تثبيت وتشغيل Ollama:
   ```bash
   # تحميل النموذج
   ollama pull deepseek-r1:7b-qwen-distill-q4_k_m
   ```

2. في ملف `.env` أو متغيرات البيئة:
   ```env
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=deepseek-r1:7b-qwen-distill-q4_k_m
   ```

## الطريقة 2: استخدام Gemini 2.5 Flash

1. احصل على API Key من Google AI Studio:
   - اذهب إلى: https://aistudio.google.com/app/apikey
   - أنشئ API Key جديد

2. في ملف `.env` أو متغيرات البيئة:
   ```env
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your_api_key_here
   ```

3. تثبيت المكتبة المطلوبة:
   ```bash
   pip install google-generativeai>=0.3.0
   ```

## ملاحظات

- **Ollama**: مجاني، يعمل محلياً، لا يحتاج إنترنت (بعد تحميل النموذج)
- **Gemini**: يحتاج إنترنت و API Key، قد يكون أسرع وأكثر دقة

## التبديل بين النماذج

ببساطة غيّر `LLM_PROVIDER` في ملف `.env`:
- `LLM_PROVIDER=ollama` للاستخدام المحلي
- `LLM_PROVIDER=gemini` لاستخدام Gemini

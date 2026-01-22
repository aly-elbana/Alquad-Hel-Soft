"""
Whisper-based speech recognition for voice input.
"""

import os
import speech_recognition as sr
from faster_whisper import WhisperModel
import logging
import time

logger = logging.getLogger("FileSystemAgent")

class WhisperTranscriber:
    """Speech-to-text using Faster-Whisper model."""
    
    def __init__(self, model_size="medium", device="auto", compute_type="auto"):
        """
        Initialize Whisper transcriber.
        
        Args:
            model_size: tiny, base, small, medium, large-v3 (default: small)
            device: 'cuda' (GPU) or 'cpu' or 'auto'
            compute_type: 'float16' for GPU, 'int8' for CPU, 'auto' for auto-detect
        """
        logger.info(f"🚀 Loading Whisper Model ({model_size}) on {device}...")
        start_time = time.time()
        
        try:
            self.model = WhisperModel(
                model_size, 
                device=device, 
                compute_type=compute_type
            )
            logger.info(f"✅ Model loaded successfully in {time.time() - start_time:.2f}s")
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise e

        self.recognizer = sr.Recognizer()

    def listen_and_transcribe(self):
        """
        Record audio and transcribe using Whisper.
        
        Returns:
            Transcribed text or None if no speech detected
        """
        with sr.Microphone() as source:
            print("\n🎤 (Whisper): I'm listening... speak now!")
            
            # Adjust for ambient noise
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                # Record audio
                audio_data = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                print("⏳ Processing audio...")

                # Save audio temporarily for Whisper
                temp_wav = "temp_command.wav"
                with open(temp_wav, "wb") as f:
                    f.write(audio_data.get_wav_data())

                # Transcribe using Whisper with support for Arabic (Egyptian) and English
                # Strategy: Use auto-detect first for better code-switching support
                # Whisper handles Arabic dialects (including Egyptian) well with auto-detect
                segments, info = self.model.transcribe(
                    temp_wav, 
                    beam_size=5,
                    language=None,  # Auto-detect (best for code-switching Arabic/English)
                    vad_filter=True,  # Filter silence for speed
                    initial_prompt="This is a conversation in Arabic (Egyptian dialect) and English. The user may mix both languages. Transcribe exactly as spoken, preserving both languages."
                )
                
                # If auto-detect gives low confidence, try specific languages
                if info.language_probability < 0.6:
                    # Check if detected language is Arabic or English
                    if info.language == "ar":
                        # Already Arabic, but low confidence - might be mixed
                        logger.info(f"⚠️ Low confidence for Arabic ({info.language_probability:.2f}), might be mixed speech")
                    elif info.language == "en":
                        # English detected, but low confidence - might be mixed
                        logger.info(f"⚠️ Low confidence for English ({info.language_probability:.2f}), might be mixed speech")
                    else:
                        # Unknown language, try Arabic first (most common for Egyptian users)
                        logger.info(f"⚠️ Unknown language detected ({info.language}), trying Arabic...")
                        segments, info = self.model.transcribe(
                            temp_wav, 
                            beam_size=5,
                            language="ar",  # Arabic (supports Egyptian dialect)
                            vad_filter=True,
                            initial_prompt="This is Arabic (Egyptian dialect) speech, possibly mixed with English words."
                        )

                # Combine segments into full text
                full_text = " ".join([segment.text for segment in segments]).strip()
                
                # Clean up temp file
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)

                if full_text:
                    # Map language codes to readable names
                    lang_names = {
                        "ar": "Arabic (Egyptian) 🇪🇬",
                        "en": "English 🇬🇧",
                    }
                    lang_name = lang_names.get(info.language, f"{info.language}")
                    
                    # Check if text contains both Arabic and English characters (code-switching)
                    has_arabic = any('\u0600' <= char <= '\u06FF' for char in full_text)
                    has_english = any(char.isalpha() and ord(char) < 128 for char in full_text)
                    
                    if has_arabic and has_english:
                        lang_name = "Mixed (Arabic/English) 🗣️"
                        logger.info(f"🗣️ Detected: {lang_name} - Code-switching detected!")
                    else:
                        logger.info(f"🗣️ Detected Language: {lang_name} (Confidence: {info.language_probability:.2f})")
                    
                    print(f"📝 You said: {full_text}")
                    return full_text
                else:
                    return None

            except sr.WaitTimeoutError:
                print("⚠️ Timeout. No speech detected.")
                return None
            except Exception as e:
                logger.error(f"Error during transcription: {e}")
                return None

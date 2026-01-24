import os
import time
import tempfile
import logging
import torch
import speech_recognition as sr
from faster_whisper import WhisperModel

# =========================
# Logger Setup
# =========================
logger = logging.getLogger("WhisperTranscriber")
logger.setLevel(logging.INFO)


# =========================
# Whisper Transcriber Class
# =========================
class WhisperTranscriber:
    """
    Speech-to-text using Faster-Whisper with:
    - Auto language detection
    - Arabic (Egyptian) + English code-switching
    - Optimized temp file handling
    - Controlled recording cutoff (20s)
    """

    # -------------------------
    # Constructor
    # -------------------------
    def __init__(
        self,
        model_size: str | None = None,
        device: str = "auto",
        compute_type: str = "auto",
        beam_size: int = 3,
        verbose: bool = True,
    ):
        """
        Initialize the Whisper transcriber.
        """

        self.verbose = verbose
        self.beam_size = beam_size

        # -------------------------
        # Auto Model Selection
        # -------------------------
        use_cuda = torch.cuda.is_available() and device != "cpu"
        if model_size is None:
            model_size = "medium" if use_cuda else "small"

        # -------------------------
        # Load Whisper Model (Timed)
        # -------------------------
        logger.info(
            f"Loading Whisper model [{model_size}] on [{device}]..."
        )
        load_start = time.time()

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )

        self.model_load_time = time.time() - load_start
        logger.info(
            f"Whisper model loaded in {self.model_load_time:.2f}s"
        )

        # -------------------------
        # SpeechRecognition Setup
        # -------------------------
        self.recognizer = sr.Recognizer()

        # Important tuning to avoid early cutoff
        self.recognizer.pause_threshold = 1.5
        self.recognizer.non_speaking_duration = 1
        self.recognizer.dynamic_energy_threshold = True

        self._calibrated = False

        # -------------------------
        # Metrics (agent-readable)
        # -------------------------
        self.last_transcribe_time = None
        self.last_fallback_time = None
        self.last_language = None
        self.last_language_confidence = None


    # =========================
    # Private Helpers
    # =========================
    def _calibrate_microphone(self, source):
        """Calibrate microphone once for ambient noise."""
        if not self._calibrated:
            logger.info("Calibrating microphone for ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self._calibrated = True


    def _save_temp_wav(self, audio_data) -> str:
        """Save audio to a safe temporary WAV file."""
        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        ) as tmp:
            tmp.write(audio_data.get_wav_data())
            return tmp.name


    def _detect_code_switch(self, text: str) -> bool:
        """Detect Arabic + English mixed speech."""
        has_arabic = any('\u0600' <= c <= '\u06FF' for c in text)
        has_english = any(c.isalpha() and ord(c) < 128 for c in text)
        return has_arabic and has_english


    # =========================
    # Public API
    # =========================
    def listen_and_transcribe(self) -> str | None:
        """
        Listen from microphone and transcribe speech.

        Hard cutoff at 20 seconds.
        """

        # -------------------------
        # Record Audio
        # -------------------------
        with sr.Microphone() as source:
            if self.verbose:
                print("\nListening...")

            self._calibrate_microphone(source)

            try:
                audio_data = self.recognizer.listen(
                    source,
                    timeout=10,
                    phrase_time_limit=20
                )
            except sr.WaitTimeoutError:
                logger.warning("No speech detected (timeout)")
                return None

        if self.verbose:
            print("Transcribing...")

        temp_wav_path = self._save_temp_wav(audio_data)

        try:
            # -------------------------
            # Primary Transcription
            # -------------------------
            start_transcribe = time.time()

            segments, info = self.model.transcribe(
                temp_wav_path,
                beam_size=self.beam_size,
                language=None,
                vad_filter=True,
                initial_prompt=(
                    "This is a conversation in Arabic (Egyptian dialect) "
                    "and English. The speaker may mix both languages. "
                    "Transcribe exactly as spoken."
                )
            )

            self.last_transcribe_time = time.time() - start_transcribe
            logger.info(
                f"Transcription took {self.last_transcribe_time:.2f}s"
            )

            # -------------------------
            # Low Confidence Fallback
            # -------------------------
            if info.language_probability < 0.6:
                logger.info(
                    f"Low confidence "
                    f"({info.language_probability:.2f}) "
                    f"for [{info.language}], falling back to Arabic"
                )

                fallback_start = time.time()

                segments, info = self.model.transcribe(
                    temp_wav_path,
                    beam_size=self.beam_size,
                    language="ar",
                    vad_filter=True,
                    initial_prompt=(
                        "This is Arabic (Egyptian dialect) speech, "
                        "possibly mixed with English words."
                    )
                )

                self.last_fallback_time = time.time() - fallback_start
                logger.info(
                    f"Fallback transcription took "
                    f"{self.last_fallback_time:.2f}s"
                )

            # -------------------------
            # Combine Segments
            # -------------------------
            full_text = " ".join(
                s.text.strip() for s in segments
            ).strip()

            if not full_text:
                return None

            # -------------------------
            # Language Reporting
            # -------------------------
            self.last_language = info.language
            self.last_language_confidence = info.language_probability

            if self._detect_code_switch(full_text):
                logger.info("Detected mixed Arabic / English speech")
            else:
                logger.info(
                    f"Detected language: {info.language} "
                    f"(confidence: {info.language_probability:.2f})"
                )

            if self.verbose:
                print(f"You said: {full_text}")

            return full_text

        except Exception:
            logger.exception("Transcription failed")
            return None

        finally:
            # -------------------------
            # Cleanup
            # -------------------------
            if os.path.exists(temp_wav_path):
                os.remove(temp_wav_path)

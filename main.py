import sys
from pathlib import Path
from src.utils.logger import setup_logger
from src.agent.agent import SmartFileSystemAgent
from src.config.settings import LLM_PROVIDER, OLLAMA_CONFIG, GEMINI_MODELS

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


# =========================
# Helper Functions
# =========================
def print_banner(agent, use_voice: bool):
    """
    Print application banner and usage info.
    """

    print("\n" + "=" * 60)
    print("Alquad - Smart File System Agent")

    if LLM_PROVIDER == "ollama":
        print(f"Powered by Ollama ({OLLAMA_CONFIG['model_name']})")
    elif LLM_PROVIDER == "gemini":
        model = GEMINI_MODELS[0] if GEMINI_MODELS else "default"
        print(f"Powered by Gemini ({model})")

    print("=" * 60)

    print(f"\nAvailable Partitions: {', '.join(agent.partitions)}")

    print("\nExamples:")
    print(" - open my documents")
    print(" - find projects folder")
    print(" - launch application name")
    print(" - open D drive")

    if use_voice:
        print("\nVoice Commands:")
        print(" - Press Enter for text input")
        print(" - Type 'v' or 'voice' for voice input")

    print("\nType 'q' to quit\n")


def load_whisper(logger):
    """
    Lazy-load Whisper transcriber.
    Returns (whisper_instance | None)
    """

    try:
        from src.utils.whisper_transcriber import WhisperTranscriber

        whisper = WhisperTranscriber(
            model_size="medium", device="cpu", compute_type="int8", beam_size=3
        )

        print("\nVoice input enabled (Whisper)")
        print("Supports: Arabic (Egyptian), English, Mixed")

        return whisper

    except Exception as e:
        logger.warning(f"Voice input not available: {e}")
        print("\nVoice input disabled (text only)")
        return None


# =========================
# Main Application Loop
# =========================
def main():
    """
    Main entry point.
    """

    logger = setup_logger()

    try:
        # -------------------------
        # Initialize Agent
        # -------------------------
        agent = SmartFileSystemAgent()

        # -------------------------
        # Try Loading Voice Support
        # -------------------------
        whisper = load_whisper(logger)
        use_voice = whisper is not None

        # -------------------------
        # Print UI Banner
        # -------------------------
        print_banner(agent, use_voice)

        # -------------------------
        # Interactive Loop
        # -------------------------
        while True:
            try:
                # =====================
                # Input Selection
                # =====================
                if use_voice:
                    choice = (
                        input("Input (Enter=text, 'v'=voice, 'q'=quit): ")
                        .strip()
                        .lower()
                    )

                    if choice == "q":
                        break

                    if choice in ("v", "voice"):
                        query = whisper.listen_and_transcribe()
                        if not query:
                            continue
                    else:
                        query = input("Request: ").strip()
                else:
                    query = input("Request: ").strip()

                # =====================
                # Exit Conditions
                # =====================
                if not query:
                    continue

                if query.lower() == "q":
                    break

                # =====================
                # Execute Agent Action
                # =====================
                agent.find_and_open(query)
                print()

            except KeyboardInterrupt:
                print("\nGoodbye.")
                break

            except Exception as e:
                logger.error("Error in main loop", exc_info=True)
                print(f"Error: {e}")

        print("Goodbye.")

    except Exception as e:
        logger.critical("Fatal error", exc_info=True)
        print(f"Fatal error: {e}")
        sys.exit(1)


# =========================
# Entry Point Guard
# =========================
if __name__ == "__main__":
    main()

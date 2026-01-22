"""
Main entry point for Alquad - Smart File System Agent
"""

import sys
from pathlib import Path

# Add src to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import setup_logger
from src.agent.agent import SmartFileSystemAgent

def main():
    """Main entry point."""
    logger = setup_logger()
    
    try:
        agent = SmartFileSystemAgent()
        
        print("\n" + "="*60)
        print("🤖 Alquad - Smart File System Agent")
        # Get provider info
        from src.config.settings import LLM_PROVIDER, OLLAMA_CONFIG, GEMINI_MODELS
        if LLM_PROVIDER == "ollama":
            print(f"   Powered by Ollama ({OLLAMA_CONFIG['model_name']})")
        elif LLM_PROVIDER == "gemini":
            print(f"   Powered by Gemini ({GEMINI_MODELS[0] if GEMINI_MODELS else 'default'})")
        print("="*60)
        print(f"\n📂 Available Partitions: {', '.join(agent.partitions)}")
        print("\n💡 Examples:")
        print("   - 'open my documents'")
        print("   - 'find projects folder'")
        print("   - 'launch application name'")
        print("   - 'open D: drive'")
        print("\nType 'q' to quit\n")
        
        while True:
            try:
                query = input("📂 Request: ").strip()
                if not query:
                    continue
                if query.lower() == 'q':
                    print("👋 Goodbye!")
                    break
                
                agent.find_and_open(query)
                print()  # Empty line for readability
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                print(f"❌ Error: {e}")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

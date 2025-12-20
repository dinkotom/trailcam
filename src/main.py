import sys
import os
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import processor, logger

def main():
    logger.setup_logging()
    log = logging.getLogger("main")
    
    # Ensure data dirs exist
    os.makedirs('data/photos', exist_ok=True)
    
    log.info("Starting processing...")
    try:
        processor.process_emails()
    except Exception as e:
        log.critical(f"Unhandled exception: {e}", exc_info=True)
        
    log.info("Done.")

if __name__ == "__main__":
    main()

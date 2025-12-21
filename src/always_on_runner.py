import time
import datetime
import sys
import os
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import processor, logger

def run_forever():
    """
    Runs the processor every 5 minutes indefinitely.
    Designed to be run by a PythonAnywhere 'Always-on' task.
    """
    logger.setup_logging()
    log = logging.getLogger("always_on_runner")
    
    interval = 300 # 5 minutes

    log.info(f"Starting Always-on runner at {datetime.datetime.now()}")

    while True:
        try:
            log.info(f"--- Check cycle at {datetime.datetime.now()} ---")
            processor.process_emails()
        except Exception as e:
            log.critical(f"CRITICAL ERROR in loop: {e}", exc_info=True)
            # Sleep a bit even on error to avoid rapid-fire processing if something breaks
            time.sleep(60)
            continue
        
        log.info(f"Sleeping for {interval} seconds...")
        time.sleep(interval)

if __name__ == "__main__":
    run_forever()

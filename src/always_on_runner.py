import time
import datetime
import sys
import os

# Ensure src is in python path if running from project root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src import processor

def run_forever():
    """
    Runs the processor every 5 minutes indefinitely.
    Designed to be run by a PythonAnywhere 'Always-on' task.
    """
    interval = 300 # 5 minutes

    print(f"Starting Always-on runner at {datetime.datetime.now()}")

    while True:
        try:
            print(f"\n--- Check cycle at {datetime.datetime.now()} ---")
            processor.process_emails()
        except Exception as e:
            print(f"CRITICAL ERROR in loop: {e}")
            # Sleep a bit even on error to avoid rapid-fire processing if something breaks
            time.sleep(60)
            continue
        
        print(f"Sleeping for {interval} seconds...")
        time.sleep(interval)

if __name__ == "__main__":
    run_forever()

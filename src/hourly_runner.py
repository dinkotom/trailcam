import time
import datetime
import sys
import os

# Ensure src is in python path if running from project root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src import processor

def run_hourly_loop():
    """
    Runs the processor every 5 minutes for about 55 minutes.
    Designed to be run by a PythonAnywhere 'Hourly' scheduled task.
    """
    start_time = time.time()
    # Run for 55 minutes (leaving 5 min buffer before the next hourly task starts)
    duration = 55 * 60 
    interval = 300 # 5 minutes

    print(f"Starting hourly runner at {datetime.datetime.now()}")

    while time.time() - start_time < duration:
        loop_start = time.time()
        print(f"\n--- Check cycle at {datetime.datetime.now()} ---")
        
        try:
            processor.process_emails()
        except Exception as e:
            print(f"CRITICAL ERROR in loop: {e}")
        
        # Calculate time to sleep to maintain 5 minute cadence
        elapsed = time.time() - loop_start
        sleep_time = max(0, interval - elapsed)
        
        # Check if sleeping would push us over the limit significantly
        if (time.time() - start_time) + sleep_time > duration + 60:
            print("Time limit approaching, exiting loop.")
            break
            
        print(f"Sleeping for {int(sleep_time)} seconds...")
        time.sleep(sleep_time)

    print("Hourly run finished.")

if __name__ == "__main__":
    run_hourly_loop()

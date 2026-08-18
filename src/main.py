import sys
import os
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import processor, logger
from src.config import Config

def main():
    logger.setup_logging()
    log = logging.getLogger("main")

    # Ensure temp dir exists (absolute, so Scheduled Tasks / CI cwd does not matter)
    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    
    log.info("Starting processing...")
    try:
        processor.process_emails()
    except Exception as e:
        log.critical(f"Critical execution error: {e}", exc_info=True)
        # Attempt to send alert email
        try:
            from src import email_ops
            email_ops.send_alert_email("Execution Failed", f"The trailcam processor crashed.\n\nError:\n{str(e)}")
        except Exception as mail_e:
            log.critical(f"Failed to send alert email: {mail_e}")

        # Non-zero exit so the scheduler (GitHub Actions) reports the run as failed
        sys.exit(1)

    log.info("Done.")

if __name__ == "__main__":
    main()

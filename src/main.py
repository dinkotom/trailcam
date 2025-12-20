import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import processor, config

def main():
    # Ensure dirs exist
    os.makedirs(config.Config.TEMP_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(config.Config.DB_PATH), exist_ok=True)
    
    # Run
    processor.process_emails()

if __name__ == "__main__":
    main()

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from src.config import Config

def setup_logging():
    """
    Configures logging for the application.
    - Output: Console (stdout) and File (data/trailcam.log)
    - Level: INFO (or DEBUG if configured)
    - Format: [Time] [Level] [Module] Message
    """
    
    # Create logs dir if not exists (usually root/data)
    log_dir = os.path.dirname(Config.DB_PATH) # reuse data dir logic
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, 'trailcam.log')
    
    # Format
    # 2023-12-20 17:45:01,123 [INFO] [processor] Message...
    log_format = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
    
    # Root logger
    level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates on re-import/re-run
    if root_logger.handlers:
        root_logger.handlers.clear()
        
    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # 2. File Handler (Rotating)
    # 5 MB per file, keep 3 backups
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
    
    # Example debug logging control
    # logging.getLogger("googleapiclient.discovery").setLevel(logging.WARNING) # Noise reduction
    
    # Noise reduction: the Google client logs every discovery/HTTP detail at INFO
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

    logging.info(f"Logging initialized ({Config.LOG_LEVEL}). Writing to: {log_file}")

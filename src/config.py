import os
from dotenv import load_dotenv

# Load .env (if present)
load_dotenv()

class Config:
    # Local Temp Dir
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TEMP_DIR = os.path.join(BASE_DIR, 'data', 'photos')
    DB_PATH = os.path.join(BASE_DIR, 'data', 'processed.db')

    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASS = os.getenv('EMAIL_PASS')
    IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.seznam.cz')
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.seznam.cz')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'tomas.dinkov@gmail.com')
    
    # Google Drive Auth
    GOOGLE_SA_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', os.path.join(BASE_DIR, 'service_account.json'))
    GOOGLE_TOKEN_FILE = os.getenv('GOOGLE_TOKEN_FILE', os.path.join(BASE_DIR, 'token.json'))
    # Contents of token.json passed as an env var (used by CI, where no files are uploaded)
    GOOGLE_TOKEN_JSON = os.getenv('GOOGLE_TOKEN_JSON')
    
    # Target Root Folder ID (optional, if you want to enforce a root)
    TARGET_DRIVE_FOLDER_ID = os.getenv('TARGET_DRIVE_FOLDER_ID')

    @classmethod
    def validate(cls):
        if not cls.EMAIL_USER or not cls.EMAIL_PASS:
            raise ValueError("EMAIL_USER and EMAIL_PASS must be set in .env or environment")
            
    # How many days back to look for emails
    EMAIL_LOOKBACK_DAYS = int(os.getenv('EMAIL_LOOKBACK_DAYS', 2))

    # Where the processed-Message-ID history lives: 'sqlite' (local data/processed.db)
    # or 'drive' (JSON file in TARGET_DRIVE_FOLDER_ID, for ephemeral runners like CI)
    STATE_BACKEND = os.getenv('STATE_BACKEND', 'sqlite').lower()

    # Console/file log level. Runs on a public repo keep this at INFO or higher;
    # DEBUG also prints email subjects.
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

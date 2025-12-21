# Trailcam Email Processor

This application automatically fetches trail camera photos from emails, renames them with a clear "Service Day" structure (handling the 15:00 CET rollover), and uploads them to Google Drive.

## Features
- **Smart Date Logic**: Emails before 15:00 CET count towards the *previous* day.
- **Location Mapping**: Auto-detects location from Subject (e.g. "NOVA" -> "Nová").
- **Google Drive Upload**: Organizes photos into folders `YYYY-MM-DD` on Drive.
- **Efficient Tracking**: Maintains a lightweight history to avoid re-downloading today's photos.
- **Cleanup**: Auto-removes tracking history older than 60 days.
- **Comprehensive Logging**: Detailed logs to Console and `data/trailcam.log` (rotating).

## Setup Instructions

### 1. Google Cloud Credentials
This app uses **OAuth2 User Credentials** (preferred) or Service Account.
1. Download your `client_secret_....json` from Google Cloud Console (OAuth Client ID - Desktop App).
2. Save it as `credentials.json` in the project root.
3. Run `python src/auth_drive.py` locally to generate `token.json`.
4. Upload `token.json` to your deployment server.

### 2. Environment Configuration
Create a `.env` file in the project root:

```ini
EMAIL_USER=your_email@seznam.cz
EMAIL_PASS=your_password
IMAP_SERVER=imap.seznam.cz

# Path to the JSON key you downloaded
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

# (Optional) The ID of the Drive folder you shared. 
# If omitted, it may upload to the Service Account's root, which is hard to access.
TARGET_DRIVE_FOLDER_ID=1x2y3z...
```

### 3. Running Locally
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 src/main.py
```

### 4. Running on PythonAnywhere
See the dedicated guide: [PythonAnywhere Deployment](pythonanywhere_deployment.md).

## Troubleshooting
### Common Issues
1. **Invalid Scope**: If you see `invalid_scope`, ensure your `token.json` matches the scopes in `src/drive_ops.py`.
2. **No valid credentials found**: 
   - Ensure `token.json` is uploaded.
   - The code uses absolute paths (`src/config.py`) to find credentials even when run from Scheduled Tasks.

## Verification Results
- **Date Logic**: Verified that 14:00 CET maps to the *previous* day and 15:00 CET maps to the *current* day.
- **Database**: Verified that the app remembers processed emails during the session but discards very old history (2+ days) to keep the DB small.

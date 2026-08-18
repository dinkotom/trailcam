# Trailcam Email Processor

This application automatically fetches trail camera photos from emails, renames them with a clear "Service Day" structure (handling the 12:00 CET rollover), and uploads them to Google Drive.

## Features
- **Smart Date Logic**: Emails before 12:00 (Noon) count towards the *previous* day.
- **Location Mapping**: Auto-detects location from Subject (e.g. "NOVA" -> "Nová").
- **Organized Storage**: 
  - Drive Folder Structure: `YYYY-MM-DD` / `{Location}` / `Photo.jpg`
  - Filename Format: `YYYY-MM-DD HH:MM {Location}.jpg` (Preserves original timestamp)
- **Efficient Tracking**: Only message headers are downloaded first; attachments are fetched
  only for messages that are new and from a known location.
- **Cleanup**: Auto-removes tracking history older than 60 days.
- **Comprehensive Logging**: Detailed logs to Console and `data/trailcam.log` (rotating).

## Setup Instructions

### 1. Google Cloud Credentials
This app uses **OAuth2 User Credentials** (preferred) or Service Account.
1. Download your `client_secret_....json` from Google Cloud Console (OAuth Client ID - Desktop App).
2. Save it as `credentials.json` in the project root.
3. Run `python src/auth_drive.py` locally to generate `token.json`.
4. For deployment, put its contents into the `GOOGLE_TOKEN_JSON` secret (see [Deployment](deployment.md)).

### 2. Environment Configuration
Create a `.env` file in the project root:

```ini
EMAIL_USER=your_email@seznam.cz
EMAIL_PASS=your_password
IMAP_SERVER=imap.seznam.cz
SMTP_SERVER=smtp.seznam.cz
ADMIN_EMAIL=you@example.com

# Path to the JSON key you downloaded
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

# (Optional) The ID of the Drive folder you shared. 
# If omitted, it may upload to the Service Account's root, which is hard to access.
TARGET_DRIVE_FOLDER_ID=1x2y3z...

# Where the processed-message history lives:
#   sqlite = local data/processed.db (default, for persistent machines)
#   drive  = JSON file in TARGET_DRIVE_FOLDER_ID (for ephemeral runners like CI)
STATE_BACKEND=sqlite

# INFO (default) / WARNING / DEBUG. DEBUG also logs email subjects.
LOG_LEVEL=INFO
```

### 3. Running Locally
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 src/main.py
```

### 4. Running in production
The processor runs as a scheduled **GitHub Actions** workflow (every ~20 min), with the
processed-message history stored on Google Drive. See the dedicated guide:
[Deployment](deployment.md).

## Troubleshooting
### Common Issues
1. **Invalid Scope**: user tokens are loaded *without* passing scopes on purpose, so the token is
   reused with the scopes it was issued for. If you re-add scopes and they differ, Google returns
   `invalid_scope` on refresh.
2. **No valid credentials found**: 
   - Locally: ensure `token.json` exists. In CI: ensure the `GOOGLE_TOKEN_JSON` secret is set.
   - The code uses absolute paths (`src/config.py`) to find credentials regardless of the working directory.
3. **`invalid_grant` after 7 days**: the Google Cloud OAuth app is in "Testing" status, which
   expires refresh tokens weekly. Switch it to "Production" (no verification needed for personal use).

## Verification Results
- **Date Logic**: Verified that 11:59 CET maps to the *previous* day and 12:00 CET maps to the *current* day.
- **History**: Verified that processed messages are remembered across runs (both backends) and
  that entries older than 60 days are pruned.
- **Tests**: `python -m unittest discover -s tests`

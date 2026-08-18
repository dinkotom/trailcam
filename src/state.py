import datetime
import json
import logging

from src import db
from src.config import Config

STATE_FILENAME = "_trailcam_state.json"
RETENTION_DAYS = 60


class SqliteState:
    """Local state backend: data/processed.db (used when running on a persistent machine)."""

    name = "sqlite"

    def open(self):
        db.init_db()

    def is_processed(self, message_id):
        return db.is_processed(message_id)

    def mark_processed(self, message_id):
        db.mark_processed(message_id)

    def flush(self):
        pass


class DriveJsonState:
    """
    State backend that keeps the processed-Message-ID list on Google Drive
    (`_trailcam_state.json` in the root target folder).

    This makes the pipeline stateless from the runner's point of view, so it can
    run on ephemeral hosts (GitHub Actions) without re-uploading old photos.
    """

    name = "drive"

    def __init__(self, service, parent_id):
        self.service = service
        self.parent_id = parent_id
        self.file_id = None
        self.processed = {}
        self.dirty = False
        self.log = logging.getLogger("state")

    def _find_file(self):
        query = (
            f"name='{STATE_FILENAME}' and '{self.parent_id}' in parents "
            "and trashed=false"
        )
        result = self.service.files().list(
            q=query, spaces='drive', fields='files(id)').execute()
        files = result.get('files', [])
        return files[0]['id'] if files else None

    def open(self):
        self.file_id = self._find_file()
        if not self.file_id:
            self.log.info("No state file on Drive yet, starting with empty history.")
            return

        raw = self.service.files().get_media(fileId=self.file_id).execute()
        try:
            data = json.loads(raw.decode('utf-8'))
            self.processed = data.get('processed', {})
        except (ValueError, UnicodeDecodeError) as e:
            # Never re-upload everything just because the state file is damaged;
            # a corrupt file is dropped, and the next flush rewrites it.
            self.log.error(f"State file unreadable ({e}), starting fresh.")
            self.processed = {}

        before = len(self.processed)
        self._prune()
        self.log.info(
            f"State loaded: {len(self.processed)} processed messages "
            f"({before - len(self.processed)} pruned)."
        )

    def _prune(self):
        cutoff = (datetime.datetime.now(datetime.timezone.utc)
                  - datetime.timedelta(days=RETENTION_DAYS)).isoformat()
        kept = {k: v for k, v in self.processed.items() if v >= cutoff}
        if len(kept) != len(self.processed):
            self.processed = kept
            self.dirty = True

    def is_processed(self, message_id):
        return message_id in self.processed

    def mark_processed(self, message_id):
        self.processed[message_id] = datetime.datetime.now(
            datetime.timezone.utc).isoformat()
        self.dirty = True

    def flush(self):
        if not self.dirty:
            return

        from googleapiclient.http import MediaInMemoryUpload

        body = json.dumps({'processed': self.processed}).encode('utf-8')
        media = MediaInMemoryUpload(body, mimetype='application/json')

        if self.file_id:
            self.service.files().update(
                fileId=self.file_id, media_body=media).execute()
        else:
            metadata = {'name': STATE_FILENAME, 'parents': [self.parent_id]}
            created = self.service.files().create(
                body=metadata, media_body=media, fields='id').execute()
            self.file_id = created['id']

        self.dirty = False


def open_state(drive_service):
    """Returns an opened state backend based on Config.STATE_BACKEND."""
    log = logging.getLogger("state")

    if Config.STATE_BACKEND == 'drive':
        if not Config.TARGET_DRIVE_FOLDER_ID:
            raise ValueError(
                "STATE_BACKEND=drive requires TARGET_DRIVE_FOLDER_ID to be set")
        backend = DriveJsonState(drive_service, Config.TARGET_DRIVE_FOLDER_ID)
    else:
        backend = SqliteState()

    log.info(f"Using '{backend.name}' state backend.")
    backend.open()
    return backend

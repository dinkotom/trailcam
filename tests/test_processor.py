"""
End-to-end tests of the processing loop against a fake Drive and a fake IMAP server.

The regression these guard: when the processed-message history is empty (new host,
lost state) the same photos must not be uploaded to Drive a second time.
"""
import hashlib
import json
import os
import sys
import unittest
from email.message import EmailMessage

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config, drive_ops, email_ops, processor, state

IMG_A = b'\xff\xd8\xff\xe0' + b'a' * 64
IMG_B = b'\xff\xd8\xff\xe0' + b'b' * 64


class _Exec:
    def __init__(self, value):
        self.value = value

    def execute(self):
        return self.value


class _FakeFiles:
    def __init__(self, drive):
        self.drive = drive

    def list(self, q=None, spaces=None, fields=None, pageSize=None, pageToken=None, **kw):
        wants_folder = "mimeType='application/vnd.google-apps.folder'" in q
        name = q.split("name='")[1].split("'")[0] if "name='" in q else None
        parent = None
        for token in q.split(' and '):
            if 'in parents' in token:
                parent = token.strip().split("'")[1]

        files = []
        for fid, f in self.drive.store.items():
            if name and f['name'] != name:
                continue
            if parent and f['parent'] != parent:
                continue
            if wants_folder and not f['is_folder']:
                continue
            item = {'id': fid, 'name': f['name']}
            if not f['is_folder']:
                item['md5Checksum'] = hashlib.md5(f['data']).hexdigest()
            files.append(item)
        return _Exec({'files': files})

    def create(self, body=None, media_body=None, fields=None):
        fid = f"f{len(self.drive.store) + 1}"
        self.drive.store[fid] = {
            'name': body['name'],
            'parent': (body.get('parents') or [None])[0],
            'is_folder': body.get('mimeType', '').endswith('folder'),
            'data': _payload(media_body),
        }
        return _Exec({'id': fid})

    def update(self, fileId=None, media_body=None):
        self.drive.store[fileId]['data'] = _payload(media_body)
        return _Exec({'id': fileId})

    def get_media(self, fileId=None):
        return _Exec(self.drive.store[fileId]['data'])


def _payload(media_body):
    if media_body is None:
        return b''
    if hasattr(media_body, 'getbytes'):
        return media_body.getbytes(0, media_body.size())
    with open(media_body._filename, 'rb') as fh:   # MediaFileUpload
        return fh.read()


class _FakeDrive:
    def __init__(self):
        self.store = {}

    def files(self):
        return _FakeFiles(self)

    def photos(self):
        return sorted(f['name'] for f in self.store.values()
                      if not f['is_folder'] and f['name'].endswith('.JPG'))

    def folders(self):
        return sorted(f['name'] for f in self.store.values() if f['is_folder'])

    def drop_state(self):
        for fid in [k for k, v in self.store.items() if v['name'] == state.STATE_FILENAME]:
            del self.store[fid]


class _FakeIMAP:
    def __init__(self, messages):
        self.messages = messages
        self.header_fetches = 0
        self.body_fetches = 0

    def select(self, mailbox):
        return ('OK', [b'1'])

    def search(self, charset, criteria):
        return ('OK', [b' '.join(eid for eid, _ in self.messages)])

    def fetch(self, eid, spec):
        msg = dict(self.messages)[eid]
        if 'HEADER' in spec:
            self.header_fetches += 1
            raw = b''.join(f"{k}: {v}\r\n".encode() for k, v in msg.items()) + b'\r\n'
        else:
            self.body_fetches += 1
            raw = msg.as_bytes()
        return ('OK', [(b'1 (BODY[])', raw), b')'])

    def logout(self):
        pass


def _message(message_id, subject, date, attachments):
    msg = EmailMessage()
    msg['Message-ID'] = message_id
    msg['Subject'] = subject
    msg['Date'] = date
    msg.set_content('photo attached')
    for name, data in attachments:
        msg.add_attachment(data, maintype='image', subtype='jpeg', filename=name)
    return msg


class TestProcessorEndToEnd(unittest.TestCase):
    def setUp(self):
        self.drive = _FakeDrive()
        self.imap = _FakeIMAP([
            (b'1', _message('<a@cam>', 'NOVA motion', 'Tue, 18 Aug 2026 20:15:04 +0200',
                            [('IMG1.JPG', IMG_A)])),
            (b'2', _message('<b@cam>', 'CHECHLUVKA motion', 'Tue, 18 Aug 2026 09:30:00 +0200',
                            [('IMG2.JPG', IMG_B)])),
            (b'3', _message('<c@cam>', 'Nothing to see here', 'Tue, 18 Aug 2026 10:00:00 +0200', [])),
        ])

        os.makedirs(config.Config.TEMP_DIR, exist_ok=True)

        # Set on the class, not via env: config is read at import time, so the test
        # must not depend on which test module imported it first.
        self._saved = (config.Config.STATE_BACKEND, config.Config.TARGET_DRIVE_FOLDER_ID)
        config.Config.STATE_BACKEND = 'drive'
        config.Config.TARGET_DRIVE_FOLDER_ID = 'ROOT'

        self._real_imap = email_ops.connect_imap
        self._real_drive = drive_ops.get_drive_service
        email_ops.connect_imap = lambda: self.imap
        drive_ops.get_drive_service = lambda: self.drive

    def tearDown(self):
        email_ops.connect_imap = self._real_imap
        drive_ops.get_drive_service = self._real_drive
        config.Config.STATE_BACKEND, config.Config.TARGET_DRIVE_FOLDER_ID = self._saved

    def test_first_run_uploads_and_files_by_service_day(self):
        processor.process_emails()

        self.assertEqual(self.drive.photos(),
                         ['2026-08-18 09:30 Chechlůvka.JPG', '2026-08-18 20:15 Nová.JPG'])
        # 09:30 is before the noon cutoff, so it belongs to the previous service day
        self.assertIn('2026-08-17', self.drive.folders())
        self.assertIn('2026-08-18', self.drive.folders())
        # The message without a known location is remembered, not uploaded
        self.assertEqual(self.imap.body_fetches, 2)

    def test_second_run_is_a_no_op(self):
        processor.process_emails()
        photos = self.drive.photos()

        self.imap.body_fetches = 0
        processor.process_emails()

        self.assertEqual(self.drive.photos(), photos)
        # History is checked against headers, so no attachment is downloaded again
        self.assertEqual(self.imap.body_fetches, 0)

    def test_empty_history_does_not_re_upload(self):
        """Cold start: the state was lost (or the pipeline moved to a new host)."""
        processor.process_emails()
        photos = self.drive.photos()

        self.drive.drop_state()
        processor.process_emails()

        self.assertEqual(self.drive.photos(), photos)

    def test_distinct_attachments_of_one_email_are_both_kept(self):
        self.imap = _FakeIMAP([
            (b'1', _message('<d@cam>', 'DUB motion', 'Tue, 18 Aug 2026 21:00:00 +0200',
                            [('A.JPG', IMG_A), ('B.JPG', IMG_B)])),
        ])
        email_ops.connect_imap = lambda: self.imap

        processor.process_emails()

        # Both share the email's timestamp, so the second one gets a suffix
        self.assertEqual(self.drive.photos(),
                         ['2026-08-18 21:00 Dub (2).JPG', '2026-08-18 21:00 Dub.JPG'])


if __name__ == '__main__':
    unittest.main()

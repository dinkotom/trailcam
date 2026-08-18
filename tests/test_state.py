import datetime
import json
import os
import sys
import unittest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import state


class _Exec:
    def __init__(self, value):
        self.value = value

    def execute(self):
        return self.value


class _FakeFiles:
    """Minimal stand-in for service.files() covering what DriveJsonState uses."""

    def __init__(self, drive):
        self.drive = drive

    def list(self, q=None, spaces=None, fields=None, **kw):
        name = q.split("name='")[1].split("'")[0]
        found = [{'id': fid} for fid, f in self.drive.store.items() if f['name'] == name]
        return _Exec({'files': found})

    def create(self, body=None, media_body=None, fields=None):
        fid = f"file{len(self.drive.store) + 1}"
        self.drive.store[fid] = {'name': body['name'], 'data': _payload(media_body)}
        self.drive.creates += 1
        return _Exec({'id': fid})

    def update(self, fileId=None, media_body=None):
        self.drive.store[fileId]['data'] = _payload(media_body)
        self.drive.updates += 1
        return _Exec({'id': fileId})

    def get_media(self, fileId=None):
        return _Exec(self.drive.store[fileId]['data'])


def _payload(media_body):
    return media_body.getbytes(0, media_body.size())


class _FakeDrive:
    def __init__(self):
        self.store = {}
        self.creates = 0
        self.updates = 0

    def files(self):
        return _FakeFiles(self)

    def state(self):
        for f in self.store.values():
            if f['name'] == state.STATE_FILENAME:
                return json.loads(f['data'].decode('utf-8'))
        return None


class TestDriveJsonState(unittest.TestCase):
    def setUp(self):
        self.drive = _FakeDrive()

    def _open(self):
        s = state.DriveJsonState(self.drive, 'ROOT')
        s.open()
        return s

    def test_creates_state_file_on_first_run(self):
        s = self._open()
        self.assertFalse(s.is_processed('<a@cam>'))
        s.mark_processed('<a@cam>')
        s.flush()

        self.assertEqual(self.drive.creates, 1)
        self.assertIn('<a@cam>', self.drive.state()['processed'])

    def test_state_survives_between_runs(self):
        s = self._open()
        s.mark_processed('<a@cam>')
        s.flush()

        # Second run: a fresh backend against the same Drive
        s2 = self._open()
        self.assertTrue(s2.is_processed('<a@cam>'))
        self.assertFalse(s2.is_processed('<b@cam>'))

    def test_flush_is_noop_when_nothing_changed(self):
        s = self._open()
        s.mark_processed('<a@cam>')
        s.flush()
        writes = self.drive.creates + self.drive.updates

        s.flush()
        self.assertEqual(self.drive.creates + self.drive.updates, writes)

    def test_old_entries_are_pruned_on_open(self):
        old = (datetime.datetime.now(datetime.timezone.utc)
               - datetime.timedelta(days=state.RETENTION_DAYS + 1)).isoformat()
        recent = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.drive.store['seed'] = {
            'name': state.STATE_FILENAME,
            'data': json.dumps({'processed': {'<old@cam>': old, '<new@cam>': recent}}).encode(),
        }

        s = self._open()
        self.assertFalse(s.is_processed('<old@cam>'))
        self.assertTrue(s.is_processed('<new@cam>'))

    def test_corrupt_state_file_starts_fresh_and_is_rewritten(self):
        self.drive.store['seed'] = {'name': state.STATE_FILENAME, 'data': b'{not json'}

        s = self._open()
        self.assertFalse(s.is_processed('<a@cam>'))
        s.mark_processed('<a@cam>')
        s.flush()

        # Rewritten in place, not duplicated
        self.assertEqual(self.drive.creates, 0)
        self.assertEqual(self.drive.updates, 1)
        self.assertEqual(list(self.drive.state()['processed']), ['<a@cam>'])


if __name__ == '__main__':
    unittest.main()

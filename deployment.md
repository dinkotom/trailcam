# Deployment (GitHub Actions)

The processor runs as a scheduled GitHub Actions workflow in this repo:
[`.github/workflows/process-emails.yml`](.github/workflows/process-emails.yml).
It replaces the previous PythonAnywhere deployment (see *Migration* at the bottom).

Why Actions: the job is a short cron task, not a server. GitHub runs it every ~20
minutes for free (this repo is public, so Actions minutes are unlimited), and there
is nothing to keep alive or pay for. The same pattern already runs the gallery repo
`dinkotom/tc-bb1b26a7`, which reads the photos this pipeline uploads.

## 1. State lives on Google Drive

GitHub runners are ephemeral, so `data/processed.db` cannot be used to remember which
emails were already handled. With `STATE_BACKEND=drive` the history is stored as
`_trailcam_state.json` inside `TARGET_DRIVE_FOLDER_ID`:

```json
{ "processed": { "<message-id@camera>": "2026-08-18T18:20:03+00:00" } }
```

Entries older than 60 days are pruned on every run, and the file is written after each
processed message, so a crash mid-run cannot cause re-uploads. Because the state sits
next to the photos, the pipeline can be moved to another host without losing history.

The history is a shortcut, not the safety net: before uploading, the md5 of the photo is
compared against the files already in the target Drive folder, and a photo that is already
there is skipped. So an empty or lost history costs some IMAP traffic on the next run, but
never produces duplicates. This was learned the hard way during the migration — the first
run started with an empty history and re-uploaded 273 photos that PythonAnywhere had already
delivered (they were removed afterwards).

Locally nothing changes: `STATE_BACKEND` defaults to `sqlite` (`data/processed.db`).

## 2. Repository secrets

**Settings → Secrets and variables → Actions → Secrets:**

| Secret | Value |
| --- | --- |
| `EMAIL_USER` | mailbox the cameras send to |
| `EMAIL_PASS` | its password |
| `ADMIN_EMAIL` | where crash alerts are sent |
| `GOOGLE_TOKEN_JSON` | **the whole contents** of `token.json` (one line) |
| `TARGET_DRIVE_FOLDER_ID` | ID of the Drive root folder |

The last two are the same values the gallery repo already uses.

Optional **Variables** (not secrets), only to override defaults: `IMAP_SERVER`
(`imap.seznam.cz`), `SMTP_SERVER` (`smtp.seznam.cz`), `LOG_LEVEL` (`INFO`).

To produce `GOOGLE_TOKEN_JSON`:

```bash
python src/auth_drive.py     # writes token.json locally
pbcopy < token.json          # paste into the secret
```

> **Keep the Google Cloud OAuth app in "Production".** In "Testing" status the refresh
> token expires after 7 days and every run then fails until the secret is refreshed.

## 3. Run it

- Automatic: cron `*/20 * * * *` (GitHub starts scheduled runs with some delay).
- Manual: **Actions → process-emails → Run workflow**.
- Failures: `src/main.py` exits non-zero, so the run goes red, GitHub emails the repo
  owner, and the processor also sends its own alert to `ADMIN_EMAIL`.

Two runs must never process the same mailbox at once, so the workflow uses
`concurrency: process-emails` with `cancel-in-progress: false`.

### Logs are public

This repo is public, which means workflow logs are readable by anyone. At `LOG_LEVEL=INFO`
the logs contain only counts, generated filenames (date, time, location name) and errors —
no subjects, no Drive IDs. Set the `LOG_LEVEL` variable to `WARNING` to reduce this further,
or to `DEBUG` when troubleshooting locally (DEBUG also prints email subjects).

### Keepalive

GitHub disables cron in repositories with no activity for 60 days. The last workflow step
pushes an empty commit once the newest commit is 50+ days old (same trick as the gallery repo).

## 4. Efficiency note

Each run only downloads message **headers** for the lookback window (`EMAIL_LOOKBACK_DAYS`,
7 in the workflow, code default 2), checks them against the state file, and downloads full bodies **only** for
messages that are new and from a known location. Headers are fetched with `BODY.PEEK`, so
the `\Seen` flags in the mailbox are left untouched.

## Running elsewhere

- **Local / VPS, one-shot:** `python src/main.py` (cron or launchd, `STATE_BACKEND=sqlite`).
- **Local / VPS, long-running:** `python src/always_on_runner.py` — loops every 5 minutes.
  This was the PythonAnywhere always-on entry point; it is kept for hosts where a resident
  process is the easier option.

## Migration from PythonAnywhere

1. Set the repository secrets above.
2. Run the workflow manually and confirm the run is green and `_trailcam_state.json`
   appears in the Drive root folder.
3. On PythonAnywhere: delete the **always-on task** and the hourly **scheduled task**
   (Tasks tab), so both hosts don't upload the same photos.
4. Downgrade the PythonAnywhere account to the free tier.

Note that the free tier could not run this app at all: outgoing connections are limited to
an HTTP(S) proxy with a domain whitelist, so IMAP/SMTP to `seznam.cz` is blocked there, and
free accounts get only one scheduled task per day.

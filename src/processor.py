import hashlib
import os
import io
import logging
from src import config, email_ops, utils, drive_ops, logger, state as state_ops


def process_emails():
    """Main execution loop."""
    # Ensure logging is setup if this is called directly or via runner
    logger.setup_logging()
    log = logging.getLogger("processor")

    # 1. Initialize
    log.info("Connecting to Drive...")
    # Raise exception to trigger notification in main.py
    drive_service = drive_ops.get_drive_service()

    # Check root target folder
    root_folder_id = config.Config.TARGET_DRIVE_FOLDER_ID

    log.info("Loading processed-message history...")
    state = state_ops.open_state(drive_service)

    log.info("Connecting to Email...")
    mail = email_ops.connect_imap()

    try:
        _process_inbox(log, mail, drive_service, root_folder_id, state)
    finally:
        state.flush()
        try:
            mail.logout()
        except Exception as e:
            log.debug(f"IMAP logout failed: {e}")


def _process_inbox(log, mail, drive_service, root_folder_id, state):
    # 2. Fetch headers only, so attachments are downloaded for new messages only
    days_back = config.Config.EMAIL_LOOKBACK_DAYS
    log.info(f"Fetching headers for the last {days_back} days of emails...")
    headers = email_ops.fetch_recent_headers(mail, days=days_back)

    uploaded_count = 0
    skipped_count = 0
    new_count = 0
    # md5 of the photos already in each Drive folder, fetched once per folder
    folder_checksums = {}

    # 3. Process
    for eid, header in headers:
        message_id = header.get("Message-ID")
        if not message_id:
            message_id = f"NO_ID_{eid}"

        if state.is_processed(message_id):
            log.debug(f"Skipping {message_id} (Already processed)")
            continue

        # Parse info from the headers
        subject = email_ops.get_email_subject(header)
        date_obj = email_ops.get_email_date(header)

        location = utils.get_location_from_subject(subject)

        if location == "Neznámá lokace":
            # Subject is only logged at DEBUG level: run logs of this repo are public.
            log.info("Skipping message with unknown location.")
            log.debug(f"Unknown location for subject '{subject}' ({message_id}).")
            # Mark processed to avoid re-fetch
            state.mark_processed(message_id)
            state.flush()
            continue

        new_count += 1
        service_day = utils.get_service_date(date_obj)  # YYYY-MM-DD

        # Now that we know the message is relevant, download it with attachments
        msg = email_ops.fetch_message(mail, eid)

        # Prepare Target Folder on Drive
        day_folder_id = drive_ops.ensure_folder(drive_service, service_day, parent_id=root_folder_id)

        # Ensure Location Subfolder
        location_folder_id = drive_ops.ensure_folder(drive_service, location, parent_id=day_folder_id)

        if location_folder_id not in folder_checksums:
            folder_checksums[location_folder_id] = drive_ops.list_folder_checksums(
                drive_service, location_folder_id)
        known_checksums = folder_checksums[location_folder_id]

        # Extract Attachments
        all_uploads_successful = True
        found_any_attachment = False
        attachment_index = 0

        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if filename:
                found_any_attachment = True
                attachment_index += 1

                # Generate new unique filename
                ext = os.path.splitext(filename)[1]
                if not ext:
                    ext = ".jpg"

                new_filename = utils.generate_filename(service_day, location, date_obj)
                # All attachments of one email share the email's timestamp, so the
                # second and later ones get a suffix instead of the same name.
                if attachment_index > 1:
                    new_filename = f"{new_filename} ({attachment_index})"
                new_filename += ext

                temp_path = os.path.join(config.Config.TEMP_DIR, new_filename)

                # Write to temp
                try:
                    payload = part.get_payload(decode=True)

                    # Idempotency guard: the same photo may already be on Drive from
                    # an earlier run whose history we no longer have.
                    checksum = hashlib.md5(payload).hexdigest()
                    if checksum in known_checksums:
                        log.info(
                            f"Already on Drive as '{known_checksums[checksum]}' "
                            f"in {service_day}/{location}, skipping upload."
                        )
                        skipped_count += 1
                        continue

                    with open(temp_path, 'wb') as f:
                        f.write(payload)

                    log.info(f"Uploading {new_filename} to {service_day}/{location}...")
                    drive_ops.upload_file(drive_service, temp_path, new_filename, location_folder_id)
                    os.remove(temp_path)
                    known_checksums[checksum] = new_filename
                    uploaded_count += 1
                    log.info("Upload success.")
                except Exception as e:
                    log.error(f"Error handling attachment {filename}: {e}")
                    all_uploads_successful = False

        # Mark as processed only if:
        # A) It had attachments and ALL were uploaded successfully
        # B) It had NO attachments (so we don't check it again)
        if found_any_attachment:
            if all_uploads_successful:
                state.mark_processed(message_id)
            else:
                log.warning(f"Skipping history mark for {message_id} due to upload failure.")
        else:
            log.info(f"No attachment in {message_id}, marking processed.")
            state.mark_processed(message_id)

        # Persist after every message, so a crash mid-run cannot cause re-uploads
        state.flush()

    log.info(
        f"Processing complete. New messages: {new_count}, photos uploaded: "
        f"{uploaded_count}, already on Drive: {skipped_count}."
    )

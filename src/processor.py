import os
import io
import logging
from src import config, db, email_ops, utils, drive_ops, logger

def process_emails():
    """Main execution loop."""
    # Ensure logging is setup if this is called directly or via runner
    logger.setup_logging()
    log = logging.getLogger("processor")
    
    # 1. Initialize
    log.info("Initializing Database...")
    db.init_db()
    
    log.info("Connecting to Drive...")
    try:
        drive_service = drive_ops.get_drive_service()
    except Exception as e:
        log.error(f"Error connecting to Google Drive: {e}")
        return

    # Check root target folder
    root_folder_id = config.Config.TARGET_DRIVE_FOLDER_ID
    
    log.info("Connecting to Email...")
    try:
        mail = email_ops.connect_imap()
    except Exception as e:
        log.error(f"Error connecting to Email: {e}")
        return

    # 2. Fetch
    log.info("Fetching recent emails...")
    # Fetching recent emails
    days_back = config.Config.EMAIL_LOOKBACK_DAYS
    log.info(f"Fetching last {days_back} days of emails...")
    emails = email_ops.fetch_recent_emails(mail, days=days_back) 
    log.info(f"Found {len(emails)} recent emails.")

    # 3. Process
    for eid, msg in emails:
        message_id = msg.get("Message-ID")
        if not message_id:
            message_id = f"NO_ID_{eid}"
            
        if db.is_processed(message_id):
            log.debug(f"Skipping {message_id} (Already processed)")
            continue
            
        # Parse info
        subject = email_ops.get_email_subject(msg)
        date_obj = email_ops.get_email_date(msg)
        
        location = utils.get_location_from_subject(subject)
        
        if location == "Neznámá lokace":
            log.info(f"Skipping {message_id}: Subject '{subject}' makes no sense (Unknown Location).")
            # Mark processed to avoid re-fetch
            db.mark_processed(message_id)
            continue
            
        service_day = utils.get_service_date(date_obj) # YYYY-MM-DD
        
        # Prepare Target Folder on Drive
        day_folder_id = drive_ops.ensure_folder(drive_service, service_day, parent_id=root_folder_id)
        
        # Extract Attachments
        all_uploads_successful = True
        found_any_attachment = False
        
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
                
            filename = part.get_filename()
            if filename:
                found_any_attachment = True
                
                # Generate new unique filename
                ext = os.path.splitext(filename)[1]
                if not ext:
                    ext = ".jpg"
                
                new_filename = utils.generate_filename(service_day, location, date_obj) + ext
                temp_path = os.path.join(config.Config.TEMP_DIR, new_filename)
                
                # Write to temp
                try:
                    with open(temp_path, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    
                    log.info(f"Uploading {new_filename} to Drive folder {service_day}...")
                    drive_ops.upload_file(drive_service, temp_path, new_filename, day_folder_id)
                    os.remove(temp_path)
                    log.info("Upload success.")
                except Exception as e:
                    log.error(f"Error handling attachment {filename}: {e}")
                    all_uploads_successful = False
        
        # Mark as processed only if:
        # A) It had attachments and ALL were uploaded successfully
        # B) It had NO attachments (so we don't check it again)
        if found_any_attachment:
            if all_uploads_successful:
                db.mark_processed(message_id)
            else:
                log.warning(f"Skipping DB mark for {message_id} due to upload failure.")
        else:
            log.info(f"No attachment in {message_id}, marking processed.")
            db.mark_processed(message_id)

    log.info("Processing complete.")

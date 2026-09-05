import time
import random
import logging
from datetime import datetime
from threading import Thread
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Campaign, CampaignRecipient, Account, Template, Setting, ActivityLog
from backend.services.sender import dispatch_email_message

logger = logging.getLogger("email_sender_pro.campaign_engine")

class CampaignEngineWorker:
    _active_threads = {}

    @classmethod
    def start_campaign(cls, campaign_id: int):
        if campaign_id in cls._active_threads and cls._active_threads[campaign_id].is_alive():
            logger.info("Campaign %d worker is already running.", campaign_id)
            return
        
        thread = Thread(target=cls._run_loop, args=(campaign_id,), daemon=True)
        cls._active_threads[campaign_id] = thread
        thread.start()
        logger.info("Started background worker thread for campaign %d", campaign_id)

    @classmethod
    def _run_loop(cls, campaign_id: int):
        db = SessionLocal()
        try:
            while True:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign or campaign.status != "running":
                    logger.info("Campaign %d stopped or paused. Worker exiting loop.", campaign_id)
                    break

                # Load settings
                settings_rows = db.query(Setting).all()
                settings_map = {s.key: s.value for s in settings_rows}
                delay_min = float(settings_map.get("delay_min", 5.0))
                delay_max = float(settings_map.get("delay_max", 15.0))
                rotation_mode = settings_map.get("rotation_mode", "round_robin")
                priority = settings_map.get("priority", "normal")
                reply_to = settings_map.get("reply_to_email", "")
                signature = settings_map.get("email_signature", "")

                # Fetch next queued recipient
                recipient = db.query(CampaignRecipient).filter(
                    CampaignRecipient.campaign_id == campaign_id,
                    CampaignRecipient.status == "queued"
                ).first()

                if not recipient:
                    # Check if all done
                    queued_count = db.query(CampaignRecipient).filter(
                        CampaignRecipient.campaign_id == campaign_id,
                        CampaignRecipient.status == "queued"
                    ).count()
                    if queued_count == 0:
                        campaign.status = "completed"
                        campaign.completed_at = datetime.utcnow()
                        db.commit()
                        logger.info("Campaign %d completed successfully.", campaign_id)
                    break

                # Select sending account
                account = None
                if campaign.account_id:
                    account = db.query(Account).filter(Account.id == campaign.account_id, Account.enabled == True).first()
                
                if not account:
                    active_accounts = db.query(Account).filter(Account.enabled == True).all()
                    if not active_accounts:
                        logger.error("Campaign %d error: No active sending accounts found.", campaign_id)
                        campaign.status = "error"
                        db.commit()
                        break
                    if rotation_mode == "random":
                        account = random.choice(active_accounts)
                    else: # round_robin
                        # simple rotation based on sent count
                        idx = (campaign.sent_count + campaign.failed_count) % len(active_accounts)
                        account = active_accounts[idx]

                lead = recipient.lead
                template = campaign.template

                if not lead or not template:
                    recipient.status = "failed"
                    recipient.last_error = "Missing lead or template."
                    campaign.failed_count += 1
                    db.commit()
                    continue

                # Render template variables
                subject = template.subject
                body = template.body_html + (f"\n\n{signature}" if signature else "")
                for key, val in [
                    ("first_name", lead.first_name or "Valued"),
                    ("last_name", lead.last_name or "Lead"),
                    ("email", lead.email),
                    ("company", lead.company or ""),
                    ("position", lead.position or ""),
                    ("location", lead.location or ""),
                ]:
                    subject = subject.replace(f"{{{{{key}}}}}", str(val))
                    body = body.replace(f"{{{{{key}}}}}", str(val))

                # Dispatch email via transport
                recipient.status = "sending"
                recipient.attempts += 1
                db.commit()

                success = False
                err_msg = ""
                message_id = f"msg_{campaign_id}_{recipient.id}_{int(time.time())}"

                try:
                    # Inject tracking pixel
                    tracking_url = f"https://ais-dev-6mn2zhysxh3rzzodeld3uj-514475041788.us-east1.run.app/api/track?id={message_id}"
                    body_with_pixel = body + f'<img src="{tracking_url}" width="1" height="1" style="display:none;" alt="" />'

                    dispatch_email_message(
                        account=account,
                        recipient=lead.email,
                        subject=subject,
                        body=body_with_pixel,
                        from_name=lead.sender_name or account.from_name or "Outreach Team",
                        high_priority=(priority == "high"),
                        reply_to=reply_to
                    )
                    success = True
                except Exception as ex:
                    err_msg = str(ex)
                    success = False

                if success:
                    recipient.status = "sent"
                    recipient.sent_at = datetime.utcnow()
                    campaign.sent_count += 1
                    
                    # Log to activity logs
                    log = ActivityLog(
                        event_type="email_sent",
                        severity="info",
                        message=f"Campaign email sent to {lead.email} via account {account.name}",
                        entity_id=campaign.id,
                        lead_email=lead.email,
                        account_name=account.name,
                        status="SENT",
                        provider_type=account.provider,
                        provider_message_id=message_id,
                        campaign_id=campaign.id
                    )
                    db.add(log)
                else:
                    recipient.status = "failed"
                    recipient.last_error = err_msg
                    campaign.failed_count += 1

                    log = ActivityLog(
                        event_type="email_failed",
                        severity="error",
                        message=f"Failed to send campaign email to {lead.email}: {err_msg}",
                        entity_id=campaign.id,
                        lead_email=lead.email,
                        account_name=account.name,
                        status="FAILED",
                        provider_type=account.provider if account else "smtp",
                        error_code="SMTP_DISPATCH_ERROR",
                        campaign_id=campaign.id
                    )
                    db.add(log)

                db.commit()

                # Delay pacing
                sleep_duration = random.uniform(delay_min, delay_max)
                time.sleep(sleep_duration)

        except Exception as e:
            logger.error("Campaign worker error on campaign %d: %s", campaign_id, str(e), exc_info=True)
        finally:
            db.close()

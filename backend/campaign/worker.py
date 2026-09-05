import time
import random
import logging
from datetime import datetime
from threading import Thread, Event
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Campaign, CampaignRecipient, Setting, ActivityLog, DeliveryLog, DeliveryEvent
from backend.services.sender import dispatch_email_message
from backend.campaign.renderer import TemplateRenderer
from backend.campaign.rotation import SenderRotationService, DailyLimitService
from backend.campaign.queue import CampaignQueueManager

logger = logging.getLogger("email_sender_pro.campaign_worker")

class CampaignWorkerInstance:
    def __init__(self, campaign_id: int):
        self.campaign_id = campaign_id
        self.stop_event = Event()

    def run(self):
        db = SessionLocal()
        logger.info("Campaign worker started for campaign %d", self.campaign_id)
        try:
            while not self.stop_event.is_set():
                campaign = db.query(Campaign).filter(Campaign.id == self.campaign_id).first()
                if not campaign or campaign.status != "running":
                    logger.info("Campaign %d is no longer running (status: %s). Worker stopping.", self.campaign_id, campaign.status if campaign else "deleted")
                    break

                # Load settings
                settings_map = {s.key: s.value for s in db.query(Setting).all()}
                delay_min = float(settings_map.get("delay_min", 5.0))
                delay_max = float(settings_map.get("delay_max", 15.0))
                rotation_mode = settings_map.get("rotation_mode", "round_robin")
                priority = settings_map.get("priority", "normal")
                reply_to = settings_map.get("reply_to_email", "")
                signature = settings_map.get("email_signature", "")
                max_retries = int(settings_map.get("max_retries", 3))

                recipient = CampaignQueueManager.get_next_recipient(db, self.campaign_id)
                if not recipient:
                    if CampaignQueueManager.count_queued(db, self.campaign_id) == 0:
                        campaign.status = "completed"
                        campaign.completed_at = datetime.utcnow()
                        db.commit()
                        logger.info("Campaign %d completed successfully.", self.campaign_id)
                    break

                lead = recipient.lead
                campaign_templates_list = campaign.templates if hasattr(campaign, 'templates') and campaign.templates else ([campaign.template] if campaign.template else [])
                template = random.choice(campaign_templates_list) if campaign_templates_list else None

                if not lead or not template:
                    recipient.status = "failed"
                    recipient.last_error = "Missing lead or template."
                    campaign.failed_count += 1
                    db.commit()
                    continue

                # Select Account via rotation & daily limits
                account = SenderRotationService.select_account(db, campaign.account_id, rotation_mode)
                if not account:
                    logger.error("Campaign %d paused: No active accounts with available daily limits.", self.campaign_id)
                    campaign.status = "paused"
                    db.commit()
                    break

                # Render template
                subject = TemplateRenderer.render(template.subject, lead, account)
                body = TemplateRenderer.render(template.body_html, lead, account)
                if signature:
                    body += f"\n\n{signature}"

                recipient.status = "sending"
                recipient.attempts += 1
                db.commit()

                success = False
                err_msg = ""
                message_id = f"msg_{self.campaign_id}_{recipient.id}_{int(time.time())}"

                # Retry loop
                attempt = 0
                while attempt <= max_retries and not success:
                    try:
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
                        attempt += 1
                        err_msg = str(ex)
                        if attempt <= max_retries:
                            time.sleep(2 ** attempt) # exponential backoff

                if success:
                    recipient.status = "sent"
                    recipient.sent_at = datetime.utcnow()
                    campaign.sent_count += 1

                    # Record delivery log
                    d_log = DeliveryLog(
                        campaign_id=campaign.id,
                        account_id=account.id,
                        recipient=lead.email,
                        provider=account.provider,
                        status="success",
                        message_id=message_id
                    )
                    db.add(d_log)
                    db.flush()

                    d_event = DeliveryEvent(
                        delivery_log_id=d_log.id,
                        event_type="sent",
                        tracking_id=message_id
                    )
                    db.add(d_event)

                    # Activity Log
                    act_log = ActivityLog(
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
                    db.add(act_log)
                else:
                    recipient.status = "failed"
                    recipient.last_error = err_msg
                    campaign.failed_count += 1

                    d_log = DeliveryLog(
                        campaign_id=campaign.id,
                        account_id=account.id if account else None,
                        recipient=lead.email,
                        provider=account.provider if account else "smtp",
                        status="failed",
                        error_info=err_msg
                    )
                    db.add(d_log)
                    db.flush()

                    d_event = DeliveryEvent(
                        delivery_log_id=d_log.id,
                        event_type="failed",
                        tracking_id=err_msg
                    )
                    db.add(d_event)

                    act_log = ActivityLog(
                        event_type="email_failed",
                        severity="error",
                        message=f"Failed to send email to {lead.email}: {err_msg}",
                        entity_id=campaign.id,
                        lead_email=lead.email,
                        account_name=account.name if account else "None",
                        status="FAILED",
                        provider_type=account.provider if account else "smtp",
                        error_code="SMTP_DISPATCH_ERROR",
                        campaign_id=campaign.id
                    )
                    db.add(act_log)

                db.commit()

                # Pacing delay
                sleep_duration = random.uniform(delay_min, delay_max)
                time.sleep(sleep_duration)

        except Exception as e:
            logger.error("Critical error in CampaignWorker for campaign %d: %s", self.campaign_id, str(e), exc_info=True)
        finally:
            db.close()

import time
import random
import logging
from datetime import datetime
from threading import Event
from backend.database import SessionLocal
from backend.models import Campaign, Setting, ActivityLog, DeliveryLog, DeliveryEvent
from backend.services.sender import dispatch_email_message
from backend.campaign.renderer import TemplateRenderer
from backend.campaign.rotation import SenderRotationService
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
                    logger.info(
                        "Campaign %d is no longer running (status: %s). Worker stopping.",
                        self.campaign_id,
                        campaign.status if campaign else "deleted",
                    )
                    break

                # Global settings as fallback only
                settings_map = {s.key: s.value for s in db.query(Setting).all()}

                # Prefer per-campaign pacing (desktop parity)
                delay_base = int(getattr(campaign, "delay_seconds", None) or settings_map.get("delay_min", 30) or 30)
                jitter = int(getattr(campaign, "jitter_seconds", None) or 0)
                if jitter <= 0 and str(settings_map.get("use_jitter", "true")).lower() in {"1", "true", "yes"}:
                    # legacy global jitter window
                    delay_min = float(settings_map.get("delay_min", delay_base))
                    delay_max = float(settings_map.get("delay_max", delay_base))
                else:
                    delay_min = max(1.0, float(delay_base - jitter))
                    delay_max = float(delay_base + max(jitter, 0))

                rotation_mode = (
                    getattr(campaign, "rotation_mode", None)
                    or settings_map.get("rotation_mode", "round_robin")
                    or "round_robin"
                )
                reply_to = (
                    (getattr(campaign, "reply_to", None) or "").strip()
                    or settings_map.get("reply_to_email", "")
                    or ""
                )
                signature = settings_map.get("email_signature", "") or ""
                max_retries = int(
                    getattr(campaign, "max_retries", None)
                    if getattr(campaign, "max_retries", None) is not None
                    else settings_map.get("max_retries", 3)
                    or 3
                )
                priority = settings_map.get("priority", "normal")

                recipient = CampaignQueueManager.get_next_recipient(db, self.campaign_id)
                if not recipient:
                    if CampaignQueueManager.count_queued(db, self.campaign_id) == 0:
                        campaign.status = "completed"
                        campaign.completed_at = datetime.utcnow()
                        db.commit()
                        logger.info("Campaign %d completed successfully.", self.campaign_id)
                    break

                lead = recipient.lead
                campaign_templates_list = (
                    list(campaign.templates)
                    if hasattr(campaign, "templates") and campaign.templates
                    else ([campaign.template] if campaign.template else [])
                )
                template = random.choice(campaign_templates_list) if campaign_templates_list else None

                if not lead or not template:
                    recipient.status = "failed"
                    recipient.last_error = "Missing lead or template."
                    campaign.failed_count = int(campaign.failed_count or 0) + 1
                    db.commit()
                    continue

                account = SenderRotationService.select_account(
                    db,
                    campaign.account_id,
                    rotation_mode,
                )
                if not account:
                    logger.error(
                        "Campaign %d paused: No active accounts with available daily limits.",
                        self.campaign_id,
                    )
                    campaign.status = "paused"
                    campaign.paused_at = datetime.utcnow()
                    db.commit()
                    break

                subject = TemplateRenderer.render(template.subject, lead, account)
                body = TemplateRenderer.render(template.body_html, lead, account)
                if signature:
                    body += f"\n\n{signature}"

                recipient.status = "sending"
                recipient.attempts = int(recipient.attempts or 0) + 1
                db.commit()

                success = False
                err_msg = ""
                message_id = f"msg_{self.campaign_id}_{recipient.id}_{int(time.time())}"

                attempt = 0
                while attempt <= max_retries and not success and not self.stop_event.is_set():
                    try:
                        # Only inject tracking pixel when a public HTTPS tracking base is configured
                        tracking_domain = (settings_map.get("tracking_public_url") or "").strip().rstrip("/")
                        body_to_send = body
                        if tracking_domain.lower().startswith("https://"):
                            tracking_url = f"{tracking_domain}/api/track?id={message_id}"
                            body_to_send = body + (
                                f'<img src="{tracking_url}" width="1" height="1" '
                                f'style="display:none;" alt="" />'
                            )

                        result = dispatch_email_message(
                            account=account,
                            recipient=lead.email,
                            subject=subject,
                            body=body_to_send,
                            from_name=lead.sender_name or account.from_name or "Outreach Team",
                            high_priority=(priority == "high"),
                            reply_to=reply_to,
                        )

                        # Support DeliveryResult objects and plain success
                        if result is not None and hasattr(result, "status"):
                            status_val = str(getattr(result, "status", "")).upper()
                            if status_val not in {"SENT", "SUCCESS"}:
                                raise RuntimeError(getattr(result, "message", None) or "Send failed")

                        success = True
                    except Exception as ex:
                        attempt += 1
                        err_msg = str(ex)
                        if attempt <= max_retries:
                            time.sleep(min(30, 2 ** attempt))

                if success:
                    recipient.status = "sent"
                    recipient.sent_at = datetime.utcnow()
                    campaign.sent_count = int(campaign.sent_count or 0) + 1

                    d_log = DeliveryLog(
                        campaign_id=campaign.id,
                        account_id=account.id,
                        recipient=lead.email,
                        provider=account.provider,
                        status="success",
                        message_id=message_id,
                    )
                    db.add(d_log)
                    db.flush()

                    db.add(
                        DeliveryEvent(
                            delivery_log_id=d_log.id,
                            event_type="sent",
                            tracking_id=message_id,
                        )
                    )

                    db.add(
                        ActivityLog(
                            event_type="email_sent",
                            severity="info",
                            message=f"Campaign email sent to {lead.email} via account {account.name}",
                            entity_id=campaign.id,
                            lead_email=lead.email,
                            account_name=account.name,
                            status="SENT",
                            provider_type=account.provider,
                            provider_message_id=message_id,
                            campaign_id=campaign.id,
                        )
                    )
                else:
                    recipient.status = "failed"
                    recipient.last_error = err_msg
                    campaign.failed_count = int(campaign.failed_count or 0) + 1

                    d_log = DeliveryLog(
                        campaign_id=campaign.id,
                        account_id=account.id if account else None,
                        recipient=lead.email,
                        provider=account.provider if account else "smtp",
                        status="failed",
                        error_info=err_msg,
                    )
                    db.add(d_log)
                    db.flush()

                    db.add(
                        DeliveryEvent(
                            delivery_log_id=d_log.id,
                            event_type="failed",
                            tracking_id=err_msg[:255] if err_msg else None,
                        )
                    )

                    db.add(
                        ActivityLog(
                            event_type="email_failed",
                            severity="error",
                            message=f"Failed to send email to {lead.email}: {err_msg}",
                            entity_id=campaign.id,
                            lead_email=lead.email,
                            account_name=account.name if account else "None",
                            status="FAILED",
                            provider_type=account.provider if account else "smtp",
                            error_code="SMTP_DISPATCH_ERROR",
                            campaign_id=campaign.id,
                        )
                    )

                db.commit()

                if self.stop_event.is_set():
                    break

                sleep_duration = random.uniform(delay_min, delay_max)
                logger.debug(
                    "Campaign %d pacing sleep %.1fs (base=%s jitter=%s rotation=%s)",
                    self.campaign_id,
                    sleep_duration,
                    delay_base,
                    jitter,
                    rotation_mode,
                )
                # Interruptible sleep
                end = time.time() + sleep_duration
                while time.time() < end and not self.stop_event.is_set():
                    time.sleep(min(0.5, end - time.time()))

        except Exception as e:
            logger.error(
                "Critical error in CampaignWorker for campaign %d: %s",
                self.campaign_id,
                str(e),
                exc_info=True,
            )
        finally:
            db.close()

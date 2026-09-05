import logging
from sqlalchemy.orm import Session
from backend.models import CampaignRecipient

logger = logging.getLogger("email_sender_pro.queue")

class CampaignQueueManager:
    @staticmethod
    def get_next_recipient(db: Session, campaign_id: int) -> CampaignRecipient:
        return db.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.status == "queued"
        ).first()

    @staticmethod
    def count_queued(db: Session, campaign_id: int) -> int:
        return db.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.status == "queued"
        ).count()

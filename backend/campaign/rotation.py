import random
import logging
from sqlalchemy.orm import Session
from backend.models import Account, DeliveryLog
from datetime import datetime, date

logger = logging.getLogger("email_sender_pro.rotation")

class DailyLimitService:
    @staticmethod
    def get_sent_today(db: Session, account_id: int) -> int:
        today_start = datetime.combine(date.today(), datetime.min.time())
        count = db.query(DeliveryLog).filter(
            DeliveryLog.account_id == account_id,
            DeliveryLog.status == "success",
            DeliveryLog.created_at >= today_start
        ).count()
        return count

    @staticmethod
    def check_limit(db: Session, account: Account) -> bool:
        sent = DailyLimitService.get_sent_today(db, account.id)
        limit = account.daily_limit or 500
        return sent < limit

class SenderRotationService:
    @staticmethod
    def select_account(db: Session, campaign_account_id: int = None, rotation_mode: str = "round_robin") -> Account:
        if campaign_account_id:
            acc = db.query(Account).filter(Account.id == campaign_account_id, Account.enabled == True).first()
            if acc and DailyLimitService.check_limit(db, acc):
                return acc
        
        active_accounts = db.query(Account).filter(Account.enabled == True).all()
        eligible_accounts = [a for a in active_accounts if DailyLimitService.check_limit(db, a)]

        if not eligible_accounts:
            return None

        if rotation_mode == "random":
            return random.choice(eligible_accounts)
        else: # round_robin or default
            # Select account with lowest sent today count
            eligible_accounts.sort(key=lambda a: DailyLimitService.get_sent_today(db, a.id))
            return eligible_accounts[0]

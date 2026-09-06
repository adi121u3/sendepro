import logging
from threading import Thread
from backend.campaign.worker import CampaignWorkerInstance

logger = logging.getLogger("email_sender_pro.engine")


class CampaignEngine:
    _workers = {}

    @classmethod
    def start_campaign(cls, campaign_id: int):
        existing = cls._workers.get(campaign_id)
        if existing is not None:
            thread = existing.get("thread")
            worker = existing.get("worker")
            alive = thread is not None and thread.is_alive()
            stopped = worker is not None and worker.stop_event.is_set()
            if alive and not stopped:
                logger.info(
                    "Campaign engine worker already active for campaign %d",
                    campaign_id,
                )
                return
            if alive and stopped:
                logger.info(
                    "Replacing stopped worker thread for campaign %d",
                    campaign_id,
                )

        worker_instance = CampaignWorkerInstance(campaign_id)
        thread = Thread(
            target=worker_instance.run,
            daemon=True,
            name=f"campaign-{campaign_id}",
        )
        cls._workers[campaign_id] = {
            "worker": worker_instance,
            "thread": thread,
        }
        thread.start()
        logger.info("Started campaign engine worker thread for campaign %d", campaign_id)

    @classmethod
    def pause_campaign(cls, campaign_id: int):
        if campaign_id in cls._workers:
            cls._workers[campaign_id]["worker"].stop_event.set()
            logger.info("Signaled stop/pause for campaign %d worker", campaign_id)

    @classmethod
    def stop_campaign(cls, campaign_id: int):
        if campaign_id in cls._workers:
            cls._workers[campaign_id]["worker"].stop_event.set()
            logger.info("Signaled stop for campaign %d worker", campaign_id)

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, Table, Float
from sqlalchemy.orm import relationship
from backend.database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False) # 'smtp', 'bell', 'microsoft', 'zeptomail', etc.
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    from_name = Column(String(100), nullable=True)
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True, default=587)
    smtp_security = Column(String(50), nullable=True, default="starttls")
    smtp_username = Column(String(255), nullable=True)
    enabled = Column(Boolean, default=True)
    daily_limit = Column(Integer, default=500)
    status = Column(String(50), default="idle") # idle, active, error, disconnected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    credential = relationship("AccountCredential", back_populates="account", uselist=False, cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="sender_account")
    delivery_logs = relationship("DeliveryLog", back_populates="account")

class AccountCredential(Base):
    __tablename__ = "account_credentials"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Encrypted sensitive fields
    smtp_password_enc = Column(Text, nullable=True)
    zeptomail_api_key_enc = Column(Text, nullable=True)
    oauth_access_token_enc = Column(Text, nullable=True)
    oauth_refresh_token_enc = Column(Text, nullable=True)
    oauth_token_expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account = relationship("Account", back_populates="credential")

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=False, index=True, unique=True)
    company = Column(String(150), nullable=True)
    domain = Column(String(150), nullable=True)
    position = Column(String(150), nullable=True)
    location = Column(String(150), nullable=True)
    sender_name = Column(String(100), nullable=True)
    sender_full_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipients = relationship("CampaignRecipient", back_populates="lead", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_lead_email", "email"),
        Index("idx_lead_company", "company"),
    )

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True)
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaigns = relationship("Campaign", back_populates="template")

campaign_templates = Table(
    "campaign_templates",
    Base.metadata,
    Column("campaign_id", Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("template_id", Integer, ForeignKey("templates.id", ondelete="CASCADE"), primary_key=True)
)

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    status = Column(String(50), default="draft") # draft, running, paused, completed, stopped, error
    tag = Column(String(50), default="Marketing")
    
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    # Desktop-parity pacing / delivery settings
    delay_seconds = Column(Integer, default=30)
    jitter_seconds = Column(Integer, default=2)
    max_retries = Column(Integer, default=3)
    rotation_mode = Column(String(50), default="round_robin")  # round_robin | random | failover
    reply_to = Column(String(255), nullable=True)
    delivery_route = Column(String(50), default="auto")  # auto | smtp | zeptomail_smtp | zeptomail_api

    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    template = relationship("Template", back_populates="campaigns")
    templates = relationship("Template", secondary=campaign_templates, backref="multi_campaigns")
    sender_account = relationship("Account", back_populates="campaigns")
    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")
    delivery_logs = relationship("DeliveryLog", back_populates="campaign", cascade="all, delete-orphan")

class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    
    status = Column(String(50), default="queued") # queued, sending, sent, failed, skipped
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    
    queued_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="recipients")
    lead = relationship("Lead", back_populates="recipients")

    __table_args__ = (
        Index("idx_queue_status", "campaign_id", "status"),
    )

class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    
    recipient = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False) # success, failed
    message_id = Column(String(255), nullable=True)
    error_info = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="delivery_logs")
    account = relationship("Account", back_populates="delivery_logs")
    events = relationship("DeliveryEvent", back_populates="delivery_log", cascade="all, delete-orphan")

class DeliveryEvent(Base):
    __tablename__ = "delivery_events"

    id = Column(Integer, primary_key=True, index=True)
    delivery_log_id = Column(Integer, ForeignKey("delivery_logs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False) # sent, opened, clicked, bounced, failed
    tracking_id = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow)

    delivery_log = relationship("DeliveryLog", back_populates="events")

class Draft(Base):
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, index=True)
    from_name = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=True)
    recipient = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    attachments = Column(Text, nullable=True) # JSON or comma-separated file names
    sender_account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False) # account_created, campaign_started, email_sent, etc.
    severity = Column(String(20), default="info") # info, warning, error
    message = Column(Text, nullable=False)
    entity_id = Column(Integer, nullable=True)
    lead_email = Column(String(255), nullable=True)
    account_name = Column(String(100), nullable=True)
    status = Column(String(50), nullable=True, default="SENT")
    provider_type = Column(String(50), nullable=True)
    provider_message_id = Column(String(255), nullable=True)
    error_code = Column(String(50), nullable=True)
    campaign_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
EmailTemplate = Template

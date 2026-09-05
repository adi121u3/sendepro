import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import (
    Account, AccountCredential, Lead, Template, Campaign,
    CampaignRecipient, DeliveryLog, ActivityLog, Setting
)
from backend.security.encryption import encrypt_credential, decrypt_credential

TEST_DB_URL = "sqlite:///./test_email_sender.db"

@pytest.fixture(scope="function")
def db_session():
    # Setup test engine
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test_email_sender.db"):
            try:
                os.remove("./test_email_sender.db")
            except Exception:
                pass

def test_encryption_helper():
    plaintext = "super_secret_smtp_password_123!"
    encrypted = encrypt_credential(plaintext)
    assert encrypted != plaintext
    decrypted = decrypt_credential(encrypted)
    assert decrypted == plaintext

def test_create_account_and_credentials(db_session):
    account = Account(
        provider="smtp",
        name="Main SMTP",
        email="sender@example.com",
        from_name="Company Sender",
        enabled=True,
        daily_limit=1000,
        status="idle"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    assert account.id is not None
    assert account.email == "sender@example.com"

    # Add secure credentials
    enc_pw = encrypt_credential("mypassword123")
    cred = AccountCredential(
        account_id=account.id,
        smtp_password_enc=enc_pw
    )
    db_session.add(cred)
    db_session.commit()
    db_session.refresh(cred)

    assert cred.id is not None
    assert decrypt_credential(cred.smtp_password_enc) == "mypassword123"
    assert account.credential.id == cred.id

def test_lead_creation_and_uniqueness(db_session):
    lead1 = Lead(
        first_name="Alice",
        last_name="Smith",
        email="alice@company.com",
        company="Company A",
        position="CEO"
    )
    db_session.add(lead1)
    db_session.commit()

    # Attempt duplicate email lead should fail uniqueness constraint or raise exception
    import sqlalchemy.exc
    lead_dup = Lead(
        first_name="Bob",
        last_name="Jones",
        email="alice@company.com",
        company="Company B"
    )
    db_session.add(lead_dup)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_template_creation(db_session):
    tpl = Template(
        name="Welcome Email",
        subject="Hello {{FirstName}}",
        body_html="<p>Hi {{FirstName}}, welcome to {{Company}}!</p>"
    )
    db_session.add(tpl)
    db_session.commit()
    db_session.refresh(tpl)

    assert tpl.id is not None
    assert tpl.name == "Welcome Email"

def test_campaign_and_queue_relationship(db_session):
    account = Account(provider="zeptomail", name="Zepto Sender", email="z@example.com")
    tpl = Template(name="Cold Outreach", subject="Quick question", body_html="Hi")
    lead = Lead(first_name="John", last_name="Doe", email="john@example.com", company="Acme")
    
    db_session.add_all([account, tpl, lead])
    db_session.commit()

    campaign = Campaign(
        name="Q3 Outreach",
        status="draft",
        template_id=tpl.id,
        account_id=account.id,
        total_recipients=1
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)

    # Add recipient to queue
    recipient = CampaignRecipient(
        campaign_id=campaign.id,
        lead_id=lead.id,
        status="queued"
    )
    db_session.add(recipient)
    db_session.commit()
    db_session.refresh(recipient)

    assert recipient.id is not None
    assert recipient.campaign.name == "Q3 Outreach"
    assert recipient.lead.email == "john@example.com"
    assert len(campaign.recipients) == 1

def test_delivery_and_activity_logs(db_session):
    log = DeliveryLog(
        recipient="test@example.com",
        provider="smtp",
        status="success",
        message_id="msg-12345"
    )
    act = ActivityLog(
        event_type="account_created",
        severity="info",
        message="SMTP account created successfully."
    )
    setting = Setting(key="max_threads", value="4")

    db_session.add_all([log, act, setting])
    db_session.commit()

    assert log.id is not None
    assert act.id is not None
    assert setting.value == "4"

def test_database_persistence_across_sessions():
    """Explicitly verify: Create record -> Close session/engine -> Open new session -> Record still exists"""
    db_file = "./persistence_test.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    db_url = f"sqlite:///{db_file}"
    engine1 = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine1)
    Session1 = sessionmaker(bind=engine1)
    
    session1 = Session1()
    lead = Lead(first_name="Persistent", last_name="User", email="persist@test.com", company="TestCorp")
    session1.add(lead)
    session1.commit()
    session1.close()
    engine1.dispose()

    # Open new session with new engine instance
    engine2 = create_engine(db_url, connect_args={"check_same_thread": False})
    Session2 = sessionmaker(bind=engine2)
    session2 = Session2()

    fetched = session2.query(Lead).filter_by(email="persist@test.com").first()
    assert fetched is not None
    assert fetched.first_name == "Persistent"
    assert fetched.company == "TestCorp"

    session2.close()
    engine2.dispose()

    if os.path.exists(db_file):
        os.remove(db_file)

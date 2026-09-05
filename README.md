# Email Sender Pro

Email Sender Pro is a Windows desktop email marketing and campaign automation application built with Python, PySide6, SQLite, SMTP transports, OAuth2 email authentication, and ZeptoMail API support.

It is designed for sending personalized email campaigns from managed SMTP accounts, tracking delivery activity, and organizing lead lists, templates, and account settings in a local desktop workflow.

## Database Persistence and Backups

The default SQLite database is stored at the project root as `email_sender_pro.db`, regardless of the directory used to start the backend. Startup migrations only add missing schema elements; they do not reset or delete application data.

Create a backup before upgrades or schema changes:

```powershell
python scripts/database_backup.py backup
```

Restore a backup while the backend is stopped:

```powershell
python scripts/database_backup.py restore backups\email_sender_pro_YYYYMMDD_HHMMSS.db
```

The restore command requires typing `RESTORE` and should only be used after making a current backup.

---

## Overview

This project is a complete desktop campaign sender with these main responsibilities:

- managing sender accounts and SMTP providers
- importing and organizing leads
- creating and editing email templates
- personalizing content with variables
- running campaigns in the background
- sending mail through SMTP or API-based providers
- recording delivery results, failures, and campaign activity

The app is not just a single mail script. It is a small campaign system with UI, database, worker threads, transport layer, and campaign processing engine.

---

## Main Features

### 1. Account Management

- Add, edit, and manage email sender accounts
- Support for:
  - Generic SMTP
  - Gmail SMTP
  - Microsoft 365 / Outlook SMTP
  - Bell / Sympatico SMTP
  - Custom SMTP servers
  - ZeptoMail API
- Security types include:
  - `starttls`
  - `ssl`
  - `none`
  - `oauth2`
- OAuth2 support for Microsoft Outlook / Office 365 with browser login and token capture flow
- Credentials are stored safely through the Windows credential system or supported secret storage abstraction

### 2. Leads and Contact Management

- Add leads manually or import from CSV/TXT/XLSX-like workflows
- Store lead metadata such as:
  - first name
  - last name
  - company
  - position
  - sender name
  - receiver name
  - email address
- Support search/filtering and processing of large contact lists
- Deduplication and validation logic can be layered in before sending

### 3. Email Template System

- Create and manage reusable email templates
- Support both HTML and plain text messages
- Dynamic personalization through Jinja-like rendering using variables like:
  - `{{FirstName}}`
  - `{{Company}}`
  - `{{Position}}`
  - custom lead data fields
- Strict validation helps prevent broken template rendering

### 4. Campaign Engine

- Run campaigns in a background worker thread
- Manage campaign lifecycle:
  - start
  - pause
  - resume
  - stop
  - complete
  - fail
- Schedule delays and jitter between sends
- Process campaign tasks one by one
- Update campaign progress and status in the database

### 5. Sending Logic

- Send emails using account-specific transports
- Supports SMTP and API-based delivery depending on provider type
- Handles retries and failures gracefully
- Logs each task result and campaign outcome
- Uses a transport manager to select the correct delivery backend dynamically

### 6. Activity and Tracking

- Keep a delivery log for sent, failed, and skipped messages
- Track account status and sent count
- Audit campaign actions and connection results
- Surface operational state in the UI dashboard

### 7. Security

- Local credential storage for SMTP passwords and OAuth access tokens
- Secret retrieval from Windows credential store or secure backend storage
- Reduced risk of storing secrets directly in plaintext inside app state

---

## Sending Logic Structure

The project follows a clear sending pipeline.

### 1. Account selection

Each account is stored in SQLite and contains fields such as:

- account name
- provider type
- provider preset
- SMTP host and port
- security type
- username
- from email
- from name
- credential key
- daily limits

The app groups accounts by type, such as SMTP, OAuth SMTP, and ZeptoMail.

### 2. Transport selection

The entry point is the transport manager:

- `app/transport/manager.py`

It decides which transport should be used based on `provider_type`:

- SMTP providers use `SMTPTransport`
- ZeptoMail providers use `ZeptoMailTransport`

This makes the system modular and easy to extend with new providers.

### 3. SMTP transport behavior

The SMTP delivery logic is implemented in:

- `app/transport/smtp_transport.py`

It can:

- open a connection to the SMTP server
- upgrade to TLS using STARTTLS when needed
- connect with direct SSL on port 465 when configured
- authenticate with username/password or OAuth2
- send a full email message using `EmailMessage`
- report success or failure back to the caller

For OAuth2, the app authenticates with the SMTP XOAUTH2 format using a bearer access token.

### 4. Campaign processing

The campaign engine is implemented in:

- `app/campaign/engine.py`

It executes a campaign loop that:

- fetches the next available lead task
- renders the email content for that lead
- loads the configured sender account
- sends the message via the selected transport
- marks the task as sent, failed, or skipped
- waits based on campaign pacing and jitter settings

### 5. Background execution

The worker thread is in:

- `app/campaign/worker.py`

This keeps the GUI responsive while a campaign runs in the background. It emits progress and status updates to the UI thread.

### 6. Persistence and state

The database layer is in:

- `app/database/db.py`

It manages SQLite tables for:

- accounts
- leads
- templates
- campaigns
- tasks
- activity logs

This gives the app a reliable local state without requiring external infrastructure.

---

## Microsoft OAuth Flow

The app supports Microsoft 365 / Outlook SMTP with OAuth2 authentication.

### Flow

1. User selects an Outlook / Microsoft 365 account in the UI
2. The app opens the Microsoft authorization page in the browser
3. The user signs in and approves the request
4. Microsoft redirects back to a local callback URL
5. The app captures the authorization code
6. The app exchanges the code for an access token
7. The token is stored in the password field for SMTP XOAUTH2 use

The callback logic is implemented in the account dialog and is designed to work with a localhost redirect such as:

- `http://127.0.0.1:4567/callback`

This allows the desktop app to complete the OAuth workflow without forcing the user to manually paste a token.

---

## Project Structure

```text
email-sender-pro0/
├── app/
│   ├── campaign/
│   │   ├── engine.py
│   │   └── worker.py
│   ├── core/
│   │   ├── config.py
│   │   └── logger.py
│   ├── database/
│   │   └── db.py
│   ├── personalization/
│   │   └── renderer.py
│   ├── providers/
│   │   └── presets.py
│   ├── security/
│   │   └── credentials.py
│   ├── services/
│   │   ├── account_service.py
│   │   ├── campaign_service.py
│   │   ├── draft_service.py
│   │   ├── lead_service.py
│   │   └── template_service.py
│   ├── transport/
│   │   ├── base.py
│   │   ├── manager.py
│   │   ├── smtp_transport.py
│   │   └── zeptomail_transport.py
│   └── ui/
│       ├── amber_theme.py
│       ├── components.py
│       ├── main_window.py
│       ├── styles.py
│       ├── dialogs/
│       ├── pages/
│       └── widgets/
├── tests/
│   ├── test_database.py
│   ├── test_personalization.py
│   └── test_transports.py
├── main.py
├── build.bat
├── requirements.txt
├── package.json
├── vite.config.ts
├── index.html
├── metadata.json
├── .env.example
├── README.md
└── assets/
```

---

## Main Application Flow

When the app is launched:

1. `main.py` creates the Qt application and opens the main window
2. `MainWindow` loads the UI tabs and pages
3. Users create or manage accounts, leads, templates, and campaigns
4. Campaign tasks are created and stored in SQLite
5. The campaign worker executes sending logic in the background
6. SMTP or API transports deliver the email
7. Results are logged back into the app and database

---

## Installation

### Requirements

- Python 3.11+
- Windows environment for desktop integration
- PySide6
- SQLite support
- Optional Windows credential manager support

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the app

```bash
python main.py
```

---

## Packaging for Windows

A packaging script is included:

```bash
build.bat
```

This is intended to build a Windows executable version of the app with PyInstaller or similar build tooling.

---

## Example Workflow

1. Open the app
2. Add a sender account
3. Configure SMTP host, port, and security type
4. Import leads
5. Create a template with placeholders
6. Start a campaign
7. Monitor delivery progress and logs
8. Review sent/failed activity in the dashboard

---

## Notes

This project is designed as a practical desktop email automation tool rather than a generic library. It is intended for local Windows use where SMTP credentials and campaign activity can be managed directly.

The architecture is intentionally modular so that new providers, transport types, or campaign workflows can be added without rewriting the core application logic.

---

## Future Extension Possibilities

- additional providers beyond SMTP and ZeptoMail
- improved lead validation and segmentation
- contact grouping and campaign scheduling
- better analytics dashboards
- export of campaign reports
- stronger security and secret rotation support

---

## Summary

Email Sender Pro is a Windows desktop campaign sender that combines:

- SMTP and OAuth2 email sending
- campaign automation
- customizable templates
- lead handling
- local database storage
- background processing
- UI-driven workflows

It is a complete system for running personalized email outreach from a local desktop environment with a structured, modular codebase.

# Mailer Library Guidelines

This library provides a minimal client for sending plain text emails via SMTP.

## Install

```bash
pip install -e libs/mailer
```

## Usage

```python
from mailer import EmailClient, EmailConfig

config = EmailConfig(
    smtp_server="smtp.example.com",
    smtp_port=587,
    username="user",
    password="pass",
)
client = EmailClient(config)
client.send_email("Hi", "Hello there", "me@example.com", ["you@example.com"])
```

## Testing
- Patch `smtplib.SMTP`; do not send real emails.
- Place tests under `tests/` and name files `test_*.py`.

## Style
- Follow repository conventions from the root `AGENTS.md`.

---
name: send-email
description: "Send emails with Markdown content, attachments, and multi-recipient support via SMTP. Use when Claude needs to send emails programmatically, including scenarios like: (1) Sending notifications or reports via email, (2) Sending Markdown-formatted content as HTML emails, (3) Sending emails with attachments, (4) Sending to multiple recipients with CC/BCC, (5) Configuring SMTP for different email providers (Gmail, QQ, 163, Outlook, etc.)"
author: Viva5649
license: MIT
---

# Email Sender

Send professional HTML emails with Markdown content, attachments, and flexible SMTP configuration.

## Quick Start

### Install dependencies

```bash
pip install -r scripts/requirements.txt
```

### Send a basic email

```bash
python scripts/send_email.py \
  --smtp-server smtp.gmail.com \
  --smtp-port 465 \
  --use-ssl \
  --sender-email "your-email@gmail.com" \
  --sender-password "your-app-password" \
  --to recipient@example.com \
  --subject "Test Email" \
  --markdown "# Hello\n\nThis is a test email."
```

## Configuration

Three methods to configure SMTP (in priority order):

1. **Command-line arguments** - Highest priority, most flexible
2. **Environment variables** - Recommended for security
3. **Configuration file** - Traditional approach

### Environment Variables (Recommended)

```bash
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT=465
export SMTP_USE_SSL=true
export SMTP_SENDER_EMAIL="your-email@gmail.com"
export SMTP_SENDER_AUTH_CODE="your-app-password"
```

### Configuration File

Copy the template and customize:

```bash
cp assets/config.json.example config.json
# Edit config.json with your SMTP settings
```

For common email provider configurations, see [references/smtp_configs.md](references/smtp_configs.md).

## Core Capabilities

### Send to Multiple Recipients

```bash
python scripts/send_email.py \
  --to user1@gmail.com user2@qq.com user3@163.com \
  --subject "Team Update" \
  --markdown "# Important Notice\n\nPlease review."
```

### Send with Attachments

```bash
python scripts/send_email.py \
  --to recipient@example.com \
  --subject "Monthly Report" \
  --markdown "# Report\n\nSee attached." \
  --attachments report.pdf data.xlsx
```

### Send with CC and BCC

```bash
python scripts/send_email.py \
  --to recipient@example.com \
  --cc manager@company.com \
  --bcc archive@company.com \
  --subject "Project Update" \
  --markdown "# Status\n\nOn track."
```

### Use Markdown File

```bash
python scripts/send_email.py \
  --to recipient@example.com \
  --subject "Newsletter" \
  --file newsletter.md
```

## Markdown Support

The email sender converts Markdown to styled HTML automatically. Supported features:

- Headings (H1-H6)
- Bold, italic, strikethrough
- Code blocks with syntax highlighting
- Tables
- Lists (ordered/unordered)
- Blockquotes
- Links and images
- Horizontal rules

## Command-line Arguments

### Required Arguments

- `--to` - Recipient email(s), space-separated for multiple
- `--subject` - Email subject line
- `--file` or `--markdown` - Content source (one required)

### Optional Arguments

- `--attachments` - File path(s) to attach
- `--cc` - CC recipient(s)
- `--bcc` - BCC recipient(s)
- `--config` - Config file path (default: config.json)

### SMTP Configuration Arguments

- `--smtp-server` - SMTP server address
- `--smtp-port` - SMTP port number
- `--use-ssl` - Enable SSL connection
- `--use-tls` - Enable TLS connection
- `--sender-email` - Sender email address
- `--sender-password` - Sender password/auth code

## Python Module Usage

```python
from send_email import EmailSender

# Initialize
sender = EmailSender('config.json')

# Send with Markdown string
sender.send_email(
    recipients=['user@example.com'],
    subject='Test',
    markdown_content='# Hello\n\nTest email.'
)

# Send with file and attachments
sender.send_email(
    recipients=['user1@gmail.com', 'user2@qq.com'],
    subject='Report',
    markdown_file='report.md',
    attachments=['data.pdf'],
    cc=['manager@company.com']
)
```

## Common Email Providers

Quick reference for popular providers:

**Gmail**: smtp.gmail.com:465 (SSL) - Requires app-specific password
**QQ Mail**: smtp.qq.com:465 (SSL) - Requires authorization code
**163 Mail**: smtp.163.com:465 (SSL) - Requires authorization code
**Outlook**: smtp-mail.outlook.com:587 (TLS) - Uses account password

For detailed configurations, see [references/smtp_configs.md](references/smtp_configs.md).

## Examples

For comprehensive usage examples including:
- Daily reports
- Notification templates
- Bulk emails
- Integration patterns

See [references/examples.md](references/examples.md).

## Troubleshooting

**Authentication failed**: Verify credentials and use app-specific passwords (Gmail) or authorization codes (QQ/163)

**Connection timeout**: Check SMTP server address, port, and SSL/TLS settings

**Attachment issues**: Verify file paths exist and check size limits (typically 20-25MB)

## Security Notes

- Use environment variables for credentials in production
- Never commit config.json with credentials to version control
- Use app-specific passwords instead of account passwords
- Limit config file permissions: `chmod 600 config.json`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Viva5649**

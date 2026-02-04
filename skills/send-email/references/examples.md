# Email Sender Usage Examples

## Basic Usage

### Send to single recipient with Markdown content

```bash
python scripts/send_email.py \
  --to recipient@example.com \
  --subject "Test Email" \
  --markdown "# Hello\n\nThis is a test email."
```

### Send to multiple recipients

```bash
python scripts/send_email.py \
  --to user1@gmail.com user2@qq.com user3@163.com \
  --subject "Important Notice" \
  --markdown "# Team Update\n\nPlease review the attached document."
```

### Send with attachments

```bash
python scripts/send_email.py \
  --to recipient@example.com \
  --subject "Monthly Report" \
  --markdown "# Report\n\nPlease find the report attached." \
  --attachments report.pdf data.xlsx
```

### Send with CC and BCC

```bash
python scripts/send_email.py \
  --to recipient@example.com \
  --cc manager@company.com \
  --bcc archive@company.com \
  --subject "Project Update" \
  --markdown "# Status Update\n\nProject is on track."
```

## Configuration Methods

### Method 1: Environment Variables (Recommended)

```bash
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT=465
export SMTP_USE_SSL=true
export SMTP_SENDER_EMAIL="your-email@gmail.com"
export SMTP_SENDER_AUTH_CODE="your-app-password"

python scripts/send_email.py \
  --to recipient@example.com \
  --subject "Test" \
  --markdown "# Hello"
```

### Method 2: Command-line Arguments

```bash
python scripts/send_email.py \
  --smtp-server smtp.gmail.com \
  --smtp-port 465 \
  --use-ssl \
  --sender-email "your-email@gmail.com" \
  --sender-password "your-app-password" \
  --to recipient@example.com \
  --subject "Test" \
  --markdown "# Hello"
```

### Method 3: Configuration File

Create `config.json`:

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 465,
  "use_ssl": true,
  "sender_email": "your-email@gmail.com",
  "sender_password": "your-app-password"
}
```

Then run:

```bash
python scripts/send_email.py \
  --config config.json \
  --to recipient@example.com \
  --subject "Test" \
  --markdown "# Hello"
```

## Markdown Features

The email sender supports full Markdown syntax:

```markdown
# Heading 1
## Heading 2

**Bold text** and *italic text*

- Bullet list
- Another item

1. Numbered list
2. Second item

> Blockquote

`inline code`

\`\`\`python
# Code block with syntax highlighting
def hello():
    print("Hello, World!")
\`\`\`

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |

[Link text](https://example.com)
```

## Python Module Usage

```python
from send_email import EmailSender

# Initialize with config file
sender = EmailSender('config.json')

# Send email with Markdown file
sender.send_email(
    recipients=['user1@gmail.com', 'user2@qq.com'],
    subject='Test Email',
    markdown_file='message.md',
    attachments=['report.pdf'],
    cc=['manager@company.com']
)

# Send email with Markdown string
sender.send_email(
    recipients=['user@example.com'],
    subject='Quick Notice',
    markdown_content='# Urgent\n\nSystem maintenance tonight.'
)
```

## Common Patterns

### Daily Report Email

```bash
python scripts/send_email.py \
  --to team@company.com \
  --subject "Daily Report - $(date +%Y-%m-%d)" \
  --markdown "# Daily Report\n\n## Metrics\n- Users: 1,234\n- Revenue: $5,678" \
  --attachments daily_report.pdf
```

### Notification with Template

```bash
# Create template file
cat > notification.md << 'EOF'
# System Notification

Dear User,

Your request has been processed successfully.

**Details:**
- Request ID: {request_id}
- Status: Completed
- Timestamp: {timestamp}

Best regards,
System Team
EOF

# Send notification
python scripts/send_email.py \
  --to user@example.com \
  --subject "Request Completed" \
  --file notification.md
```

### Bulk Email to Multiple Recipients

```bash
# Read recipients from file
RECIPIENTS=$(cat recipients.txt | tr '\n' ' ')

python scripts/send_email.py \
  --to $RECIPIENTS \
  --subject "Newsletter - February 2026" \
  --file newsletter.md \
  --attachments newsletter.pdf
```

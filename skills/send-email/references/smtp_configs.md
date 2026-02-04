# SMTP Configuration Reference

Common email provider SMTP configurations for use with the email sender.

## Gmail

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 465,
  "use_ssl": true,
  "sender_email": "your-email@gmail.com",
  "sender_password": "your-app-password"
}
```

**Requirements:**
- Enable 2-factor authentication
- Generate app-specific password at https://myaccount.google.com/apppasswords

## QQ Mail (QQ邮箱)

```json
{
  "smtp_server": "smtp.qq.com",
  "smtp_port": 465,
  "use_ssl": true,
  "sender_email": "your-email@qq.com",
  "sender_password": "authorization-code"
}
```

**Requirements:**
- Enable SMTP service in mailbox settings
- Use authorization code (not login password)

## 163 Mail (163邮箱)

```json
{
  "smtp_server": "smtp.163.com",
  "smtp_port": 465,
  "use_ssl": true,
  "sender_email": "your-email@163.com",
  "sender_password": "authorization-code"
}
```

**Requirements:**
- Enable SMTP service in mailbox settings
- Use authorization code (not login password)

## Outlook / Hotmail

```json
{
  "smtp_server": "smtp-mail.outlook.com",
  "smtp_port": 587,
  "use_ssl": false,
  "use_tls": true,
  "sender_email": "your-email@outlook.com",
  "sender_password": "your-password"
}
```

## Tencent Enterprise Mail (腾讯企业邮)

```json
{
  "smtp_server": "smtp.exmail.qq.com",
  "smtp_port": 465,
  "use_ssl": true,
  "sender_email": "your-email@yourcompany.com",
  "sender_password": "your-password"
}
```

## Environment Variables

All SMTP configurations can be provided via environment variables (highest priority):

| Variable | Description |
|----------|-------------|
| `SMTP_SERVER` | SMTP server address |
| `SMTP_PORT` | SMTP port number |
| `SMTP_USE_SSL` | Use SSL connection (true/false) |
| `SMTP_USE_TLS` | Use TLS connection (true/false) |
| `SMTP_SENDER_EMAIL` | Sender email address |
| `SMTP_SENDER_AUTH_CODE` | Sender password/auth code |

## Configuration Priority

The script reads configuration in this priority order (higher overrides lower):

1. Command-line arguments (`--smtp-server`, `--sender-email`, etc.)
2. Environment variables (`SMTP_SERVER`, `SMTP_SENDER_EMAIL`, etc.)
3. Configuration file (`config.json`)

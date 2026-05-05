#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送脚本 - 支持多域名、多收件人、Markdown内容和附件
适用于 Docker 环境
"""

import smtplib
import json
import os
import subprocess
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional
import markdown


class EmailSender:
    """邮件发送器类"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化邮件发送器
        
        Args:
            config_path: 配置文件路径
        """
        self._interactive_smtp_env = None
        self.config = self._load_config(config_path)

    def _load_interactive_smtp_env(self) -> dict:
        """从交互式 zsh 环境读取 SMTP 变量，兼容 ~/.zshrc 中的配置"""
        if self._interactive_smtp_env is not None:
            return self._interactive_smtp_env

        try:
            result = subprocess.run(
                ['zsh', '-ic', 'env'],
                capture_output=True,
                text=True,
                check=True
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            self._interactive_smtp_env = {}
            return self._interactive_smtp_env

        smtp_env = {}
        for line in result.stdout.splitlines():
            if '=' not in line:
                continue

            key, value = line.split('=', 1)
            if key.startswith('SMTP_') and value:
                smtp_env[key] = value

        self._interactive_smtp_env = smtp_env
        return self._interactive_smtp_env

    def _get_smtp_env(self, env_name: str) -> Optional[str]:
        """优先读取当前环境，缺失时回退到交互式 zsh 环境"""
        current_value = os.getenv(env_name)
        if current_value:
            return current_value

        fallback_value = self._load_interactive_smtp_env().get(env_name)
        if fallback_value:
            print(f"提示: 当前环境缺少 {env_name}，已从交互式 zsh 环境回退加载")

        return fallback_value

    @staticmethod
    def _parse_env_bool(value: str) -> bool:
        """解析环境变量中的布尔值"""
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
        
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件，支持环境变量覆盖，并在缺失时回退到交互式 zsh 环境"""
        # 如果配置文件不存在，返回空配置（允许完全通过环境变量/命令行参数配置）
        if not os.path.exists(config_path):
            print(f"提示: 配置文件不存在: {config_path}，将使用环境变量或命令行参数")
            config = {}
        else:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

        # 从环境变量读取 SMTP 配置（优先级高于配置文件，缺失时回退 zsh -ic）
        smtp_server = self._get_smtp_env('SMTP_SERVER')
        smtp_port = self._get_smtp_env('SMTP_PORT')
        smtp_use_ssl = self._get_smtp_env('SMTP_USE_SSL')
        smtp_use_tls = self._get_smtp_env('SMTP_USE_TLS')
        sender_email = self._get_smtp_env('SMTP_SENDER_EMAIL')
        sender_auth_code = self._get_smtp_env('SMTP_SENDER_AUTH_CODE')

        if smtp_server:
            config['smtp_server'] = smtp_server
        if smtp_port:
            config['smtp_port'] = int(smtp_port)
        if smtp_use_ssl:
            config['use_ssl'] = self._parse_env_bool(smtp_use_ssl)
        if smtp_use_tls:
            config['use_tls'] = self._parse_env_bool(smtp_use_tls)
        if sender_email:
            config['sender_email'] = sender_email
        if sender_auth_code:
            config['sender_password'] = sender_auth_code
        
        # 验证必需的配置项
        required_fields = ['smtp_server', 'smtp_port', 'sender_email', 'sender_password']
        missing_fields = [field for field in required_fields if field not in config or not config[field]]
        
        if missing_fields:
            raise ValueError(
                f"缺少必需的配置: {', '.join(missing_fields)}\n"
                f"请通过以下方式之一提供:\n"
                f"  1. 当前 shell 环境变量\n"
                f"  2. ~/.zshrc 等交互式 zsh 环境变量\n"
                f"  3. 配置文件 (config.json)\n"
                f"  4. 命令行参数 (--smtp-server, --smtp-port, --sender-email, --sender-password)"
            )
        
        return config
    
    def _read_markdown_file(self, file_path: str) -> tuple[str, str]:
        """
        读取 Markdown 文件并转换为 HTML
        
        Args:
            file_path: Markdown 文件路径
            
        Returns:
            (原始markdown文本, HTML文本)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Markdown 文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # 转换为 HTML
        html_content = markdown.markdown(
            md_content,
            extensions=['extra', 'codehilite', 'tables', 'fenced_code']
        )
        
        # 添加基本样式
        html_with_style = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3 {{
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                }}
                code {{
                    background-color: #f6f8fa;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                }}
                pre {{
                    background-color: #f6f8fa;
                    padding: 16px;
                    border-radius: 6px;
                    overflow: auto;
                }}
                blockquote {{
                    border-left: 4px solid #ddd;
                    padding-left: 16px;
                    color: #666;
                    margin-left: 0;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                table th, table td {{
                    border: 1px solid #ddd;
                    padding: 8px 12px;
                    text-align: left;
                }}
                table th {{
                    background-color: #f6f8fa;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        return md_content, html_with_style
    
    def send_email(
        self,
        recipients: List[str],
        subject: str,
        markdown_file: Optional[str] = None,
        markdown_content: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        发送邮件
        
        Args:
            recipients: 收件人列表
            subject: 邮件主题
            markdown_file: Markdown 文件路径（与 markdown_content 二选一）
            markdown_content: Markdown 内容字符串（与 markdown_file 二选一）
            attachments: 附件文件路径列表
            cc: 抄送列表
            bcc: 密送列表
            
        Returns:
            发送是否成功
        """
        try:
            # 创建邮件对象
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['sender_email']
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            # 处理 Markdown 内容
            if markdown_file:
                md_text, html_text = self._read_markdown_file(markdown_file)
            elif markdown_content:
                md_text = markdown_content
                html_text = markdown.markdown(
                    markdown_content,
                    extensions=['extra', 'codehilite', 'tables', 'fenced_code']
                )
            else:
                raise ValueError("必须提供 markdown_file 或 markdown_content")
            
            # 添加纯文本和 HTML 版本
            part_text = MIMEText(md_text, 'plain', 'utf-8')
            part_html = MIMEText(html_text, 'html', 'utf-8')
            
            msg.attach(part_text)
            msg.attach(part_html)
            
            # 添加附件
            if attachments:
                for file_path in attachments:
                    if not os.path.exists(file_path):
                        print(f"警告: 附件文件不存在，跳过: {file_path}")
                        continue
                    
                    with open(file_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                    
                    encoders.encode_base64(part)
                    filename = os.path.basename(file_path)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    msg.attach(part)
            
            # 合并所有收件人
            all_recipients = recipients.copy()
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)
            
            # 连接 SMTP 服务器并发送
            # 如果没有明确配置，默认使用 SSL（最常见的配置）
            use_ssl = self.config.get('use_ssl', True)
            
            if use_ssl:
                server = smtplib.SMTP_SSL(
                    self.config['smtp_server'],
                    self.config['smtp_port']
                )
            else:
                server = smtplib.SMTP(
                    self.config['smtp_server'],
                    self.config['smtp_port']
                )
                # 如果没有明确配置，默认不使用 TLS
                if self.config.get('use_tls', False):
                    server.starttls()
            
            server.login(
                self.config['sender_email'],
                self.config['sender_password']
            )
            
            server.send_message(msg)
            server.quit()
            
            print(f"✓ 邮件发送成功!")
            print(f"  收件人: {', '.join(recipients)}")
            if cc:
                print(f"  抄送: {', '.join(cc)}")
            print(f"  主题: {subject}")
            
            return True
            
        except Exception as e:
            print(f"✗ 邮件发送失败: {str(e)}")
            return False


def main():
    """主函数 - 命令行使用示例"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='邮件发送脚本',
        epilog='提示: 可以使用环境变量 SMTP_SENDER_EMAIL 和 SMTP_SENDER_AUTH_CODE 代替配置文件中的敏感信息'
    )
    parser.add_argument('-c', '--config', default='config.json',
                        help='配置文件路径 (默认: config.json)')
    parser.add_argument('-t', '--to', required=True, nargs='+',
                        help='收件人邮箱地址（可以多个）')
    parser.add_argument('-s', '--subject', required=True,
                        help='邮件主题')
    parser.add_argument('-f', '--file',
                        help='Markdown 文件路径')
    parser.add_argument('-m', '--markdown',
                        help='Markdown 内容（字符串）')
    parser.add_argument('-a', '--attachments', nargs='+',
                        help='附件文件路径（可以多个）')
    parser.add_argument('--cc', nargs='+',
                        help='抄送邮箱地址（可以多个）')
    parser.add_argument('--bcc', nargs='+',
                        help='密送邮箱地址（可以多个）')
    
    # SMTP 配置参数
    parser.add_argument('--smtp-server',
                        help='SMTP 服务器地址（覆盖配置文件）')
    parser.add_argument('--smtp-port', type=int,
                        help='SMTP 端口（覆盖配置文件）')
    parser.add_argument('--use-ssl', action='store_true',
                        help='使用 SSL 连接（不传此参数默认为 false）')
    parser.add_argument('--use-tls', action='store_true',
                        help='使用 TLS 连接（不传此参数默认为 false）')
    
    # 认证信息参数
    parser.add_argument('--sender-email',
                        help='发件人邮箱（覆盖配置文件）')
    parser.add_argument('--sender-password',
                        help='发件人密码（覆盖配置文件）')
    
    args = parser.parse_args()
    
    # 检查是否提供了内容
    if not args.file and not args.markdown:
        parser.error("必须提供 --file 或 --markdown 参数")
    
    try:
        # 如果通过命令行参数提供了 SMTP 配置，设置为环境变量
        if args.smtp_server:
            os.environ['SMTP_SERVER'] = args.smtp_server
        if args.smtp_port:
            os.environ['SMTP_PORT'] = str(args.smtp_port)
        # 只有在命令行明确传了 --use-ssl 参数时才设置环境变量
        if args.use_ssl:
            os.environ['SMTP_USE_SSL'] = 'true'
        # 只有在命令行明确传了 --use-tls 参数时才设置环境变量
        if args.use_tls:
            os.environ['SMTP_USE_TLS'] = 'true'
        
        # 如果通过命令行参数提供了认证信息，设置为环境变量
        if args.sender_email:
            os.environ['SMTP_SENDER_EMAIL'] = args.sender_email
        if args.sender_password:
            os.environ['SMTP_SENDER_AUTH_CODE'] = args.sender_password
        
        sender = EmailSender(args.config)
        success = sender.send_email(
            recipients=args.to,
            subject=args.subject,
            markdown_file=args.file,
            markdown_content=args.markdown,
            attachments=args.attachments,
            cc=args.cc,
            bcc=args.bcc
        )
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

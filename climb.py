#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
climb - Command Line Interface Mail Bot V1.1 by Michael Boehm, Cephei AG
Utility to send automated E-Mails with full encryption support - Freeware
"""

import os
import sys
import shlex
import mimetypes
import time
import imaplib
import smtplib
import ssl as sslmod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email import encoders
from email.header import Header
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import format_datetime, make_msgid, parseaddr
from pathlib import Path
from typing import List, Optional, Tuple


# Constants
DEFAULT_CHARSET = "UTF-8"
DEFAULT_PORT_TLS = 587
DEFAULT_PORT_NOCRYPT = 25
DEFAULT_TIMEOUT = 60
MAX_ATTACHMENT_SIZE = 50 * 1024 * 1024  # 50 MB
VERSION = "1.2"


@dataclass
class MailConfig:
    """Configuration for email sending operation."""
    
    # SMTP Settings
    smtp_host: str = ""
    port: int = DEFAULT_PORT_TLS
    timeout: int = DEFAULT_TIMEOUT
    use_ssl: bool = False
    nocrypt: bool = False
    
    # Authentication
    login: str = ""
    password: str = ""
    
    # Email Content
    sender_email: str = ""
    recipients_emails: str = ""
    cc_emails: str = ""
    bcc_emails: str = ""
    mail_subject: str = ""
    mail_body: str = ""
    html_body: str = ""
    character_set: str = DEFAULT_CHARSET
    
    # File Sources
    body_file: str = ""
    html_file: str = ""
    attachment_files: List[str] = field(default_factory=list)
    inline_attachment_file: str = ""
    content_id: str = ""
    
    # Options File
    options_file: str = ""
    
    # IMAP Copy
    copy_email: str = ""
    imap_host: str = ""
    
    # Output
    output_file: str = ""
    
    # Flags
    verbose: bool = False
    receipt: bool = False
    
    def __post_init__(self) -> None:
        """Validate and set derived values after initialization."""
        # Ensure port is int
        if isinstance(self.port, str):
            self.port = int(self.port)
        
        # Ensure timeout is int
        if isinstance(self.timeout, str):
            self.timeout = int(self.timeout)
        
        # Apply nocrypt default port
        if self.nocrypt and self.port == DEFAULT_PORT_TLS:
            self.port = DEFAULT_PORT_NOCRYPT
        
        # SSL and nocrypt are mutually exclusive
        if self.nocrypt and self.use_ssl:
            self.use_ssl = False
        
        # Default sender to login
        if not self.sender_email:
            self.sender_email = self.login
        
        # Default IMAP host to SMTP host
        if self.copy_email and not self.imap_host:
            self.imap_host = self.smtp_host
    
    def validate(self) -> None:
        """Validate configuration. Exits with error if invalid."""
        errors = []
        
        if not self.smtp_host:
            errors.append("SMTP-Server not set")
        if not self.login:
            errors.append("Login username not set")
        if not self.password:
            errors.append("Password not set")
        if not self.recipients_emails:
            errors.append("No mail-recipients given")
        if not self.mail_subject:
            errors.append("Mail subject missing")
        if not self.mail_body:
            errors.append("Text mail body missing")
        if not self.sender_email:
            errors.append("From: E-Mail not set")

        if self.inline_attachment_file and not self.content_id:
            errors.append("Inline attachment requires Content-ID (-cid)")
        if self.content_id and not self.inline_attachment_file:
            errors.append("Content-ID (-cid) requires inline attachment (-ai)")
        if self.content_id and ("<" in self.content_id or ">" in self.content_id):
            errors.append("Content-ID must be provided without <>")
        if self.inline_attachment_file and not self.html_body:
            errors.append("Inline attachment requires HTML body (-ht/-hf)")
        
        if errors:
            for err in errors:
                print(err)
            print("Use climb -h for help")
            sys.exit(1)
        
        # Validate port range
        if not (1 <= self.port <= 65535):
            print(f"Invalid port: must be between 1 and 65535, got {self.port}", file=sys.stderr)
            sys.exit(1)
        
        # Validate timeout
        if self.timeout <= 0:
            print(f"Invalid timeout: must be a positive integer, got {self.timeout}", file=sys.stderr)
            sys.exit(1)
        
        # Validate sender email format
        if not validate_email(self.sender_email):
            print(f"Invalid sender email address: '{self.sender_email}'", file=sys.stderr)
            sys.exit(1)
        
        # Validate recipient email formats (fail fast)
        recipients_list = split_addrs(self.recipients_emails)
        if not recipients_list:
            print("No valid mail-recipients given", file=sys.stderr)
            sys.exit(1)
        validate_email_list(recipients_list, "To")


def usage() -> None:
    """Print usage information and exit."""
    print(
        f"climb - Command Line Interface Mail Bot V{VERSION} by Michael Boehm, Cephei AG\n"
        "Utility to send automated E-Mails with full encryption support - Freeware\n"
        "Usage: climb [options]\n"
        "Case-insensitive options, and [arguments] that follow them:\n"
        "-s  or -server   : SMTP [Server] to use\n"
        "-p  or -port     : Server [Port] (Default 587 for encrypted connections)\n"
        "-tm or -timeout  : Network timeout in seconds (Default 60)\n"
        "-ss or -ssl      : Force SSL from beginning of connection (ignored if -nc)\n"
        "-nc or -nocrypt  : Unencrypted connection (don't use SSL; default port 25)\n"
        "-u  or -user     : [Username] for login\n"
        "-pw or -password : [Password] for login ('-' for stdin or set CLIMB_PASSWORD)\n"
        "-f  or -from     : Sender [E-Mail] (defaults to login username)\n"
        "-t  or -to       : Recipients [E-Mails], comma-separated\n"
        "-c  or -cc       : CC: Recipients [E-Mails], comma-separated\n"
        "-bc or -bcc      : BCC: Recipients [E-Mails], comma-separated\n"
        "-tt or -title    : Mail [Title] (Subject - use quotes for whitespace)\n"
        "-b  or -body     : Mail [Body] (Message Text - use quotes for whitespace)\n"
        "-bf or -bodyF    : [File] to read Mail Body from\n"
        "-ht or -html     : Mail [HTML] (Message HTML - use quotes for whitespace)\n"
        "-hf or -htmlF    : [File] to read Mail HTML Body from\n"
        "-a  or -attach   : Attachment [File or Dir] (Use repeatedly to add more)\n"
        "-ai or -al or -attach-inline : Inline image [File] (requires -cid)\n"
        "-cid or -ci or -content-id : Content-ID for inline image (without <>)\n"
        f"-ch or -charset  : Use this [Charset] for text, default \"{DEFAULT_CHARSET}\"\n"
        "-r  or -receipt  : Request a return receipt\n"
        "-cp or -copy     : Place a copy of Mail into [IMAP Folder] (ignored if -o)\n"
        "-i  or -imap     : IMAP4 [Server] to use (only relevant with -cp; default SMTP)\n"
        "-o  or -output   : Instead of sending mail, create [File] containing mail\n"
        "-v  or -verbose  : Give status info while sending\n"
        "-of or -optionsF : [File] to read options from (CLI options higher prio!)\n"
        "-h  or -help     : Help (this usage)"
    )
    sys.exit(1)


def get_arg(args: List[str], index: int) -> str:
    """Get argument at index+1, exit with error if missing or empty."""
    if index + 1 >= len(args) or args[index + 1].startswith("-") or len(args[index + 1]) == 0:
        print(f"Argument missing for \"{args[index].lower()}\"")
        print("Use climb -h for help")
        sys.exit(1)
    return args[index + 1]


def normalize_option(opt: str) -> str:
    """Normalize option string (handle -- and / prefixes)."""
    opt = opt.lower()
    # Double hyphen equals single hyphen for long form
    # Long options: --ssl (5 chars) vs short: -ss (3 chars)
    # Threshold 4 differentiates between short (-ss) and long (--ssl)
    if opt.startswith("--") and len(opt) > 4:
        opt = opt[1:]
    # For short form, '/' equals '-'
    if len(opt) <= 4 and opt.startswith("/") and not opt.startswith("/-"):
        opt = "-" + opt[1:]
    return opt


def parse_args_to_dict(args: List[str], warn_on_cli_password: bool) -> Tuple[dict, List[str]]:
    """
    Parse arguments into a dictionary and collect attachment files separately.
    Returns (config_dict, attachment_files).
    """
    config_dict = {}
    attachments = []
    
    i = 0
    while i < len(args):
        opt = normalize_option(args[i])
        
        if opt in ("-user", "-u"):
            config_dict["login"] = get_arg(args, i)
            i += 1
        elif opt in ("-password", "-pw"):
            arg = get_arg(args, i)
            if arg == "-":
                config_dict["password"] = sys.stdin.read().strip("\n")
            else:
                config_dict["password"] = arg
                if warn_on_cli_password and arg:
                    print(
                        "Warning: passing passwords via CLI can expose secrets; "
                        "prefer CLIMB_PASSWORD or stdin.",
                        file=sys.stderr
                    )
            i += 1
        elif opt in ("-server", "-s"):
            config_dict["smtp_host"] = get_arg(args, i)
            i += 1
        elif opt in ("-port", "-p"):
            config_dict["port"] = int(get_arg(args, i))
            i += 1
        elif opt in ("-timeout", "-tm"):
            config_dict["timeout"] = int(get_arg(args, i))
            i += 1
        elif opt in ("-title", "-tt"):
            config_dict["mail_subject"] = get_arg(args, i)
            i += 1
        elif opt in ("-body", "-b"):
            config_dict["mail_body"] = get_arg(args, i)
            config_dict["body_file"] = ""  # Clear file if body is set
            i += 1
        elif opt in ("-bodyf", "-bf"):
            path = get_arg(args, i)
            if not os.path.isfile(path):
                print(f"Text Body File \"{path}\" does not exist.")
                sys.exit(1)
            config_dict["body_file"] = path
            config_dict["mail_body"] = ""  # Clear body if file is set
            i += 1
        elif opt in ("-html", "-ht"):
            config_dict["html_body"] = get_arg(args, i)
            config_dict["html_file"] = ""  # Clear file if html is set
            i += 1
        elif opt in ("-htmlf", "-hf"):
            path = get_arg(args, i)
            if not os.path.isfile(path):
                print(f"HTML Body File \"{path}\" does not exist.")
                sys.exit(1)
            config_dict["html_file"] = path
            config_dict["html_body"] = ""  # Clear html if file is set
            i += 1
        elif opt in ("-from", "-f"):
            config_dict["sender_email"] = get_arg(args, i)
            i += 1
        elif opt in ("-to", "-t"):
            config_dict["recipients_emails"] = get_arg(args, i)
            i += 1
        elif opt in ("-cc", "-c"):
            config_dict["cc_emails"] = get_arg(args, i)
            i += 1
        elif opt in ("-bcc", "-bc"):
            config_dict["bcc_emails"] = get_arg(args, i)
            i += 1
        elif opt in ("-charset", "-ch"):
            config_dict["character_set"] = get_arg(args, i)
            i += 1
        elif opt in ("-attach", "-a"):
            path = get_arg(args, i)
            if os.path.isdir(path):
                for fn in os.listdir(path):
                    filepath = os.path.join(path, fn)
                    if os.path.isfile(filepath):
                        attachments.append(filepath)
            else:
                if not os.path.isfile(path):
                    print(f"Attachment File \"{path}\" does not exist.")
                    sys.exit(1)
                attachments.append(path)
            i += 1
        elif opt in ("-attach-inline", "-ai", "-al"):
            path = get_arg(args, i)
            if config_dict.get("inline_attachment_file"):
                print("Only one inline attachment is supported.")
                sys.exit(1)
            if not os.path.isfile(path):
                print(f"Inline Attachment File \"{path}\" does not exist.")
                sys.exit(1)
            config_dict["inline_attachment_file"] = path
            i += 1
        elif opt in ("-cid", "-ci", "-content-id"):
            config_dict["content_id"] = get_arg(args, i)
            i += 1
        elif opt in ("-optionsf", "-of"):
            path = get_arg(args, i)
            if not os.path.isfile(path):
                print(f"Options File \"{path}\" does not exist.")
                sys.exit(1)
            config_dict["options_file"] = path
            i += 1
        elif opt in ("-output", "-o"):
            config_dict["output_file"] = get_arg(args, i)
            i += 1
        elif opt in ("-copy", "-cp"):
            config_dict["copy_email"] = get_arg(args, i)
            i += 1
        elif opt in ("-ssl", "-ss"):
            config_dict["use_ssl"] = True
        elif opt in ("-receipt", "-r"):
            config_dict["receipt"] = True
        elif opt in ("-nocrypt", "-nc"):
            config_dict["nocrypt"] = True
        elif opt in ("-imap", "-i"):
            config_dict["imap_host"] = get_arg(args, i)
            i += 1
        elif opt in ("-verbose", "-v"):
            config_dict["verbose"] = True
        elif opt in ("-help", "-h", "-?"):
            usage()
        else:
            print(f"Unknown option \"{opt}\"")
            print("Use climb -h for help")
            sys.exit(1)
        
        i += 1
    
    return config_dict, attachments


def merge_configs(base: MailConfig, override: MailConfig) -> MailConfig:
    """Merge two configs, with override taking precedence for non-default values."""
    # Convert to dicts for easier manipulation
    base_dict = base.__dict__.copy()
    override_dict = override.__dict__.copy()
    
    # Fields that should override
    for key, value in override_dict.items():
        if key == "attachment_files":
            # Special handling: merge attachment lists
            if value:
                base_dict[key] = value
        elif key == "options_file":
            # options_file is metadata, don't carry over
            continue
        elif value:
            # For strings, non-empty overrides; for bools, True overrides
            base_dict[key] = value
    
    return MailConfig(**base_dict)


def load_config(args: List[str]) -> MailConfig:
    """Load configuration from CLI args and optionally an options file."""
    # Parse CLI args first to get options_file if specified
    cli_dict, cli_attachments = parse_args_to_dict(args, warn_on_cli_password=True)
    
    # If options file specified, load and parse it
    if cli_dict.get("options_file"):
        options_file = cli_dict["options_file"]
        
        # Check file permissions (must be owner-readable only)
        # Open first, then fstat to avoid TOCTOU race condition
        try:
            fd = os.open(options_file, os.O_RDONLY)
        except OSError as exc:
            print(f"Failed to open options file '{options_file}': {exc}", file=sys.stderr)
            sys.exit(1)
        
        try:
            st = os.fstat(fd)
            if st.st_mode & 0o077:
                print(f"Options file '{options_file}' must not be group/world-readable.", file=sys.stderr)
                sys.exit(1)
            
            # Read from file descriptor
            opts_content = os.read(fd, os.stat(fd).st_size).decode("utf-8")
        except OSError as exc:
            print(f"Failed to read options file '{options_file}': {exc}", file=sys.stderr)
            sys.exit(1)
        finally:
            os.close(fd)
        
        opts_args = shlex.split(opts_content)
        
        # Parse options file (no password warning needed for file)
        file_dict, file_attachments = parse_args_to_dict(opts_args, warn_on_cli_password=False)
        
        # Start with file config
        config = MailConfig(**file_dict)
        config.attachment_files = file_attachments
        
        # Override with CLI args
        cli_config = MailConfig(**cli_dict)
        cli_config.attachment_files = cli_attachments
        
        config = merge_configs(config, cli_config)
    else:
        # Just use CLI args
        config = MailConfig(**cli_dict)
        config.attachment_files = cli_attachments
    
    # Check for password in environment variable if not set
    if not config.password:
        env_password = os.getenv("CLIMB_PASSWORD")
        if env_password is not None:
            config.password = env_password
    
    # Load body from file if specified
    if config.body_file:
        try:
            with open(config.body_file, "r", encoding=config.character_set, errors="replace") as f:
                config.mail_body = f.read()
        except OSError as exc:
            print(f"Failed to read body file '{config.body_file}': {exc}", file=sys.stderr)
            sys.exit(1)
    
    # Load HTML from file if specified
    if config.html_file:
        try:
            with open(config.html_file, "r", encoding=config.character_set, errors="replace") as f:
                config.html_body = f.read()
        except OSError as exc:
            print(f"Failed to read HTML file '{config.html_file}': {exc}", file=sys.stderr)
            sys.exit(1)
    
    return config


def split_addrs(s: str) -> List[str]:
    """Split comma or semicolon separated address string into list."""
    parts = [x.strip() for x in s.replace(";", ",").split(",")]
    addrs = [x for x in parts if x]
    if addrs and any(not x for x in parts):
        print("Warning: empty email address entries were ignored", file=sys.stderr)
    return addrs


def validate_email(addr: str) -> bool:
    """Validate email address format using parseaddr."""
    _, email = parseaddr(addr)
    if not email:
        return False
    if "@" not in email:
        return False
    local, domain = email.rsplit("@", 1)
    if not local or not domain:
        return False
    if domain.lower() == "localhost":
        return True
    if "." not in domain:
        return False
    return True


def validate_email_list(addrs: List[str], field_name: str) -> None:
    """Validate a list of email addresses. Exits with error if any are invalid."""
    for addr in addrs:
        if not validate_email(addr):
            print(f"Invalid email address in {field_name}: '{addr}'", file=sys.stderr)
            sys.exit(1)


def create_email_message(config: MailConfig) -> Tuple[MIMEBase, List[str]]:
    """
    Create email message from config.
    Returns (message, full_recipient_list).
    """
    # Build message structure
    has_inline = bool(config.inline_attachment_file)
    has_html = bool(config.html_body)
    has_attachments = bool(config.attachment_files)

    if has_attachments:
        msg = MIMEMultipart("mixed")
        if has_html or has_inline:
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(config.mail_body, "plain", config.character_set))
            if has_inline:
                related = MIMEMultipart("related")
                related.attach(MIMEText(config.html_body, "html", config.character_set))
                attach_inline_file(
                    related,
                    config.inline_attachment_file,
                    config.character_set,
                    config.content_id,
                )
                alt.attach(related)
            else:
                alt.attach(MIMEText(config.html_body, "html", config.character_set))
            msg.attach(alt)
        else:
            msg.attach(MIMEText(config.mail_body, "plain", config.character_set))
    else:
        if has_inline:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(config.mail_body, "plain", config.character_set))
            related = MIMEMultipart("related")
            related.attach(MIMEText(config.html_body, "html", config.character_set))
            attach_inline_file(
                related,
                config.inline_attachment_file,
                config.character_set,
                config.content_id,
            )
            msg.attach(related)
        elif has_html:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(config.mail_body, "plain", config.character_set))
            msg.attach(MIMEText(config.html_body, "html", config.character_set))
        else:
            msg = MIMEText(config.mail_body, "plain", config.character_set)
    
    # Set headers
    msg["Date"] = format_datetime(datetime.now(timezone.utc).astimezone())
    msg["Message-ID"] = make_msgid()
    msg["Subject"] = Header(config.mail_subject, config.character_set)
    msg["From"] = config.sender_email
    
    if config.receipt:
        msg["Disposition-Notification-To"] = config.sender_email
    
    # Process recipients
    recipients_list = split_addrs(config.recipients_emails)
    validate_email_list(recipients_list, "To")
    msg["To"] = ", ".join(recipients_list)
    email_list = list(recipients_list)
    
    # Process CC
    if config.cc_emails:
        cc_list = split_addrs(config.cc_emails)
        if cc_list:
            validate_email_list(cc_list, "CC")
            msg["CC"] = ", ".join(cc_list)
            email_list += cc_list
    
    # Process BCC (not added to headers)
    if config.bcc_emails:
        bcc_list = split_addrs(config.bcc_emails)
        if bcc_list:
            validate_email_list(bcc_list, "BCC")
            email_list += bcc_list
    
    # Attach files
    for path in config.attachment_files:
        attach_file(msg, path, config.character_set)
    
    return msg, email_list


def attach_file(msg: MIMEMultipart, path: str, charset: str) -> None:
    """Attach a file to the message."""
    # Check file size limit
    try:
        file_size = os.path.getsize(path)
    except OSError as exc:
        print(f"Failed to stat attachment '{path}': {exc}", file=sys.stderr)
        sys.exit(1)
    
    if file_size > MAX_ATTACHMENT_SIZE:
        print(f"Attachment '{path}' exceeds maximum size of {MAX_ATTACHMENT_SIZE // 1024 // 1024} MB.", file=sys.stderr)
        sys.exit(1)
    
    try:
        basename = os.path.basename(path)
        ext = os.path.splitext(basename)[1].lower()
        
        # Handle PDF specifically for proper MIME type
        if ext == ".pdf":
            with open(path, "rb") as f:
                att = MIMEBase("application", "pdf")
                att.set_payload(f.read())
            encoders.encode_base64(att)
            att.add_header("Content-Disposition", "attachment", filename=("utf-8", "", basename))
            msg.attach(att)
            return
        
        # Guess MIME type
        ctype, encoding = mimetypes.guess_type(path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        
        # Create appropriate MIME object
        if maintype == "text":
            with open(path, "r", encoding=charset, errors="replace") as f:
                att = MIMEText(f.read(), subtype, charset)
        elif maintype == "image":
            with open(path, "rb") as f:
                att = MIMEImage(f.read(), subtype)
        elif maintype == "audio":
            with open(path, "rb") as f:
                att = MIMEAudio(f.read(), subtype)
        else:
            with open(path, "rb") as f:
                att = MIMEBase(maintype, subtype)
                att.set_payload(f.read())
            encoders.encode_base64(att)
        
        att.add_header("Content-Disposition", "attachment", filename=("utf-8", "", basename))
        msg.attach(att)
        
    except OSError as exc:
        print(f"Failed to read attachment '{path}': {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Failed to process attachment '{path}': {exc}", file=sys.stderr)
        sys.exit(1)


def attach_inline_file(msg: MIMEMultipart, path: str, charset: str, content_id: str) -> None:
    """Attach a file as inline content with Content-ID."""
    try:
        file_size = os.path.getsize(path)
    except OSError as exc:
        print(f"Failed to stat inline attachment '{path}': {exc}", file=sys.stderr)
        sys.exit(1)

    if file_size > MAX_ATTACHMENT_SIZE:
        print(
            f"Inline attachment '{path}' exceeds maximum size of "
            f"{MAX_ATTACHMENT_SIZE // 1024 // 1024} MB.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        basename = os.path.basename(path)
        ctype, encoding = mimetypes.guess_type(path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        if maintype == "image":
            with open(path, "rb") as f:
                att = MIMEImage(f.read(), subtype)
        elif maintype == "text":
            with open(path, "r", encoding=charset, errors="replace") as f:
                att = MIMEText(f.read(), subtype, charset)
        elif maintype == "audio":
            with open(path, "rb") as f:
                att = MIMEAudio(f.read(), subtype)
        else:
            with open(path, "rb") as f:
                att = MIMEBase(maintype, subtype)
                att.set_payload(f.read())
            encoders.encode_base64(att)

        att.add_header("Content-Disposition", "inline", filename=("utf-8", "", basename))
        att.add_header("Content-ID", f"<{content_id}>")
        msg.attach(att)
    except OSError as exc:
        print(f"Failed to read inline attachment '{path}': {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Failed to process inline attachment '{path}': {exc}", file=sys.stderr)
        sys.exit(1)


def send_smtp(config: MailConfig, msg: MIMEBase, recipients: List[str]) -> bool:
    """
    Send email via SMTP.
    Returns True on success, False on failure.
    """
    try:
        tls_ctx = sslmod.create_default_context()
        
        if config.use_ssl:
            server = smtplib.SMTP_SSL(
                config.smtp_host, 
                config.port, 
                timeout=config.timeout, 
                context=tls_ctx
            )
            server.sock.settimeout(config.timeout)
        else:
            server = smtplib.SMTP(
                config.smtp_host, 
                config.port, 
                timeout=config.timeout
            )
    except (smtplib.SMTPException, OSError, ValueError) as exc:
        print(f"Failed to connect to SMTP server '{config.smtp_host}:{config.port}': {exc}", file=sys.stderr)
        return False
    
    try:
        if config.verbose:
            server.set_debuglevel(1)
        
        if not config.use_ssl and not config.nocrypt:
            server.ehlo()
            server.starttls(context=tls_ctx)
            server.ehlo()
            server.sock.settimeout(config.timeout)
        
        server.login(config.login, config.password)
        server.sendmail(msg["From"], recipients, msg.as_string())
        return True
        
    except (smtplib.SMTPException, OSError, ValueError) as exc:
        print(f"Failed to send mail: {exc}", file=sys.stderr)
        return False
    finally:
        try:
            server.quit()
        except (smtplib.SMTPException, OSError):
            pass


def save_imap_copy(config: MailConfig, msg: MIMEBase) -> None:
    """Save a copy of the message to IMAP folder."""
    if not config.copy_email:
        return
    
    if config.verbose:
        imaplib.Debug = 4
    
    try:
        if config.nocrypt:
            imap_server = imaplib.IMAP4(config.imap_host)
        else:
            imap_server = imaplib.IMAP4_SSL(config.imap_host)
        
        if imap_server.sock is not None:
            imap_server.sock.settimeout(config.timeout)
    except (imaplib.IMAP4.error, OSError, ValueError) as exc:
        print(f"Warning: failed to connect to IMAP server '{config.imap_host}': {exc}", file=sys.stderr)
        return
    
    try:
        imap_server.login(config.login, config.password)
        imap_server.append(
            config.copy_email, 
            "\\Seen", 
            imaplib.Time2Internaldate(time.time()), 
            msg.as_bytes()
        )
    except (imaplib.IMAP4.error, OSError, ValueError) as exc:
        print(f"Warning: failed to store copy in IMAP folder '{config.copy_email}': {exc}", file=sys.stderr)
    finally:
        try:
            imap_server.logout()
        except (imaplib.IMAP4.error, OSError, ValueError) as exc:
            if config.verbose:
                print(f"Warning: IMAP logout failed: {exc}", file=sys.stderr)


def write_output_file(config: MailConfig, msg: MIMEBase) -> bool:
    """Write message to output file instead of sending."""
    try:
        with open(config.output_file, "wb") as f:
            f.write(msg.as_bytes())
        return True
    except OSError as exc:
        print(f"Failed to write output file '{config.output_file}': {exc}", file=sys.stderr)
        return False


def main() -> int:
    """Main entry point."""
    if len(sys.argv) == 1:
        usage()
    
    # Load configuration from arguments
    config = load_config(sys.argv[1:])
    
    # Validate configuration
    config.validate()
    
    # Warn about unencrypted connection with password
    if config.nocrypt and config.password:
        print(
            "Warning: Password will be transmitted unencrypted (-nocrypt). "
            "Consider using TLS/SSL for secure authentication.",
            file=sys.stderr
        )
    
    # Create email message
    msg, recipients = create_email_message(config)
    
    # Either write to file or send via SMTP
    if config.output_file:
        success = write_output_file(config, msg)
        return 0 if success else 1
    else:
        success = send_smtp(config, msg, recipients)
        
        if success and config.copy_email:
            save_imap_copy(config, msg)
        
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

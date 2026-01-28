# climb - Command Line Interface Mail Bot

A Python CLI utility for sending automated emails with full encryption support.

## Features

- SMTP email sending with TLS/SSL encryption
- Plain text and HTML email bodies
- Multiple recipients (To, CC, BCC)
- File attachments (single files or entire directories; directory attachments are non-recursive)
- IMAP support for saving sent mail copies
- Read receipt requests
- Options file support for batch/automated sending
- Password input via stdin or environment variable for security

## Requirements

- Python 3.x
- No external dependencies (uses standard library only)

## Installation

Simply download `climb.py` and make it executable:

```bash
chmod +x climb.py
```

## Usage

```bash
climb.py [options]
```

### Basic Example

```bash
climb.py -s smtp.example.com -u user@example.com -pw - \
    -t recipient@example.com -tt "Subject" -b "Message body"
```

### Options

| Option | Long Form | Description |
|--------|-----------|-------------|
| `-s` | `-server` | SMTP server to use |
| `-p` | `-port` | Server port (default: 587 for TLS, 25 for unencrypted) |
| `-tm` | `-timeout` | Network timeout in seconds (default: 60) |
| `-ss` | `-ssl` | Force SSL from beginning of connection |
| `-nc` | `-nocrypt` | Unencrypted connection (no SSL/TLS) |
| `-u` | `-user` | Username for login |
| `-pw` | `-password` | Password for login (use `-` for stdin or set `CLIMB_PASSWORD`) |
| `-f` | `-from` | Sender email (defaults to login username) |
| `-t` | `-to` | Recipients (comma-separated) |
| `-c` | `-cc` | CC recipients (comma-separated) |
| `-bc` | `-bcc` | BCC recipients (comma-separated) |
| `-tt` | `-title` | Mail subject |
| `-b` | `-body` | Plain text message body |
| `-bf` | `-bodyF` | File to read plain text body from |
| `-ht` | `-html` | HTML message body (requires a plain text body too) |
| `-hf` | `-htmlF` | File to read HTML body from (requires a plain text body too) |
| `-a` | `-attach` | Attachment file or directory (repeatable, directories are non-recursive) |
| `-ch` | `-charset` | Character set for text (default: UTF-8) |
| `-r` | `-receipt` | Request a read receipt |
| `-cp` | `-copy` | Save copy to IMAP folder (ignored if `-o` is set) |
| `-i` | `-imap` | IMAP server (only relevant with `-cp`; defaults to SMTP server) |
| `-o` | `-output` | Testing mode: build and validate the email normally, but write it to file instead of sending |
| `-v` | `-verbose` | Show status info while sending |
| `-of` | `-optionsF` | File to read options from (CLI options higher prio!) |
| `-h` | `-help` | Show help |

## Password Handling

For security, avoid passing passwords directly on the command line. Use one of these methods:

1. **stdin** (recommended):
   ```bash
   echo "mypassword" | climb.py -pw - ...
   ```

2. **Environment variable**:
   ```bash
   export CLIMB_PASSWORD="mypassword"
   climb.py ...
   ```

3. **Options file** (must be owner-readable only):
   ```bash
   chmod 600 options.txt
   climb.py -of options.txt
   ```

## Examples

### Send a simple email

```bash
climb.py -s smtp.gmail.com -p 587 -u sender@gmail.com -pw - \
    -t recipient@example.com \
    -tt "Hello" \
    -b "This is the message body."
```

### Send HTML email with attachment

```bash
climb.py -s smtp.example.com -u user@example.com -pw - \
    -t recipient@example.com \
    -tt "Report" \
    -b "Please see the attached report." \
    -ht "<html><body><h1>Report</h1><p>Please see the attached report.</p></body></html>" \
    -a report.pdf
```
Note: HTML-only emails are not supported; a plain-text body is always required for compatibility.

Note: Attaching a directory only includes the files in that directory (no nested subdirectories). For complex folder structures, zip them first.

### Send to multiple recipients with CC

```bash
climb.py -s smtp.example.com -u user@example.com -pw - \
    -t "alice@example.com, bob@example.com" \
    -c "manager@example.com" \
    -tt "Team Update" \
    -b "Here is the weekly update."
```

### Use options file for automated sending

Create `mail-options.txt`:
```
-s smtp.example.com
-u automation@example.com
-pw secretpassword
-f "Automated System <automation@example.com>"
```

Secure and use:
```bash
chmod 600 mail-options.txt
climb.py -of mail-options.txt -t admin@example.com -tt "Alert" -b "System alert message"
```

### Save email to file without sending (testing mode)

```bash
climb.py -s smtp.example.com -u user@example.com -pw dummy \
    -t recipient@example.com \
    -tt "Test" \
    -b "Test body" \
    -o email.eml
```

Note: `-o` still requires full credentials and performs normal validation so you can inspect the exact message that would be sent.

### Store copy in IMAP Sent folder

```bash
climb.py -s smtp.example.com -u user@example.com -pw - \
    -t recipient@example.com \
    -tt "Important" \
    -b "Message content" \
    -cp "Sent"
```

## Security Notes

- Options files must have restrictive permissions (no group/world access)
- Passwords passed via CLI will trigger a warning
- Use TLS/SSL encryption (default) unless connecting to a local relay
- BCC recipients are not written to email headers

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (missing arguments, connection failure, etc.) |

## License

Freeware - Created by Michael Boehm, Cephei AG

## Version

1.1

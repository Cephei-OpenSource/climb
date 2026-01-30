# climb Options File Guide

## Overview

Options files allow you to store commonly-used settings for climb, reducing command-line complexity and improving security by keeping passwords out of process lists.

## Security Requirements

**CRITICAL:** Options files containing passwords MUST have restricted permissions:

```bash
chmod 600 my-options.txt
```

climb will **refuse to run** if the options file is group or world-readable.

## File Format

- One option per line
- Comments start with #
- Options use same format as command line: `-option value`
- Quotes around values with spaces: `-title "My Subject"`
- Boolean options need no value: `-ssl`, `-verbose`

## Priority

Command-line options **override** options file settings. This allows:

```bash
# Use common settings but override recipient
climb -of common.txt -to different@example.com
```

## Best Practices

### 1. Store passwords securely

**Option A (Best):** Environment variable
```bash
# For current session
export CLIMB_PASSWORD="your_password"

# For persistent storage (system-wide)
# Add to /etc/environment:
CLIMB_PASSWORD="your_password"

# For systemd services
# Add to service file:
Environment="CLIMB_PASSWORD=your_password"

# Omit -password from options file
```

**Option B:** Options file with strict permissions
```bash
chmod 600 options.txt
# Include -password in options file
```

**Option C (Testing only):** Stdin
```bash
echo "password" | climb -of options.txt -pw -
```

### 2. Separate configs by purpose

- `climb-options-monitoring.txt` - For alerts
- `climb-options-reports.txt` - For scheduled reports
- `climb-options-notifications.txt` - For user notifications

### 3. Keep common settings in base config

```bash
# base-smtp.txt - Common server settings
-server smtp.example.com
-port 587
-timeout 30
-charset UTF-8
-user admin@example.com

# Then override for specific purposes
climb -of base-smtp.txt -to alerts@example.com -tt "Alert"
```

### 4. Testing configurations

**Test without sending (save to file):**
```bash
climb -of options.txt -output /tmp/test.eml -tt "Test" -b "Test body"
cat /tmp/test.eml  # Verify message is correct
```

**Test authentication and connection (discard output):**
```bash
# This validates SMTP credentials without sending actual mail
climb -of options.txt -output /dev/null -tt "Test" -b "Connection test"
# Exit code 0 = success, 1 = failure
```

**Test with verbose output:**
```bash
climb -of options.txt -v -output /tmp/test.eml -tt "Test" -b "Debug test"
# Shows detailed SMTP communication
```

### 5. Document your configurations

Add comments to options files explaining the purpose and any special settings.

## Common Patterns

### Pattern 1: Monitoring with Dynamic Content

```bash
# options-monitoring.txt contains static config
# Command line provides dynamic content
climb -of /etc/climb/monitoring.txt \
  -tt "$(hostname) - Service Down" \
  -b "Service $SERVICE stopped at $(date)" \
  -a /var/log/service.log
```

### Pattern 2: HTML Reports

```bash
# Generate HTML report
generate-report.sh > /tmp/report.html

# Send with options file
climb -of reports.txt \
  -tt "Weekly Report" \
  -b "Please see attached HTML report" \
  -hf /tmp/report.html \
  -a /tmp/data.csv
```

### Pattern 3: Multiple Attachments

```bash
# Attach entire directory of reports
climb -of options.txt \
  -tt "Batch Reports" \
  -b "All reports attached" \
  -a /tmp/reports/
```

### Pattern 4: Scheduled Reports via Cron

```bash
# Add to crontab: crontab -e
# Daily report at 8 AM
0 8 * * * export CLIMB_PASSWORD="secure_password"; /usr/local/bin/climb -of /etc/climb/daily-report.txt -tt "Daily Report $(date +\%Y-\%m-\%d)" -bf /tmp/daily.txt

# Weekly report every Monday at 9 AM
0 9 * * 1 export CLIMB_PASSWORD="secure_password"; /usr/local/bin/climb -of /etc/climb/weekly-report.txt -tt "Weekly Report" -bf /tmp/weekly.txt
```

### Pattern 5: Monitoring Script Integration

```bash
#!/bin/bash
# monitoring-script.sh

export CLIMB_PASSWORD="secure_password"
OPTIONS_FILE="/etc/climb/monitoring.txt"

# Check disk space
USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$USAGE" -gt 90 ]; then
    climb -of "$OPTIONS_FILE" \
        -tt "CRITICAL: Disk Space Alert on $(hostname)" \
        -b "Root filesystem usage: ${USAGE}%
        
Threshold: 90%
Current: ${USAGE}%
Server: $(hostname)
Time: $(date)

Please investigate immediately." \
        -a <(df -h) \
        -a /var/log/syslog
fi

# Check service status
if ! systemctl is-active --quiet apache2; then
    climb -of "$OPTIONS_FILE" \
        -tt "ALERT: Apache Service Down on $(hostname)" \
        -b "Apache2 service is not running.
        
Server: $(hostname)
Time: $(date)
Status: $(systemctl status apache2 | head -10)" \
        -a /var/log/apache2/error.log
fi
```

## Troubleshooting

### Error: "Options file must not be group/world-readable"

```bash
chmod 600 your-options.txt
ls -l your-options.txt  # Should show -rw-------
```

### Error: Options not being used

Check that options file path is correct and readable:
```bash
test -r your-options.txt && echo "OK" || echo "Not readable"
```

### Testing with verbose output

```bash
climb -of options.txt -v -tt "Test" -b "Test"
# Shows SMTP debug information
```

### Choosing the right SMTP port

Different mail providers use different ports and encryption methods:

**Port 587 (STARTTLS - Recommended):**
- Most common for modern SMTP
- Starts unencrypted, upgrades to TLS
- Use with default settings (no `-ssl` flag)

**Port 465 (SMTPS - SSL from start):**
- Encrypted from connection start
- Requires `-ssl` flag
- Used by some providers (e.g., older Gmail settings)

**Port 25 (Unencrypted - Not recommended):**
- Legacy port, no encryption
- Requires `-nocrypt` flag
- Only use on trusted internal networks

```bash
# Port 587 (most common)
climb -of options.txt -p 587 ...

# Port 465 (Gmail, some providers)
climb -of options.txt -p 465 -ssl ...

# Port 25 (internal/legacy only)
climb -of options.txt -p 25 -nocrypt ...
```

### Debugging connection issues

```bash
# Test SMTP connection manually
telnet smtp.example.com 587

# Test with verbose mode
climb -of options.txt -v -tt "Test" -b "Test" 2>&1 | tee debug.log

# Validate credentials without sending
climb -of options.txt -output /dev/null -tt "Auth Test" -b "Test"
echo $?  # 0 = success, 1 = failed
```

### Testing different timeout values

```bash
# Quick failure for monitoring
climb -of options.txt -tm 10 -tt "Test" -b "Test"

# Longer timeout for large attachments
climb -of options.txt -tm 120 -tt "Test" -b "Test" -a /large/file.zip
```

## Security Checklist

- [ ] Options file permissions: 600 (user-only read/write)
- [ ] Password stored in environment variable (preferred)
- [ ] OR password in options file with 600 permissions
- [ ] Options file not in web-accessible directory
- [ ] Options file not in version control (add to .gitignore)
- [ ] Regular password rotation policy
- [ ] Separate accounts for different purposes (monitoring, reports, etc.)
- [ ] SMTP account has strong password
- [ ] Consider using application-specific passwords
- [ ] Review sent mail archives periodically

## Systemd Service Example

For running climb as a systemd service (e.g., for periodic monitoring):

**Create `/etc/systemd/system/climb-monitoring.service`:**
```ini
[Unit]
Description=Server Monitoring Email Alert
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=monitoring
Group=monitoring
Environment="CLIMB_PASSWORD=your_secure_password"
ExecStart=/usr/local/bin/climb -of /etc/climb/monitoring.txt -tt "Monitoring Alert" -bf /tmp/monitoring-status.txt
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Create corresponding timer `/etc/systemd/system/climb-monitoring.timer`:**
```ini
[Unit]
Description=Run climb monitoring every hour
Requires=climb-monitoring.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

**Enable and start:**
```bash
systemctl daemon-reload
systemctl enable climb-monitoring.timer
systemctl start climb-monitoring.timer
systemctl status climb-monitoring.timer
```

## Examples Directory

This directory contains the following example files:

- **climb-options-example.txt** - Comprehensive template with all options documented
- **climb-options-monitoring.txt** - Minimal template optimized for server monitoring
- **climb-options-reports.txt** - Template for scheduled reports with attachments
- **README-options.md** - This guide

## Additional Resources

### Quick Reference

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| -server | -s | SMTP server | `-s smtp.gmail.com` |
| -port | -p | SMTP port | `-p 587` |
| -timeout | -tm | Network timeout (seconds) | `-tm 30` |
| -user | -u | Username | `-u admin@example.com` |
| -password | -pw | Password | `-pw secret` or `-pw -` |
| -from | -f | Sender email | `-f sender@example.com` |
| -to | -t | Recipients | `-t "user1@example.com, user2@example.com"` |
| -cc | -c | CC recipients | `-c manager@example.com` |
| -bcc | -bc | BCC recipients | `-bc archive@example.com` |

**Note:** Multiple recipients can be separated by commas (`,`) or semicolons (`;`)
| -title | -tt | Subject | `-tt "Alert Message"` |
| -body | -b | Message body | `-b "Alert text"` |
| -bodyF | -bf | Body from file | `-bf /path/to/body.txt` |
| -html | -ht | HTML body | `-ht "<html>...</html>"` |
| -htmlF | -hf | HTML from file | `-hf /path/to/body.html` |
| -attach | -a | Attachment | `-a /path/to/file.pdf` |
| -charset | -ch | Character set | `-ch UTF-8` |
| -receipt | -r | Request read receipt | `-r` |
| -copy | -cp | IMAP folder for copy | `-cp Sent` |
| -imap | -i | IMAP server | `-i imap.example.com` |
| -output | -o | Save to file | `-o /tmp/message.eml` |
| -verbose | -v | Debug output | `-v` |
| -optionsF | -of | Options file | `-of options.txt` |
| -ssl | -ss | Force SSL | `-ss` |
| -nocrypt | -nc | No encryption | `-nc` |

### Environment Variables

- **CLIMB_PASSWORD** - Set password via environment variable (recommended)

### Exit Codes

- **0** - Success
- **1** - Failure (any error)

Note: IMAP copy failures are non-fatal and will not cause exit code 1 if the email was sent successfully.

## Support

For issues, questions, or suggestions, please refer to the main climb documentation or contact your system administrator.

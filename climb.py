#!/usr/bin/python3
# -*- coding: utf-8 -*-
import smtplib, os, sys, shlex, mimetypes, time, imaplib
from email.mime.text import MIMEText
from email.header import Header
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from email.utils import format_datetime
from email.utils import make_msgid
import ssl as sslmod

defcharset = "UTF-8"; defport = "587"; defport_nc = "25"; deftimeout = "60" # defcharset was "ISO-8859-1"

password = ""; smtp_host = ""; mail_subject = ""; character_set = defcharset; sender_email = ""; login = "";
recipients_emails = ""; options_file = ""; verbose = False; cc_emails = ""; bcc_emails = "";
attachment_files = []; port = defport; html_body = ""; mail_body = ""; output_file = ""; ssl = False;
copy_email = ""; nocrypt = False; receipt = False; imap_host = ""; timeout = deftimeout;
body_file = ""; html_file = ""

def Usage():
    print("climb - Command Line Interface Mail Bot V1.0 by Michael Boehm, Cephei AG\n" \
        "Utility to send automated E-Mails with full encryption support - Freeware\n" \
        "Usage: climb [options]\n" + \
        "Case-insensitive options, and [arguments] that follow them:\n" + \
        "-s  or -server   : SMTP [Server] to use\n" + \
        "-p  or -port     : Server [Port] (Default " + defport + " for encrypted connections)\n" + \
        "-tm or -timeout  : Network timeout in seconds (Default " + deftimeout + ")\n" + \
        "-ss or -ssl      : Force SSL from beginning of connection (ignored if -nc)\n" + \
        "-nc or -nocrypt  : Unencrypted connection (don't use SSL; default port " + defport_nc + ")\n" + \
        "-u  or -user     : [Username] for login\n" + \
        "-pw or -password : [Password] for login (use '-' for stdin or set CLIMB_PASSWORD)\n" + \
        "-f  or -from     : Sender [E-Mail] (defaults to login username)\n" + \
        "-t  or -to       : Recipients [E-Mails], comma-separated\n" + \
        "-c  or -cc       : CC: Recipients [E-Mails], comma-separated\n" + \
        "-bc or -bcc      : BCC: Recipients [E-Mails], comma-separated\n" + \
        "-tt or -title    : Mail [Title] (Subject - use quotes for whitespace)\n" + \
        "-b  or -body     : Mail [Body] (Message Text - use quotes for whitespace)\n" + \
        "-bf or -bodyF    : [File] to read Mail Body from\n" + \
        "-ht or -html     : Mail [HTML] (Message HTML - use quotes for whitespace)\n" + \
        "-hf or -htmlF    : [File] to read Mail HTML Body from\n" + \
        "-a  or -attach   : Attachment [File or Dir] (Use repeatedly to add more)\n" + \
        "-ch or -charset  : Use this [Charset] for text, default \"" + defcharset + "\"\n" + \
        "-r  or -receipt  : Request a return receipt\n" + \
        "-cp or -copy     : Place a copy of Mail into [IMAP Folder] (ignored if -o)\n" + \
        "-i  or -imap     : IMAP4 [Server] to use (only relevant with -cp; default SMTP)\n" + \
        "-o  or -output   : Instead of sending mail, create [File] containing mail\n" + \
        "-v  or -verbose  : Give status info while sending\n" + \
        "-of or -optionsF : [File] to read options from (CLI opts higher prio!)\n" + \
        "-h  or -help     : Help (this usage)")
    sys.exit(1)
    
def ExitWithHelp():
    print("Use climb -h for help")
    sys.exit(1)
    
def CheckArg(argf, i):
    if i+1 < len(argf) and len(argf[i+1]) == 0:
        return "" #command line argument may void argument in options file
    elif i+1 >= len(argf) or argf[i+1][0] == "-":
        print("Argument missing for \"" + argf[i].lower() + "\"")
        ExitWithHelp()
    else:
        return argf[i+1]
    
def ParseArgs(argf, ignore_attachment, warn_on_cli_password):
    global password, smtp_host, mail_subject, mail_body, sender_email, login, port, recipients_emails, \
        options_file, verbose, cc_emails, bcc_emails, ssl, attachment_files, receipt, html_body, \
        output_file, character_set, copy_email, nocrypt, imap_host, timeout, body_file, html_file

    i = 0
    while True:
        i += 1
        if i >= len(argf):
            break

        opt = argf[i].lower()
        if (len(opt) > 4 and opt[0] == "-" and opt[1] == "-") or opt == "--to" or opt == "--cc":
            opt = opt[1:] #double hyphen equals single hyphen for long form of options
        if len(opt) <= 4 and opt[0] == "/" and opt[1] != "-":
            opt = "-" + opt[1:] #for short form of options '/' equals '-'
        
        if opt == "-user" or opt == "-u":
            login = CheckArg(argf, i)
            i += 1
        elif opt == "-password" or opt == "-pw":
            arg = CheckArg(argf, i)
            if arg == "-":
                password = sys.stdin.read().strip("\n")
            else:
                password = arg
                if warn_on_cli_password and arg != "":
                    print("Warning: passing passwords via CLI can expose secrets; prefer CLIMB_PASSWORD or stdin.", file=sys.stderr)
            i += 1
        elif opt == "-server" or opt == "-s":
            smtp_host = CheckArg(argf, i)
            i += 1
        elif opt == "-port" or opt == "-p":
            port = CheckArg(argf, i)
            i += 1
        elif opt == "-timeout" or opt == "-tm":
            timeout = CheckArg(argf, i)
            i += 1
        elif opt == "-title" or opt == "-tt":
            mail_subject = CheckArg(argf, i)
            i += 1
        elif opt == "-body" or opt == "-b":
            mail_body = CheckArg(argf, i)
            body_file = ""
            i += 1
        elif opt == "-bodyf" or opt == "-bf":
            arg = CheckArg(argf, i)
            if not os.path.isfile(arg):
                print("Text Body File \"" + arg + "\" does not exist.")
                sys.exit(1)
            body_file = arg
            mail_body = ""
            i += 1
        elif opt == "-html" or opt == "-ht":
            html_body = CheckArg(argf, i)
            html_file = ""
            i += 1
        elif opt == "-htmlf" or opt == "-hf":
            arg = CheckArg(argf, i)
            if not os.path.isfile(arg):
                print("HTML Body File \"" + arg + "\" does not exist.")
                sys.exit(1)
            html_file = arg
            html_body = ""
            i += 1
        elif opt == "-from" or opt == "-f":
            sender_email = CheckArg(argf, i)
            i += 1
        elif opt == "-to" or opt == "-t":
            recipients_emails = CheckArg(argf, i)
            i += 1
        elif opt == "-cc" or opt == "-c":
            cc_emails = CheckArg(argf, i)
            i += 1
        elif opt == "-bcc" or opt == "-bc":
            bcc_emails = CheckArg(argf, i)
            i += 1
        elif opt == "-charset" or opt == "-ch":
            character_set = CheckArg(argf, i)
            i += 1
        elif opt == "-attach" or opt == "-a":
            arg = CheckArg(argf, i)
            if os.path.isdir(arg):
                if not ignore_attachment:
                    for fn in os.listdir(arg):
                        attachment_files.append(os.path.join(arg, fn))
            else:
                if not os.path.isfile(arg):
                    print("Attachment File \"" + arg + "\" does not exist.")
                    sys.exit(1)
                if not ignore_attachment:
                    attachment_files.append(arg)
            i += 1
        elif opt == "-optionsf" or opt == "-of":
            arg = CheckArg(argf, i)
            if not os.path.isfile(arg):
                print("Options File \"" + arg + "\" does not exist.")
                sys.exit(1)
            options_file = arg
            i += 1
        elif opt == "-output" or opt == "-o":
            output_file = CheckArg(argf, i)
            i += 1
        elif opt == "-copy" or opt == "-cp":
            copy_email = CheckArg(argf, i)
            i += 1
        elif opt == "-ssl" or opt == "-ss":
            ssl = True
        elif opt == "-receipt" or opt == "-r":
            receipt = True
        elif opt == "-nocrypt" or opt == "-nc":
            nocrypt = True
            if port == defport:
                port = defport_nc
        elif opt == "-imap" or opt == "-i":
            imap_host = CheckArg(argf, i)
            i += 1
        elif opt == "-verbose" or opt == "-v":
            verbose = True
        elif opt == "-help" or opt == "-h" or opt == "-?":
            Usage()
        else:
            print("Unknown option \"" + opt + "\"")
            ExitWithHelp()

def split_addrs(s):
    return [x.strip() for x in s.replace(";", ",").split(",") if x.strip()]

#--------------------
#------ main() ------
#--------------------
if len(sys.argv) == 1:
    Usage()

ParseArgs(sys.argv, False, True)
if options_file != "":
    try:
        st = os.stat(options_file)
    except OSError as exc:
        print(f"Failed to stat options file '{options_file}': {exc}", file=sys.stderr)
        sys.exit(1)
    if st.st_mode & 0o077:
        print(f"Options file '{options_file}' must not be group/world-readable.", file=sys.stderr)
        sys.exit(1)
    try:
        with open(options_file, "r") as f:
            opt = f.read()
    except OSError as exc:
        print(f"Failed to read options file '{options_file}': {exc}", file=sys.stderr)
        sys.exit(1)
    optv = shlex.split(opt)
    optv.insert(0, options_file)
    ParseArgs(optv, False, False)
    ParseArgs(sys.argv, True, True) #command-line args have higher priority

if password == "":
    env_password = os.getenv("CLIMB_PASSWORD")
    if env_password is not None:
        password = env_password

try:
    port_num = int(port)
    if not (1 <= port_num <= 65535):
        raise ValueError(f"must be between 1 and 65535, got {port_num}")
except ValueError as exc:
    print(f"Invalid port '{port}': {exc}", file=sys.stderr)
    sys.exit(1)

try:
    timeout_secs = int(timeout)
    if timeout_secs <= 0:
        raise ValueError(f"must be a positive integer in seconds, got {timeout_secs}")
except ValueError as exc:
    print(f"Invalid timeout '{timeout}': {exc}", file=sys.stderr)
    sys.exit(1)

if body_file != "":
    try:
        with open(body_file, "r", encoding=character_set, errors="replace") as f:
            mail_body = f.read()
    except OSError as exc:
        print(f"Failed to read body file '{body_file}': {exc}", file=sys.stderr)
        sys.exit(1)

if html_file != "":
    try:
        with open(html_file, "r", encoding=character_set, errors="replace") as f:
            html_body = f.read()
    except OSError as exc:
        print(f"Failed to read HTML file '{html_file}': {exc}", file=sys.stderr)
        sys.exit(1)

if sender_email == "":
    sender_email = login
if nocrypt and ssl:
    ssl = False
if copy_email and imap_host == "":
    imap_host = smtp_host

if smtp_host == "" or login == "" or password == "" or mail_subject == "" or \
    mail_body == "" or sender_email == "" or recipients_emails == "":
    if smtp_host == "":
        print("SMTP-Server not set")
    if login == "":
        print("Login username not set")
    if password == "":
        print("Password not set")
    if recipients_emails == "":
        print("No mail-recipients given")
    if mail_subject == "":
        print("Mail subject missing")
    if mail_body == "":
        print("Text mail body missing")
    if sender_email == "":
        print("From: E-Mail not set")
    ExitWithHelp() #these arguments are minimally required

if len(attachment_files) == 0:
    if html_body == "":
        msg = MIMEText(mail_body, "plain", character_set)
    else:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(mail_body, "plain", character_set))
        msg.attach(MIMEText(html_body, "html", character_set))
else:
    msg = MIMEMultipart()

    if html_body == "":
        msg.attach(MIMEText(mail_body, "plain", character_set))
    else:
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(mail_body, "plain", character_set))
        alt.attach(MIMEText(html_body, "html", character_set))
        msg.attach(alt)

msg["Date"] = format_datetime(datetime.now().astimezone())
msg["Message-ID"] = make_msgid()
msg["Subject"] = Header(mail_subject, character_set)
msg["From"] = sender_email
if receipt:
    msg["Disposition-Notification-To"] = sender_email #alternative "Return-Receipt-To" is non-standard

recipients_list = split_addrs(recipients_emails)
msg["To"] = ", ".join(recipients_list)
email_list = list(recipients_list)

if cc_emails != "":
    cc_list = split_addrs(cc_emails)
    if cc_list:
        msg["CC"] = ", ".join(cc_list)
        email_list += cc_list
            
if bcc_emails != "":
    bcc_list = split_addrs(bcc_emails)
    if bcc_list:
        # Do not write BCC into the header
        email_list += bcc_list

for i in range(0, len(attachment_files)):
    path = attachment_files[i]
    try:
        basename = os.path.basename(path)
        ext = os.path.splitext(basename)[1].lower()

        if ext == ".pdf":
            with open(path, "rb") as f:
                att = MIMEBase("application", "pdf")
                att.set_payload(f.read())
            encoders.encode_base64(att)
            # RFC-2231: UTF-8-safe filename
            att.add_header("Content-Disposition", "attachment", filename=("utf-8", "", basename))
            msg.attach(att)
            continue

        ctype, encoding = mimetypes.guess_type(path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        if maintype == "text":
            with open(path, "r", encoding=character_set, errors="replace") as f:
                att = MIMEText(f.read(), subtype, character_set)
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

        # For non-PDFs: set filename robustly
        att.add_header("Content-Disposition", "attachment", filename=("utf-8", "", basename))
        msg.attach(att)
    except OSError as exc:
        print(f"Failed to read attachment '{path}': {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Failed to process attachment '{path}': {exc}", file=sys.stderr)
        sys.exit(1)
    
exitlevel = 0
    
if output_file != "":
    try:
        with open(output_file, "wb") as f:
            f.write(msg.as_bytes())
    except OSError as exc:
        print(f"Failed to write output file '{output_file}': {exc}", file=sys.stderr)
        exitlevel = 1
else:
    try:
        tls_ctx = sslmod.create_default_context()
        if ssl:
            s = smtplib.SMTP_SSL(smtp_host, port_num, timeout=timeout_secs, context=tls_ctx)
            s.sock.settimeout(timeout_secs)
        else:
            s = smtplib.SMTP(smtp_host, port_num, timeout=timeout_secs)
    except (smtplib.SMTPException, OSError, ValueError) as exc:
        print(f"Failed to connect to SMTP server '{smtp_host}:{port_num}': {exc}", file=sys.stderr)
        sys.exit(1)

    if verbose:
        s.set_debuglevel(1)

    try:
        if not ssl and not nocrypt:
            s.starttls(context=tls_ctx)
            s.sock.settimeout(timeout_secs)
        s.login(login, password)
        s.sendmail(msg["From"], email_list, msg.as_string())
    except (smtplib.SMTPException, OSError, ValueError) as exc:
        print(f"Failed to send mail: {exc}", file=sys.stderr)
        exitlevel = 1
    finally:
        s.quit()
        
    if copy_email != "":
        if verbose:
            imaplib.Debug = 4

        try:
            if nocrypt:
                i = imaplib.IMAP4(imap_host)
            else:
                i = imaplib.IMAP4_SSL(imap_host)
            if i.sock is not None:
                i.sock.settimeout(timeout_secs)
        except (imaplib.IMAP4.error, OSError, ValueError) as exc:
            print(f"Warning: failed to connect to IMAP server '{imap_host}': {exc}", file=sys.stderr)
            i = None

        if i is not None:
            try:
                i.login(login, password)
                i.append(copy_email, "\\Seen", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
            except (imaplib.IMAP4.error, OSError, ValueError) as exc:
                print(f"Warning: failed to store copy in IMAP folder '{copy_email}': {exc}", file=sys.stderr)
            finally:
                try:
                    i.logout()
                except (imaplib.IMAP4.error, OSError, ValueError):
                    pass

sys.exit(exitlevel)

"""
Smart Library v2 — notification.py
Email (Gmail SMTP) + Telegram (100% FREE, UNLIMITED, NEVER restricted/banned)

WHY TELEGRAM:
- CallMeBot got rate-limited/banned (common issue with shared free service)
- Fast2SMS needs payment (DLT regulation in India)
- Telegram Bot API is run by Telegram itself — completely free forever,
  no message limits, no bans, no payment, used by millions of apps.

Function names/signatures kept IDENTICAL (send_sms, is_sms_configured,
test_sms) so library_manager.py, deadline_checker.py, gui.py are
UNCHANGED — nothing else in the project needs to be touched.

IMPORTANT: The "phone" parameter is now used to hold the student's
Telegram Chat ID (a number like 123456789) instead of a real phone
number — see setup instructions below.
"""

import smtplib
import threading
import json
import os
import urllib.request
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


class EmailNotifier:
    def __init__(self, sender_email='', sender_password='',
                 smtp_server='smtp.gmail.com', smtp_port=587,
                 sms_api_key=''):
        self.sender_email    = sender_email
        self.sender_password = sender_password
        self.smtp_server     = smtp_server
        self.smtp_port       = smtp_port
        # sms_api_key now stores the Telegram BOT TOKEN
        # (same setting field/name reused — keeps other files unchanged)
        self.sms_api_key     = sms_api_key

    def is_configured(self):
        return bool(self.sender_email and self.sender_password)

    def is_sms_configured(self):
        return bool(self.sms_api_key)

    # ── EMAIL ────────────────────────────────────────────────────────────────

    def _send_email(self, to_email, subject, html_body, attachment_path=None):
        if not self.is_configured():
            return False, "Email not configured. Go to Settings."
        try:
            msg = MIMEMultipart('mixed')
            msg['Subject'] = subject
            msg['From']    = f"Smart Library <{self.sender_email}>"
            msg['To']      = to_email

            body_part = MIMEMultipart('alternative')
            body_part.attach(MIMEText(html_body, 'html'))
            msg.attach(body_part)

            # ── Optional PDF attachment (public domain / free books only) ────
            if attachment_path and os.path.isfile(attachment_path):
                try:
                    with open(attachment_path, 'rb') as f:
                        part = MIMEBase('application', 'pdf')
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(attachment_path)
                    part.add_header(
                        'Content-Disposition', f'attachment; filename="{filename}"'
                    )
                    msg.attach(part)
                except Exception as e:
                    print(f"[EMAIL] Attachment error (sending without it): {e}")

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20) as s:
                s.starttls()
                s.login(self.sender_email, self.sender_password)
                s.sendmail(self.sender_email, to_email, msg.as_string())
            print(f"[EMAIL] Sent to {to_email}: {subject}")
            return True, f"Email sent to {to_email}"
        except smtplib.SMTPAuthenticationError:
            return False, "Wrong Gmail ID or App Password."
        except Exception as e:
            return False, str(e)

    def _send_async(self, to_email, subject, html_body, callback=None, attachment_path=None):
        def _worker():
            ok, msg = self._send_email(to_email, subject, html_body, attachment_path)
            if callback:
                callback(ok, msg)
        threading.Thread(target=_worker, daemon=True).start()

    # ── TELEGRAM — 100% FREE FOREVER, NEVER BANNED ───────────────────────────
    #
    # ONE-TIME SETUP (5 minutes, completely free, no card needed):
    #
    #  STEP 1 — Create your bot:
    #    1. Open Telegram app, search for:  @BotFather
    #    2. Send message:  /newbot
    #    3. Give it any name, e.g.  "Smart Library Bot"
    #    4. Give it a username ending in 'bot', e.g.  "mylibrary_xyz_bot"
    #    5. BotFather replies with a TOKEN like:
    #         123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
    #    6. Copy that token → paste in Settings → "SMS API Key" field
    #
    #  STEP 2 — Get YOUR Chat ID (to receive test messages):
    #    1. In Telegram, search for your new bot by its username
    #    2. Open chat with it, send:  /start
    #    3. Now open this URL in your browser (replace TOKEN):
    #         https://api.telegram.org/bot<TOKEN>/getUpdates
    #    4. Look for "chat":{"id": 123456789  ← that number is your Chat ID
    #    5. Use that number in the "Test Phone Number" field
    #
    #  FOR EACH STUDENT (one-time per student):
    #    Student opens your bot, sends /start once → you note their
    #    Chat ID → enter it in the "Phone" field when issuing their book.

    def send_sms(self, phone, message, callback=None):
        """
        Sends a message via Telegram Bot API.
        Kept the name 'send_sms' and signature identical so no other
        file in the project needs to change.
        'phone' here is actually the Telegram numeric Chat ID.
        """
        def _worker():
            if not self.is_sms_configured():
                if callback:
                    callback(False, "Telegram Bot Token not set. Go to Settings.")
                return

            chat_id = str(phone).strip()
            if not chat_id:
                if callback:
                    callback(False, "No Telegram Chat ID provided.")
                return

            try:
                bot_token = self.sms_api_key.strip()
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

                payload = json.dumps({
                    "chat_id": chat_id,
                    "text"   : message[:4000],   # Telegram allows long messages
                }).encode('utf-8')

                req = urllib.request.Request(
                    url, data=payload,
                    headers={"Content-Type": "application/json"},
                    method='POST'
                )

                with urllib.request.urlopen(req, timeout=15) as resp:
                    body   = resp.read().decode('utf-8')
                    result = json.loads(body)

                print(f"[TELEGRAM] Response: {result}")

                if result.get('ok') is True:
                    if callback:
                        callback(True, f"Telegram message sent!")
                else:
                    err = result.get('description', 'Unknown error')
                    if callback:
                        callback(False, f"Telegram: {err}")

            except urllib.error.HTTPError as e:
                err_body = ''
                try:
                    err_body = e.read().decode(errors='ignore')
                    err_json = json.loads(err_body)
                    err_body = err_json.get('description', err_body)
                except Exception:
                    pass
                print(f"[TELEGRAM] HTTP {e.code}: {err_body}")
                if callback:
                    callback(False, f"{err_body[:100]}")
            except Exception as e:
                print(f"[TELEGRAM] Error: {e}")
                if callback:
                    callback(False, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def test_sms(self, phone, callback=None):
        msg = "📚 Smart Library Test: Telegram notifications are working!"
        self.send_sms(phone, msg, callback)

    # ── NOTIFICATION TEMPLATES — Email + Telegram ────────────────────────────

    def send_issue_confirmation(self, to_email, phone, student_name,
                                 book_title, issue_date_str, due_date_str,
                                 callback=None, pdf_path=None):
        if to_email and self.is_configured():
            subject = f"Book Issued: {book_title}"
            pdf_note = (
                "<p style=\"background:#e3f2fd;padding:10px 14px;border-radius:6px;"
                "color:#0d47a1\">📎 The book PDF is attached to this email "
                "(public domain / free resource).</p>"
            ) if (pdf_path and os.path.isfile(pdf_path)) else ""
            html = f"""
            <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;
                        border:1px solid #e0e0e0;border-radius:10px;overflow:hidden">
              <div style="background:#1b5e20;padding:20px;text-align:center">
                <h2 style="color:white;margin:0">Smart Library</h2>
                <p style="color:#a5d6a7;margin:5px 0">Book Issued Successfully</p>
              </div>
              <div style="padding:24px">
                <p>Hello <b>{student_name}</b>,</p>
                <p>Your book has been issued:</p>
                <div style="background:#f5f5f5;border-left:4px solid #1b5e20;padding:14px;margin:16px 0">
                  <b>{book_title}</b><br>
                  Issued: {issue_date_str}<br>
                  <b style="color:#1b5e20">Return By: {due_date_str}</b>
                </div>
                {pdf_note}
                <p>Late fine: Rs 5 per day after due date.</p>
              </div>
            </div>"""
            self._send_async(to_email, subject, html, callback, attachment_path=pdf_path)

        if phone and self.is_sms_configured():
            msg = (f"📚 Smart Library\n\n"
                   f"Book Issued: {book_title}\n"
                   f"Issued to: {student_name}\n"
                   f"Return by: {due_date_str}\n\n"
                   f"⚠️ Fine: Rs 5/day if late.")
            self.send_sms(phone, msg, callback)

    def send_due_reminder(self, to_email, phone, student_name,
                           book_title, due_date_str, callback=None):
        if to_email and self.is_configured():
            subject = f"Reminder: Return '{book_title}' TOMORROW"
            html = f"""
            <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;
                        border:1px solid #e0e0e0;border-radius:10px;overflow:hidden">
              <div style="background:#1a237e;padding:20px;text-align:center">
                <h2 style="color:white;margin:0">Smart Library</h2>
                <p style="color:#90caf9;margin:5px 0">Return Reminder</p>
              </div>
              <div style="padding:24px">
                <p>Hello <b>{student_name}</b>,</p>
                <p><b style="color:#e53935">'{book_title}'</b> is due TOMORROW ({due_date_str}).</p>
                <p>Please return to avoid Rs 5/day fine.</p>
              </div>
            </div>"""
            self._send_async(to_email, subject, html, callback)

        if phone and self.is_sms_configured():
            msg = (f"📚 Smart Library — REMINDER\n\n"
                   f"'{book_title}' is due TOMORROW ({due_date_str}).\n\n"
                   f"⚠️ Return to avoid Rs 5/day fine!")
            self.send_sms(phone, msg, callback)

    def send_overdue_notice(self, to_email, phone, student_name,
                             book_title, due_date_str, days_overdue,
                             fine_amount, callback=None):
        if to_email and self.is_configured():
            subject = f"OVERDUE: '{book_title}' — Fine Rs {fine_amount:.0f}"
            html = f"""
            <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;
                        border:1px solid #e0e0e0;border-radius:10px;overflow:hidden">
              <div style="background:#b71c1c;padding:20px;text-align:center">
                <h2 style="color:white;margin:0">Smart Library</h2>
                <p style="color:#ffcdd2;margin:5px 0">Overdue Notice</p>
              </div>
              <div style="padding:24px">
                <p>Hello <b>{student_name}</b>,</p>
                <p><b>'{book_title}'</b> is overdue by <b>{days_overdue} days</b>.</p>
                <div style="background:#ffebee;padding:14px;text-align:center;border-radius:6px">
                  <b style="font-size:24px;color:#b71c1c">Fine: Rs {fine_amount:.0f}</b><br>
                  <small>Rs 5 x {days_overdue} days</small>
                </div>
                <p style="margin-top:12px">Please return immediately.</p>
              </div>
            </div>"""
            self._send_async(to_email, subject, html, callback)

        if phone and self.is_sms_configured():
            msg = (f"📚 Smart Library — OVERDUE ⚠️\n\n"
                   f"'{book_title}' overdue by {days_overdue} days.\n"
                   f"Fine: Rs {fine_amount:.0f}\n\n"
                   f"Please return immediately!")
            self.send_sms(phone, msg, callback)

    # ── TEST CONNECTION ───────────────────────────────────────────────────────

    def test_connection(self):
        if not self.is_configured():
            return False, "Email not configured."
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=8) as s:
                s.starttls()
                s.login(self.sender_email, self.sender_password)
            return True, "Gmail connected! Emails will work."
        except smtplib.SMTPAuthenticationError:
            return False, "Wrong Gmail ID or App Password."
        except Exception as e:
            return False, str(e)

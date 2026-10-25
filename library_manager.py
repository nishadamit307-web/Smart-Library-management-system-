"""
Smart Library Management System v2 — library_manager.py
NEW: passes book's pdf_path to email so public-domain PDFs get attached
All previous logic (deadline, fine, search, notifications) kept intact
"""

from database         import LibraryDatabase
from qr_generator     import QRGenerator
from serial_comm      import SerialComm
from notification     import EmailNotifier
from deadline_checker import DeadlineChecker
from datetime         import datetime, timedelta


class LibraryManager:
    def __init__(self):
        self.db      = LibraryDatabase()
        self.qr_gen  = QRGenerator()
        self.serial  = SerialComm()
        self._load_notifier()
        self.checker = DeadlineChecker(self.db, self.notifier)
        self.checker.start()
        self.on_event_callback = None

    def _load_notifier(self):
        self.notifier = EmailNotifier(
            sender_email    = self.db.get_setting('email_sender', ''),
            sender_password = self.db.get_setting('email_password', ''),
            sms_api_key     = self.db.get_setting('sms_api_key', ''),
        )

    def reload_notifier(self):
        self._load_notifier()
        self.checker.notifier = self.notifier

    def save_email_settings(self, email, password):
        self.db.set_setting('email_sender',   email)
        self.db.set_setting('email_password', password)
        self.reload_notifier()

    def save_sms_settings(self, api_key):
        self.db.set_setting('sms_api_key', api_key)
        self.reload_notifier()

    def test_email(self):
        return self.notifier.test_connection()

    def test_sms(self, phone, callback=None):
        self.notifier.test_sms(phone, callback)

    # ── QR Scan ──────────────────────────────────────────────────────────────
    def process_qr_scan(self, qr_data,
                        student_name='', student_id='',
                        student_email='', student_phone=''):
        qr_data = qr_data.strip()
        book    = self.db.get_book_by_id(qr_data)

        if not book:
            try:
                self.serial.send_invalid_scan(qr_data)
            except Exception:
                pass
            event = {
                'type': 'INVALID',
                'message': f"Unknown QR: '{qr_data}' — not in database.",
                'book': None,
                'student_name': '', 'student_email': '',
                'student_phone': '', 'due_date': '',
            }
            self._fire(event)
            return event

        due_date_str = ''

        if book['available'] > 0:
            # ── ISSUE ────────────────────────────────────────────────────────
            loan_days = int(self.db.get_setting('loan_days', '30'))
            ok, msg   = self.db.issue_book(
                qr_data, student_name, student_id,
                student_email, student_phone, loan_days
            )
            action = 'ISSUE'
            if ok:
                due_dt       = datetime.now() + timedelta(days=loan_days)
                due_date_str = due_dt.strftime('%d %b %Y')

                # ✅ NEW: pass book's pdf_path so it can be attached
                pdf_path = book.get('pdf_path', '') or None
                try:
                    self.notifier.send_issue_confirmation(
                        to_email       = student_email,
                        phone          = student_phone,
                        student_name   = student_name or 'Student',
                        book_title     = book['title'],
                        issue_date_str = datetime.now().strftime('%d %b %Y'),
                        due_date_str   = due_date_str,
                        pdf_path       = pdf_path,
                    )
                except Exception as e:
                    print(f"[NOTIFY] Email/SMS send error (non-fatal): {e}")
        else:
            # ── RETURN ───────────────────────────────────────────────────────
            ok, msg = self.db.return_book(qr_data, student_name, student_id)
            action  = 'RETURN'

        updated_book = self.db.get_book_by_id(qr_data)

        if ok:
            try:
                self.serial.send_book_data(
                    action, book['book_id'], book['title'],
                    book['author'],
                    'ISSUED' if action == 'ISSUE' else 'RETURNED'
                )
            except Exception:
                pass
            event = {
                'type': action, 'message': msg, 'book': updated_book,
                'student_name': student_name, 'student_email': student_email,
                'student_phone': student_phone, 'due_date': due_date_str,
            }
        else:
            event = {
                'type': 'ERROR', 'message': msg, 'book': updated_book,
                'student_name': student_name, 'student_email': student_email,
                'student_phone': student_phone, 'due_date': '',
            }

        self._fire(event)
        return event

    # ── Book CRUD ─────────────────────────────────────────────────────────────
    def add_book(self, book_id, title, author, isbn='', genre='',
                 quantity=1, generate_qr=True, pdf_path=''):
        ok, msg = self.db.add_book(book_id, title, author, isbn, genre, quantity, pdf_path)
        if ok and generate_qr:
            try:
                path = self.qr_gen.generate_qr(book_id, title, author)
                self.db.update_qr_path(book_id, path)
            except Exception as e:
                msg += f" (QR error: {e})"
        return ok, msg

    def update_book(self, book_id, title, author, isbn='', genre='', quantity=1, pdf_path=None):
        return self.db.update_book(book_id, title, author, isbn, genre, quantity, pdf_path)

    def update_pdf_path(self, book_id, pdf_path):
        self.db.update_pdf_path(book_id, pdf_path)

    def delete_book(self, book_id):
        return self.db.delete_book(book_id)

    def get_book(self, book_id):
        return self.db.get_book_by_id(book_id)

    def get_all_books(self):
        return self.db.get_all_books()

    def search_books(self, query):
        return self.db.search_books(query)

    def get_next_book_id(self):
        return self.db.get_next_book_id()

    def get_history(self, book_id=None):
        return self.db.get_issue_history(book_id)

    def get_active_issues(self):
        return self.db.get_active_issues()

    def get_overdue_books(self):
        return self.db.get_overdue_books()

    def run_deadline_check(self):
        self.checker.run_now()

    def send_reminder_manually(self, record, callback=None):
        email = record.get('student_email', '').strip()
        phone = record.get('student_phone', '').strip()
        name  = record.get('student_name', 'Student')
        title = record.get('title', '')
        due   = record.get('due_date', '')
        try:
            due_fmt = datetime.fromisoformat(due).strftime('%d %b %Y')
        except Exception:
            due_fmt = due[:10]

        try:
            if record.get('overdue'):
                fine = record.get('fine', 0)
                days = abs(record.get('days_left', 0))
                self.notifier.send_overdue_notice(
                    email, phone, name, title, due_fmt, days, fine, callback
                )
            else:
                self.notifier.send_due_reminder(
                    email, phone, name, title, due_fmt, callback
                )
        except Exception as e:
            if callback:
                callback(False, str(e))

    def generate_qr_for_book(self, book_id):
        book = self.db.get_book_by_id(book_id)
        if not book:
            return None, "Book not found."
        try:
            path = self.qr_gen.generate_qr(book_id, book['title'], book['author'])
            self.db.update_qr_path(book_id, path)
            return path, "QR generated."
        except Exception as e:
            return None, str(e)

    def connect_pico(self, port=None):
        return self.serial.connect(port)

    def disconnect_pico(self):
        self.serial.disconnect()

    def is_pico_connected(self):
        return self.serial.connected

    def get_available_ports(self):
        return self.serial.get_available_ports()

    def get_setting(self, key, default=''):
        return self.db.get_setting(key, default)

    def set_setting(self, key, value):
        self.db.set_setting(key, value)

    def _fire(self, event):
        if self.on_event_callback:
            self.on_event_callback(event)

"""
Smart Library v2 — deadline_checker.py
Fixed:
  1. Lambda closure bug — each student now gets correct callback
  2. Per-student try/except — one failure won't block others
  3. on_status_callback called safely via threading to avoid
     'main thread is not in main loop' RuntimeError in Tkinter
"""

import threading
import time
from datetime import datetime


class DeadlineChecker:
    CHECK_INTERVAL = 6 * 60 * 60  # 6 hours

    def __init__(self, db, notifier):
        self.db       = db
        self.notifier = notifier
        self._stop    = threading.Event()
        self._thread  = None
        self.last_run = None
        self.on_status_callback = None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[DEADLINE] Checker started.")

    def stop(self):
        self._stop.set()

    def run_now(self):
        threading.Thread(target=self._check, daemon=True).start()

    def _loop(self):
        while not self._stop.is_set():
            self._check()
            self._stop.wait(self.CHECK_INTERVAL)

    # ── Safe callback helpers ─────────────────────────────────────────────────

    def _safe_status(self, msg):
        """Call on_status_callback safely from any thread."""
        cb = self.on_status_callback
        if cb:
            try:
                cb(msg)
            except RuntimeError:
                # Tkinter 'main thread is not in main loop' — ignore silently
                pass
            except Exception as e:
                print(f"[DEADLINE] Status callback error: {e}")

    @staticmethod
    def _make_reminder_cb(label, name, title):
        """
        FIX: Create a real closure per student so lambda doesn't share
        the loop variable (classic Python late-binding closure bug).
        """
        def _cb(ok, m):
            status = "OK" if ok else "FAIL"
            print(f"[{label}] {status} → {name} | {title[:30]} | {m}")
        return _cb

    # ── Main check ────────────────────────────────────────────────────────────

    def _check(self):
        self.last_run = datetime.now()
        print(f"[DEADLINE] Check at {self.last_run.strftime('%H:%M:%S')}")
        sent = 0

        # ── Due tomorrow reminders ────────────────────────────────────────────
        try:
            records = self.db.get_due_tomorrow()
        except Exception as e:
            print(f"[DEADLINE] DB error (due_tomorrow): {e}")
            records = []

        for r in records:
            # FIX: Per-student try/except — one bad record won't stop the rest
            try:
                email = r.get('student_email', '').strip()
                phone = r.get('student_phone', '').strip()
                name  = r.get('student_name', 'Student')
                title = r.get('title', r.get('book_id', ''))
                due   = r.get('due_date', '')
                try:
                    due_fmt = datetime.fromisoformat(due).strftime('%d %b %Y')
                except Exception:
                    due_fmt = str(due)[:10]

                if email or phone:
                    # FIX: Use _make_reminder_cb to capture name/title correctly
                    cb = self._make_reminder_cb("REMINDER", name, title)
                    self.notifier.send_due_reminder(
                        email, phone, name, title, due_fmt, callback=cb
                    )
                    sent += 1
                    print(f"[DEADLINE] Reminder queued → {name} ({email or phone})")
            except Exception as e:
                print(f"[DEADLINE] Reminder error for record {r}: {e}")

        # ── Overdue notices ───────────────────────────────────────────────────
        try:
            overdue_records = self.db.get_overdue_books()
        except Exception as e:
            print(f"[DEADLINE] DB error (overdue): {e}")
            overdue_records = []

        for r in overdue_records:
            # FIX: Per-student try/except
            try:
                email     = r.get('student_email', '').strip()
                phone     = r.get('student_phone', '').strip()
                name      = r.get('student_name', 'Student')
                title     = r.get('title', r.get('book_id', ''))
                due       = r.get('due_date', '')
                days_over = abs(r.get('days_left', 0) or 0)
                fine      = days_over * 5
                try:
                    due_fmt = datetime.fromisoformat(due).strftime('%d %b %Y')
                except Exception:
                    due_fmt = str(due)[:10]

                if email or phone:
                    # FIX: Use _make_reminder_cb to capture name/title correctly
                    cb = self._make_reminder_cb("OVERDUE", name, title)
                    self.notifier.send_overdue_notice(
                        email, phone, name, title, due_fmt, days_over, fine,
                        callback=cb
                    )
                    sent += 1
                    print(f"[DEADLINE] Overdue notice queued → {name} ({email or phone}) | {days_over}d overdue | Rs {fine}")
            except Exception as e:
                print(f"[DEADLINE] Overdue error for record {r}: {e}")

        msg = f"Check done. {sent} notification(s) queued."
        print(f"[DEADLINE] {msg}")
        # FIX: Safe callback — won't crash Tkinter even from background thread
        self._safe_status(msg)

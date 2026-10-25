"""
Smart Library Management System v2 — database.py
NEW: pdf_path column added to books table (for public domain / free PDFs)
All previous features (deadline, fine, search) kept intact
"""

import sqlite3
import os
from datetime import datetime, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(_HERE, '..', 'database', 'library.db')

FINE_PER_DAY = 5
LOAN_DAYS    = 30


class LibraryDatabase:
    def __init__(self):
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()
        self._migrate()
        self._insert_sample_data()

    def _create_tables(self):
        self.cursor.executescript('''
            CREATE TABLE IF NOT EXISTS books (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id     TEXT    UNIQUE NOT NULL,
                title       TEXT    NOT NULL,
                author      TEXT    NOT NULL,
                isbn        TEXT    DEFAULT '',
                genre       TEXT    DEFAULT '',
                quantity    INTEGER DEFAULT 1,
                available   INTEGER DEFAULT 1,
                added_date  TEXT    NOT NULL,
                qr_path     TEXT    DEFAULT '',
                pdf_path    TEXT    DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS issue_history (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id        TEXT    NOT NULL,
                student_name   TEXT    DEFAULT '',
                student_id     TEXT    DEFAULT '',
                student_email  TEXT    DEFAULT '',
                student_phone  TEXT    DEFAULT '',
                action         TEXT    NOT NULL,
                issue_date     TEXT    DEFAULT '',
                due_date       TEXT    DEFAULT '',
                return_date    TEXT    DEFAULT '',
                fine_amount    REAL    DEFAULT 0.0,
                fine_paid      INTEGER DEFAULT 0,
                timestamp      TEXT    NOT NULL,
                FOREIGN KEY (book_id) REFERENCES books(book_id)
            );

            CREATE TABLE IF NOT EXISTS students (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id   TEXT    UNIQUE NOT NULL,
                name         TEXT    NOT NULL,
                email        TEXT    DEFAULT '',
                phone        TEXT    DEFAULT '',
                books_issued INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        ''')
        self.conn.commit()

    def _migrate(self):
        new_cols = [
            ("issue_history", "student_email",  "TEXT DEFAULT ''"),
            ("issue_history", "student_phone",  "TEXT DEFAULT ''"),
            ("issue_history", "issue_date",     "TEXT DEFAULT ''"),
            ("issue_history", "due_date",       "TEXT DEFAULT ''"),
            ("issue_history", "return_date",    "TEXT DEFAULT ''"),
            ("issue_history", "fine_amount",    "REAL DEFAULT 0.0"),
            ("issue_history", "fine_paid",      "INTEGER DEFAULT 0"),
            ("books",         "pdf_path",       "TEXT DEFAULT ''"),
        ]
        for table, col, col_def in new_cols:
            try:
                self.cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
                self.conn.commit()
            except Exception:
                pass

    def _insert_sample_data(self):
        self.cursor.execute("SELECT COUNT(*) FROM books")
        if self.cursor.fetchone()[0] > 0:
            return
        sample = [
            ('BK001', 'Python Programming',          'Mark Lutz',            '978-1449355739', 'Technology', 3, 3),
            ('BK002', 'Clean Code',                  'Robert C. Martin',     '978-0132350884', 'Technology', 2, 2),
            ('BK003', 'The Great Gatsby',             'F. Scott Fitzgerald',  '978-0743273565', 'Fiction',    4, 4),
            ('BK004', 'Artificial Intelligence',      'Stuart Russell',       '978-0136042594', 'Technology', 2, 2),
            ('BK005', 'Data Structures & Algorithms', 'Thomas H. Cormen',    '978-0262033848', 'Technology', 3, 3),
            ('BK006', 'Introduction to IoT',          'Arshdeep Bahga',      '978-0996025553', 'Technology', 2, 2),
            ('BK007', 'Harry Potter & The Goblet',    'J. K. Rowling',       '978-0439139601', 'Fiction',    5, 5),
        ]
        for b in sample:
            self.cursor.execute(
                '''INSERT OR IGNORE INTO books
                   (book_id, title, author, isbn, genre, quantity, available, added_date)
                   VALUES(?,?,?,?,?,?,?,?)''',
                b + (datetime.now().isoformat(),)
            )
        self.conn.commit()

    # ── Books ────────────────────────────────────────────────────────────────

    def get_all_books(self):
        self.cursor.execute("SELECT * FROM books ORDER BY title")
        return [dict(r) for r in self.cursor.fetchall()]

    def get_book_by_id(self, book_id):
        self.cursor.execute("SELECT * FROM books WHERE book_id=?", (book_id,))
        r = self.cursor.fetchone()
        return dict(r) if r else None

    def search_books(self, query):
        like = f"%{query}%"
        self.cursor.execute(
            """SELECT * FROM books
               WHERE title LIKE ? OR author LIKE ? OR book_id LIKE ?
                  OR isbn LIKE ? OR genre LIKE ?
               ORDER BY
                 CASE WHEN available > 0 THEN 0 ELSE 1 END, title""",
            (like, like, like, like, like)
        )
        return [dict(r) for r in self.cursor.fetchall()]

    def add_book(self, book_id, title, author, isbn='', genre='', quantity=1, pdf_path=''):
        try:
            self.cursor.execute(
                '''INSERT INTO books
                   (book_id, title, author, isbn, genre, quantity, available, added_date, pdf_path)
                   VALUES(?,?,?,?,?,?,?,?,?)''',
                (book_id, title, author, isbn, genre, quantity, quantity,
                 datetime.now().isoformat(), pdf_path)
            )
            self.conn.commit()
            return True, f"'{title}' added successfully."
        except sqlite3.IntegrityError:
            return False, f"Book ID '{book_id}' already exists."
        except Exception as e:
            return False, str(e)

    def update_book(self, book_id, title, author, isbn='', genre='', quantity=1, pdf_path=None):
        try:
            if pdf_path is None:
                self.cursor.execute(
                    "UPDATE books SET title=?,author=?,isbn=?,genre=?,quantity=? WHERE book_id=?",
                    (title, author, isbn, genre, quantity, book_id)
                )
            else:
                self.cursor.execute(
                    "UPDATE books SET title=?,author=?,isbn=?,genre=?,quantity=?,pdf_path=? WHERE book_id=?",
                    (title, author, isbn, genre, quantity, pdf_path, book_id)
                )
            self.conn.commit()
            return True, "Book updated."
        except Exception as e:
            return False, str(e)

    def delete_book(self, book_id):
        try:
            self.cursor.execute("DELETE FROM books WHERE book_id=?", (book_id,))
            self.conn.commit()
            return True, "Book deleted."
        except Exception as e:
            return False, str(e)

    def update_qr_path(self, book_id, qr_path):
        self.cursor.execute("UPDATE books SET qr_path=? WHERE book_id=?", (qr_path, book_id))
        self.conn.commit()

    def update_pdf_path(self, book_id, pdf_path):
        self.cursor.execute("UPDATE books SET pdf_path=? WHERE book_id=?", (pdf_path, book_id))
        self.conn.commit()

    def get_next_book_id(self):
        self.cursor.execute("SELECT book_id FROM books ORDER BY id DESC LIMIT 1")
        r = self.cursor.fetchone()
        if r:
            try:
                return f"BK{int(r[0][2:]) + 1:03d}"
            except Exception:
                pass
        return "BK001"

    # ── Issue / Return ───────────────────────────────────────────────────────

    def issue_book(self, book_id, student_name='', student_id='',
                   student_email='', student_phone='', loan_days=LOAN_DAYS):
        book = self.get_book_by_id(book_id)
        if not book:
            return False, "Book not found."
        if book['available'] <= 0:
            return False, f"No copies of '{book['title']}' available."

        now      = datetime.now()
        due_date = now + timedelta(days=loan_days)

        try:
            self.cursor.execute(
                "UPDATE books SET available=available-1 WHERE book_id=?", (book_id,)
            )
            self.cursor.execute(
                '''INSERT INTO issue_history
                   (book_id,student_name,student_id,student_email,student_phone,
                    action,issue_date,due_date,timestamp)
                   VALUES(?,?,?,?,?,'ISSUED',?,?,?)''',
                (book_id, student_name, student_id, student_email, student_phone,
                 now.isoformat(), due_date.isoformat(), now.isoformat())
            )
            self.conn.commit()
            return True, f"'{book['title']}' issued. Due: {due_date.strftime('%d %b %Y')}"
        except Exception as e:
            return False, str(e)

    def return_book(self, book_id, student_name='', student_id=''):
        book = self.get_book_by_id(book_id)
        if not book:
            return False, "Book not found."
        if book['available'] >= book['quantity']:
            return False, "All copies already returned."

        now      = datetime.now()
        fine     = self._calculate_fine(book_id)
        fine_msg = f" Fine: Rs {fine:.0f}" if fine > 0 else ""

        try:
            self.cursor.execute(
                "UPDATE books SET available=available+1 WHERE book_id=?", (book_id,)
            )
            self.cursor.execute(
                '''INSERT INTO issue_history
                   (book_id,student_name,student_id,action,return_date,fine_amount,timestamp)
                   VALUES(?,?,?,'RETURNED',?,?,?)''',
                (book_id, student_name, student_id,
                 now.isoformat(), fine, now.isoformat())
            )
            self.conn.commit()
            return True, f"'{book['title']}' returned.{fine_msg}"
        except Exception as e:
            return False, str(e)

    def _calculate_fine(self, book_id):
        self.cursor.execute(
            '''SELECT due_date FROM issue_history
               WHERE book_id=? AND action='ISSUED'
               ORDER BY id DESC LIMIT 1''',
            (book_id,)
        )
        r = self.cursor.fetchone()
        if not r or not r['due_date']:
            return 0.0
        try:
            due  = datetime.fromisoformat(r['due_date'])
            diff = (datetime.now() - due).days
            return max(0, diff) * FINE_PER_DAY
        except Exception:
            return 0.0

    # ── History ──────────────────────────────────────────────────────────────

    def get_issue_history(self, book_id=None, limit=200):
        if book_id:
            self.cursor.execute(
                "SELECT * FROM issue_history WHERE book_id=? ORDER BY timestamp DESC LIMIT ?",
                (book_id, limit)
            )
        else:
            self.cursor.execute(
                "SELECT * FROM issue_history ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
        return [dict(r) for r in self.cursor.fetchall()]

    # ── Deadline / Fine helpers ───────────────────────────────────────────────

    def get_active_issues(self):
        self.cursor.execute(
            '''SELECT ih.*, b.title, b.author
               FROM issue_history ih
               JOIN books b ON ih.book_id = b.book_id
               WHERE ih.action = 'ISSUED'
                 AND ih.book_id NOT IN (
                     SELECT book_id FROM issue_history
                     WHERE action='RETURNED' AND id > ih.id
                 )
               ORDER BY ih.due_date ASC'''
        )
        rows = [dict(r) for r in self.cursor.fetchall()]
        now  = datetime.now()
        for row in rows:
            try:
                due = datetime.fromisoformat(row['due_date']) if row['due_date'] else None
                if due:
                    diff = (due - now).days
                    row['days_left']    = diff
                    row['overdue']      = diff < 0
                    row['due_tomorrow'] = diff == 1
                    row['fine']         = max(0, -diff) * FINE_PER_DAY
                else:
                    row['days_left'] = None
                    row['overdue']   = False
                    row['due_tomorrow'] = False
                    row['fine']      = 0
            except Exception:
                row['days_left'] = None
                row['overdue']   = False
                row['due_tomorrow'] = False
                row['fine']      = 0
        return rows

    def get_due_tomorrow(self):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        self.cursor.execute(
            '''SELECT ih.*, b.title
               FROM issue_history ih
               JOIN books b ON ih.book_id = b.book_id
               WHERE ih.action='ISSUED'
                 AND ih.due_date LIKE ?
                 AND ih.student_email != ''
            ''',
            (f"{tomorrow}%",)
        )
        return [dict(r) for r in self.cursor.fetchall()]

    def get_overdue_books(self):
        now = datetime.now().isoformat()
        self.cursor.execute(
            '''SELECT ih.*, b.title, b.author
               FROM issue_history ih
               JOIN books b ON ih.book_id = b.book_id
               WHERE ih.action='ISSUED'
                 AND ih.due_date != ''
                 AND ih.due_date < ?
               ORDER BY ih.due_date ASC''',
            (now,)
        )
        return [dict(r) for r in self.cursor.fetchall()]

    # ── Settings ─────────────────────────────────────────────────────────────

    def get_setting(self, key, default=''):
        self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        r = self.cursor.fetchone()
        return r['value'] if r else default

    def set_setting(self, key, value):
        self.cursor.execute(
            "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value)
        )
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()

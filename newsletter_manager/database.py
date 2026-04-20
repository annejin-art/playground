import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_email    TEXT    UNIQUE NOT NULL,
                    sender_name     TEXT,
                    list_id         TEXT,
                    unsubscribe_link TEXT,
                    gmail_label_id  TEXT,
                    active          INTEGER DEFAULT 1,
                    first_seen      TEXT,
                    last_received   TEXT,
                    email_count     INTEGER DEFAULT 0,
                    created_at      TEXT    DEFAULT CURRENT_TIMESTAMP,
                    updated_at      TEXT    DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS newsletter_items (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id  INTEGER REFERENCES subscriptions(id),
                    gmail_message_id TEXT    UNIQUE NOT NULL,
                    subject          TEXT,
                    received_at      TEXT,
                    snippet          TEXT,
                    content          TEXT,
                    summary          TEXT,
                    headlines        TEXT,
                    digest_included  INTEGER DEFAULT 0,
                    created_at       TEXT    DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS digest_runs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date    TEXT NOT NULL,
                    items_count INTEGER DEFAULT 0,
                    recipient   TEXT,
                    status      TEXT,
                    error       TEXT,
                    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_items_received
                    ON newsletter_items(received_at);
                CREATE INDEX IF NOT EXISTS idx_items_digest
                    ON newsletter_items(digest_included, received_at);
                CREATE INDEX IF NOT EXISTS idx_subs_email
                    ON subscriptions(sender_email);
                CREATE INDEX IF NOT EXISTS idx_subs_active
                    ON subscriptions(active);
            """)

    # ── Subscriptions ─────────────────────────────────────────────────────────

    def upsert_subscription(
        self,
        sender_email: str,
        sender_name: Optional[str] = None,
        list_id: Optional[str] = None,
        unsubscribe_link: Optional[str] = None,
    ) -> int:
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM subscriptions WHERE sender_email = ?", (sender_email,)
            ).fetchone()
            if row:
                conn.execute(
                    """UPDATE subscriptions
                       SET sender_name      = COALESCE(?, sender_name),
                           list_id          = COALESCE(?, list_id),
                           unsubscribe_link = COALESCE(?, unsubscribe_link),
                           last_received    = ?,
                           email_count      = email_count + 1,
                           updated_at       = ?
                       WHERE sender_email = ?""",
                    (sender_name, list_id, unsubscribe_link, now, now, sender_email),
                )
                return row["id"]
            else:
                cur = conn.execute(
                    """INSERT INTO subscriptions
                       (sender_email, sender_name, list_id, unsubscribe_link,
                        first_seen, last_received)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (sender_email, sender_name, list_id, unsubscribe_link, now, now),
                )
                return cur.lastrowid

    def list_subscriptions(self, active_only: bool = True) -> List[sqlite3.Row]:
        with self._conn() as conn:
            q = "SELECT * FROM subscriptions"
            if active_only:
                q += " WHERE active = 1"
            return conn.execute(q + " ORDER BY email_count DESC").fetchall()

    def deactivate_subscription(self, sender_email: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE subscriptions SET active = 0, updated_at = ? WHERE sender_email = ?",
                (datetime.utcnow().isoformat(), sender_email),
            )

    def set_label(self, sender_email: str, label_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE subscriptions SET gmail_label_id = ? WHERE sender_email = ?",
                (label_id, sender_email),
            )

    # ── Newsletter items ──────────────────────────────────────────────────────

    def add_newsletter_item(
        self,
        subscription_id: int,
        gmail_message_id: str,
        subject: str,
        received_at: str,
        snippet: Optional[str] = None,
        content: Optional[str] = None,
    ) -> Optional[int]:
        """Insert item; returns new row id, or None if already stored."""
        with self._conn() as conn:
            if conn.execute(
                "SELECT id FROM newsletter_items WHERE gmail_message_id = ?",
                (gmail_message_id,),
            ).fetchone():
                return None
            cur = conn.execute(
                """INSERT INTO newsletter_items
                   (subscription_id, gmail_message_id, subject, received_at,
                    snippet, content)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (subscription_id, gmail_message_id, subject, received_at, snippet, content),
            )
            return cur.lastrowid

    def update_item_summary(
        self, item_id: int, summary: str, headlines_json: str
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE newsletter_items SET summary = ?, headlines = ? WHERE id = ?",
                (summary, headlines_json, item_id),
            )

    def get_unsummarized_items(self, limit: int = 50) -> List[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                """SELECT ni.*, s.sender_name, s.sender_email
                   FROM newsletter_items ni
                   JOIN subscriptions s ON s.id = ni.subscription_id
                   WHERE ni.summary IS NULL AND ni.content IS NOT NULL
                   ORDER BY ni.received_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()

    def get_todays_items(self, date_str: str) -> List[sqlite3.Row]:
        """Items whose received_at date (UTC) matches date_str (YYYY-MM-DD)."""
        with self._conn() as conn:
            return conn.execute(
                """SELECT ni.*, s.sender_name, s.sender_email
                   FROM newsletter_items ni
                   JOIN subscriptions s ON s.id = ni.subscription_id
                   WHERE date(ni.received_at) = ? AND s.active = 1
                   ORDER BY ni.received_at DESC""",
                (date_str,),
            ).fetchall()

    def mark_items_in_digest(self, item_ids: List[int]) -> None:
        with self._conn() as conn:
            conn.executemany(
                "UPDATE newsletter_items SET digest_included = 1 WHERE id = ?",
                [(i,) for i in item_ids],
            )

    # ── Search ────────────────────────────────────────────────────────────────

    def search_items(self, query: str, limit: int = 20) -> List[sqlite3.Row]:
        pattern = f"%{query}%"
        with self._conn() as conn:
            return conn.execute(
                """SELECT ni.*, s.sender_name, s.sender_email
                   FROM newsletter_items ni
                   JOIN subscriptions s ON s.id = ni.subscription_id
                   WHERE (ni.subject  LIKE ?
                       OR ni.content  LIKE ?
                       OR ni.summary  LIKE ?)
                     AND s.active = 1
                   ORDER BY ni.received_at DESC
                   LIMIT ?""",
                (pattern, pattern, pattern, limit),
            ).fetchall()

    # ── Digest runs ───────────────────────────────────────────────────────────

    def log_digest_run(
        self,
        run_date: str,
        items_count: int,
        recipient: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO digest_runs
                   (run_date, items_count, recipient, status, error)
                   VALUES (?, ?, ?, ?, ?)""",
                (run_date, items_count, recipient, status, error),
            )

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        with self._conn() as conn:
            subs = conn.execute(
                """SELECT COUNT(*) total,
                          SUM(active) active,
                          SUM(1 - active) inactive
                   FROM subscriptions"""
            ).fetchone()
            items = conn.execute(
                """SELECT COUNT(*) total_items,
                          COUNT(DISTINCT date(received_at)) days_with_items
                   FROM newsletter_items"""
            ).fetchone()
            recent = conn.execute(
                """SELECT COUNT(*) cnt
                   FROM newsletter_items
                   WHERE date(received_at) = date('now')"""
            ).fetchone()
            return {
                "subscriptions": dict(subs),
                "items": dict(items),
                "today": recent["cnt"],
            }

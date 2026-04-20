import os
import base64
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import timezone
from typing import Dict, List, Optional, Tuple

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify",
]


def _parse_sender(from_header: str) -> Tuple[str, str]:
    match = re.match(r"^(.*?)\s*<(.+?)>\s*$", from_header)
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip().lower()
        return name, email
    return "", from_header.strip().lower()


def _decode_base64(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    except Exception:
        return ""


def _html_to_text(html: str) -> str:
    try:
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        return h.handle(html)
    except ImportError:
        try:
            from bs4 import BeautifulSoup
            return BeautifulSoup(html, "html.parser").get_text(separator="\n")
        except ImportError:
            return re.sub(r"<[^>]+>", " ", html)


def _extract_text_from_payload(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return _decode_base64(data) if data else ""

    if mime_type == "text/html":
        data = payload.get("body", {}).get("data", "")
        return _html_to_text(_decode_base64(data)) if data else ""

    parts = payload.get("parts", [])
    plain, html_text = "", ""
    for part in parts:
        part_mime = part.get("mimeType", "")
        if part_mime == "text/plain":
            plain += _extract_text_from_payload(part)
        elif part_mime == "text/html":
            html_text += _extract_text_from_payload(part)
        elif part_mime.startswith("multipart/"):
            result = _extract_text_from_payload(part)
            if result:
                plain += result

    return plain or html_text


def _parse_gmail_date(date_str: str) -> str:
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        from datetime import datetime
        return datetime.utcnow().isoformat()


class GmailClient:
    def __init__(self, credentials_file: str, token_file: str):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None

    def authenticate(self) -> None:
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {self.credentials_file}\n"
                        "Download OAuth2 credentials from Google Cloud Console > "
                        "APIs & Services > Credentials (OAuth 2.0 Client ID, Desktop app)."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_file, "w") as f:
                f.write(creds.to_json())

        self.service = build("gmail", "v1", credentials=creds)

    def _ensure_auth(self):
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

    # ── Search & fetch ────────────────────────────────────────────────────────

    def search_messages(self, query: str, max_results: int = 500) -> List[Dict]:
        self._ensure_auth()
        results, page_token = [], None
        while len(results) < max_results:
            batch = min(500, max_results - len(results))
            kwargs: Dict = {"userId": "me", "q": query, "maxResults": batch}
            if page_token:
                kwargs["pageToken"] = page_token
            resp = self.service.users().messages().list(**kwargs).execute()
            results.extend(resp.get("messages", []))
            page_token = resp.get("nextPageToken")
            if not page_token or not resp.get("messages"):
                break
        return results

    def get_message(self, message_id: str, format: str = "full") -> Dict:
        self._ensure_auth()
        return (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format=format)
            .execute()
        )

    def parse_message(self, message: Dict) -> Dict:
        payload = message.get("payload", {})
        headers = {
            h["name"].lower(): h["value"] for h in payload.get("headers", [])
        }
        sender_name, sender_email = _parse_sender(headers.get("from", ""))
        content = _extract_text_from_payload(payload)

        return {
            "id": message["id"],
            "thread_id": message.get("threadId", ""),
            "sender_email": sender_email,
            "sender_name": sender_name,
            "subject": headers.get("subject", "(no subject)"),
            "date": headers.get("date", ""),
            "received_at": _parse_gmail_date(headers.get("date", "")),
            "snippet": message.get("snippet", ""),
            # Cap stored content; enough for summarization
            "content": content[:8000],
            "unsubscribe": headers.get("list-unsubscribe", ""),
            "list_id": headers.get("list-id", ""),
        }

    # ── Newsletter discovery ──────────────────────────────────────────────────

    def get_recent_newsletters(
        self, subscription_email: str, after_date: Optional[str] = None
    ) -> List[Dict]:
        """Return deduplicated recent newsletter messages using both detection methods."""
        date_filter = f" after:{after_date}" if after_date else ""
        msgs1 = self.search_messages(f"has:unsubscribe{date_filter}", max_results=300)
        msgs2 = self.search_messages(
            f"to:{subscription_email}{date_filter}", max_results=300
        )
        seen: set = set()
        combined: List[Dict] = []
        for msg in msgs1 + msgs2:
            if msg["id"] not in seen:
                seen.add(msg["id"])
                combined.append(msg)
        return combined

    # ── Sending ───────────────────────────────────────────────────────────────

    def send_email(
        self, to: str, subject: str, html_body: str, text_body: Optional[str] = None
    ) -> Dict:
        self._ensure_auth()
        message = MIMEMultipart("alternative")
        message["to"] = to
        message["subject"] = subject
        if text_body:
            message.attach(MIMEText(text_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return (
            self.service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )

    # ── Labels ────────────────────────────────────────────────────────────────

    def list_labels(self) -> List[Dict]:
        self._ensure_auth()
        return (
            self.service.users().labels().list(userId="me").execute().get("labels", [])
        )

    def get_or_create_label(self, name: str) -> str:
        """Return the label ID, creating the label if it doesn't exist."""
        for label in self.list_labels():
            if label["name"] == name:
                return label["id"]
        result = (
            self.service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )
        return result["id"]

    def apply_labels(self, message_id: str, label_ids: List[str]) -> None:
        self._ensure_auth()
        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": label_ids},
        ).execute()

    def get_messages_with_label(self, label_id: str) -> List[Dict]:
        return self.search_messages(f"label:{label_id}", max_results=200)

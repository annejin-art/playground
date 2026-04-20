import json
import logging
from datetime import datetime, date
from html import escape
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
        max-width:680px;margin:0 auto;padding:24px;color:#1f2937;background:#f9fafb}}
  .hdr{{background:linear-gradient(135deg,#1e1b4b,#312e81);color:#fff;
        padding:32px;border-radius:12px;margin-bottom:28px}}
  .hdr h1{{margin:0 0 6px;font-size:22px;font-weight:700}}
  .hdr p{{margin:0;opacity:.8;font-size:13px}}
  .count{{font-weight:700;color:#a5b4fc}}
  .card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;
         padding:20px 24px;margin-bottom:16px}}
  .sender{{font-size:11px;font-weight:700;letter-spacing:.08em;
           text-transform:uppercase;color:#6366f1}}
  .subj{{font-size:17px;font-weight:600;color:#111827;margin:6px 0 4px}}
  .ts{{font-size:12px;color:#9ca3af;margin-bottom:10px}}
  .summary{{font-size:14px;line-height:1.65;color:#374151}}
  .hl-title{{font-size:11px;font-weight:700;letter-spacing:.06em;
             text-transform:uppercase;color:#9ca3af;margin:12px 0 4px}}
  .hl-list{{margin:0;padding-left:18px}}
  .hl-list li{{font-size:13px;color:#374151;margin:3px 0}}
  .footer{{text-align:center;font-size:11px;color:#9ca3af;
           margin-top:36px;padding-top:16px;border-top:1px solid #e5e7eb}}
</style>
</head>
<body>
<div class="hdr">
  <h1>Your Daily Newsletter Digest</h1>
  <p>{date_label} &bull; <span class="count">{count} newsletter{plural}</span></p>
</div>
{cards}
<div class="footer">
  Generated {timestamp} UTC &bull; Newsletter Manager
</div>
</body>
</html>"""

_CARD = """\
<div class="card">
  <div class="sender">{sender}</div>
  <div class="subj">{subject}</div>
  <div class="ts">{time_label}</div>
  {summary_block}
  {headlines_block}
</div>"""


def _fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%-I:%M %p UTC")
    except Exception:
        return ""


def _headlines_html(raw: Optional[str]) -> str:
    if not raw:
        return ""
    try:
        items = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(items, list) or not items:
        return ""
    lis = "".join(f"<li>{escape(str(h))}</li>" for h in items[:5])
    return f'<div class="hl-title">Key headlines</div><ul class="hl-list">{lis}</ul>'


def _card_html(item: dict) -> str:
    sender = escape(item.get("sender_name") or item.get("sender_email") or "Unknown")
    subject = escape(item.get("subject") or "(no subject)")
    time_label = _fmt_time(item.get("received_at") or "")
    summary_block = (
        f'<div class="summary">{escape(item["summary"])}</div>'
        if item.get("summary")
        else ""
    )
    return _CARD.format(
        sender=sender,
        subject=subject,
        time_label=time_label,
        summary_block=summary_block,
        headlines_block=_headlines_html(item.get("headlines")),
    )


def _render_text(items: List[dict], run_date: str) -> str:
    d = datetime.strptime(run_date, "%Y-%m-%d")
    lines = [
        f"Daily Newsletter Digest — {d.strftime('%A, %B %d, %Y')}",
        f"{len(items)} newsletter(s)",
        "=" * 60,
        "",
    ]
    for item in items:
        lines += [
            f"FROM:    {item.get('sender_name') or item.get('sender_email', '?')}",
            f"SUBJECT: {item.get('subject', '(no subject)')}",
        ]
        if item.get("summary"):
            lines += ["", item["summary"]]
        if item.get("headlines"):
            try:
                hl = json.loads(item["headlines"])
                if hl:
                    lines += ["", "Key headlines:"] + [f"  • {h}" for h in hl[:5]]
            except (json.JSONDecodeError, TypeError):
                pass
        lines += ["-" * 40, ""]
    return "\n".join(lines)


class DigestGenerator:
    def __init__(self, gmail_client, database, summarizer):
        self.gmail = gmail_client
        self.db = database
        self.summarizer = summarizer

    def run_digest(
        self, recipient: str, run_date: Optional[str] = None
    ) -> Dict:
        """Summarize today's newsletters and email the digest. Returns status dict."""
        if run_date is None:
            run_date = date.today().isoformat()

        items = [dict(r) for r in self.db.get_todays_items(run_date)]
        if not items:
            self.db.log_digest_run(run_date, 0, recipient, "skipped")
            return {"status": "skipped", "count": 0}

        # Summarize anything not yet summarized
        for item in items:
            if not item.get("summary") and item.get("content"):
                try:
                    summary, headlines = self.summarizer.summarize(
                        item.get("sender_name") or item.get("sender_email", ""),
                        item.get("subject", ""),
                        item["content"],
                    )
                    self.db.update_item_summary(item["id"], summary, json.dumps(headlines))
                    item["summary"] = summary
                    item["headlines"] = json.dumps(headlines)
                except Exception as exc:
                    logger.warning("Summarization failed for item %s: %s", item["id"], exc)

        # Re-fetch so summaries are fresh
        items = [dict(r) for r in self.db.get_todays_items(run_date)]

        d = datetime.strptime(run_date, "%Y-%m-%d")
        date_label = d.strftime("%A, %B %d, %Y")
        count = len(items)
        subject_line = (
            f"Newsletter Digest — {date_label} ({count} newsletter{'s' if count != 1 else ''})"
        )

        html_body = _HTML.format(
            date_label=date_label,
            count=count,
            plural="s" if count != 1 else "",
            cards="\n".join(_card_html(i) for i in items),
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        )
        text_body = _render_text(items, run_date)

        try:
            self.gmail.send_email(recipient, subject_line, html_body, text_body)
            self.db.mark_items_in_digest([i["id"] for i in items])
            self.db.log_digest_run(run_date, count, recipient, "sent")
            return {"status": "sent", "count": count}
        except Exception as exc:
            self.db.log_digest_run(run_date, count, recipient, "error", str(exc))
            raise

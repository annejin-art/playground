#!/usr/bin/env python3
"""Newsletter Subscription Manager — CLI entry point."""

import json
import logging
import sys
from datetime import date

import click

from newsletter_manager.config import config
from newsletter_manager.database import Database
from newsletter_manager.digest import DigestGenerator
from newsletter_manager.gmail import GmailClient
from newsletter_manager.scheduler import NewsletterScheduler
from newsletter_manager.summarizer import NewsletterSummarizer

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


# ── Client helpers ────────────────────────────────────────────────────────────


def _db() -> Database:
    return Database(config.DATABASE_PATH)


def _gmail() -> GmailClient:
    client = GmailClient(config.GMAIL_CREDENTIALS_FILE, config.GMAIL_TOKEN_FILE)
    client.authenticate()
    return client


def _all_clients():
    gmail = _gmail()
    db = _db()
    summarizer = NewsletterSummarizer(config.ANTHROPIC_API_KEY)
    digest = DigestGenerator(gmail, db, summarizer)
    return gmail, db, summarizer, digest


# ── CLI ───────────────────────────────────────────────────────────────────────


@click.group()
def cli():
    """Manage and read your newsletter subscriptions from the command line."""


# ── sync ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--days", default=7, show_default=True, help="Days to look back in Gmail.")
@click.option("--label/--no-label", default=True, show_default=True, help="Apply Gmail labels.")
def sync(days: int, label: bool) -> None:
    """Pull newsletters from Gmail into the local database."""
    gmail, db, summarizer, digest = _all_clients()
    scheduler = NewsletterScheduler(config, gmail, db, summarizer, digest)

    click.echo(f"Syncing newsletters from the last {days} day(s)…")
    new_items = scheduler.sync(lookback_days=days)
    stats = db.get_stats()
    click.echo(
        f"Done — {new_items} new item(s). "
        f"Total: {stats['subscriptions']['active']} active subscriptions, "
        f"{stats['items']['total_items']} stored newsletters."
    )


# ── list ──────────────────────────────────────────────────────────────────────


@cli.command("list")
@click.option("--all", "show_all", is_flag=True, help="Include inactive subscriptions.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def list_subscriptions(show_all: bool, as_json: bool) -> None:
    """List all newsletter subscriptions."""
    db = _db()
    subs = db.list_subscriptions(active_only=not show_all)

    if as_json:
        click.echo(json.dumps([dict(s) for s in subs], indent=2, default=str))
        return

    if not subs:
        click.echo("No subscriptions found. Run `sync` to import from Gmail.")
        return

    col = "{:<40} {:<32} {:>7}  {:<12}  {}"
    click.echo(col.format("SENDER EMAIL", "NAME", "EMAILS", "LAST SEEN", "STATUS"))
    click.echo("─" * 100)
    for s in subs:
        status = (
            click.style("active", fg="green")
            if s["active"]
            else click.style("paused", fg="yellow")
        )
        last = (s["last_received"] or "")[:10] or "—"
        click.echo(
            col.format(
                s["sender_email"][:39],
                (s["sender_name"] or "")[:31],
                s["email_count"] or 0,
                last,
                status,
            )
        )
    click.echo(f"\n{len(subs)} subscription(s)")


# ── search ────────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("query")
@click.option("--limit", default=20, show_default=True, help="Maximum results to show.")
@click.option(
    "--gmail",
    "use_gmail",
    is_flag=True,
    help="Search Gmail directly instead of local DB (slower).",
)
def search(query: str, limit: int, use_gmail: bool) -> None:
    """Search newsletter content.

    By default searches the local database. Use --gmail to query Gmail directly.
    """
    if use_gmail:
        gmail = _gmail()
        q = (
            f"({query}) "
            f"(has:unsubscribe OR to:{config.SUBSCRIPTION_EMAIL})"
        )
        click.echo(f"Searching Gmail: {q}\n")
        messages = gmail.search_messages(q, max_results=limit)
        if not messages:
            click.echo("No results.")
            return
        for ref in messages:
            msg = gmail.get_message(ref["id"], format="metadata")
            headers = {
                h["name"].lower(): h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            click.echo(
                f"  {click.style(headers.get('subject', '(no subject)'), bold=True)}\n"
                f"  {headers.get('from', '')}  {headers.get('date', '')}\n"
            )
        return

    db = _db()
    results = db.search_items(query, limit=limit)
    if not results:
        click.echo(
            "No local results. Run `sync` first, or try `search --gmail` to query Gmail directly."
        )
        return

    click.echo(f"{len(results)} result(s) for "{query}":\n")
    for item in results:
        click.echo(click.style(item["subject"] or "(no subject)", bold=True))
        click.echo(
            f"  From: {item['sender_name'] or item['sender_email']}  "
            f"| {(item['received_at'] or '')[:10]}"
        )
        if item["summary"]:
            click.echo(f"  {item['summary'][:200]}")
        click.echo()


# ── digest ────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--date", "run_date", default=None, metavar="YYYY-MM-DD", help="Date to digest.")
@click.option("--to", "recipient", default=None, help="Recipient email (overrides .env).")
@click.option("--dry-run", is_flag=True, help="Preview without sending.")
def digest(run_date: str, recipient: str, dry_run: bool) -> None:
    """Generate and send the daily newsletter digest email."""
    gmail, db, summarizer, digest_gen = _all_clients()
    target = run_date or date.today().isoformat()
    to = recipient or config.DIGEST_RECIPIENT

    if not to:
        click.echo(
            "Error: no recipient. Set DIGEST_RECIPIENT in .env or pass --to.", err=True
        )
        sys.exit(1)

    items = list(db.get_todays_items(target))
    if not items:
        click.echo(f"No newsletters found for {target}.")
        return

    if dry_run:
        click.echo(f"[dry-run] Would send {len(items)} newsletter(s) to {to}:\n")
        for item in items:
            click.echo(
                f"  • {item['subject']}  —  {item['sender_name'] or item['sender_email']}"
            )
        return

    click.echo(f"Generating digest for {target} → {to}…")
    result = digest_gen.run_digest(to, run_date=target)
    if result["status"] == "sent":
        click.echo(f"Sent! {result['count']} newsletter(s) included.")
    elif result["status"] == "skipped":
        click.echo("Nothing to send today.")
    else:
        click.echo(f"Result: {result}")


# ── unsubscribe ───────────────────────────────────────────────────────────────


@cli.command()
@click.argument("email_fragment")
def unsubscribe(email_fragment: str) -> None:
    """Deactivate a subscription (fuzzy match on sender email).

    The unsubscribe link from the original newsletter is shown so you can
    complete the actual opt-out from the sender's side.
    """
    db = _db()
    subs = db.list_subscriptions(active_only=False)
    matches = [s for s in subs if email_fragment.lower() in s["sender_email"].lower()]

    if not matches:
        click.echo(f"No subscription matching "{email_fragment}".")
        sys.exit(1)

    if len(matches) > 1:
        click.echo("Multiple matches:")
        for i, s in enumerate(matches):
            click.echo(f"  [{i}] {s['sender_email']}  ({s['sender_name'] or ''})")
        idx = click.prompt("Select index", type=int)
        sub = matches[idx]
    else:
        sub = matches[0]

    click.echo(f"\nSubscription: {sub['sender_email']}")
    if not click.confirm("Deactivate (stop including in digest)?"):
        return

    db.deactivate_subscription(sub["sender_email"])
    click.echo(f"Deactivated {sub['sender_email']}.")
    if sub["unsubscribe_link"]:
        click.echo(f"\nUnsubscribe link from sender:\n  {sub['unsubscribe_link']}")
    else:
        click.echo("\nNo unsubscribe link recorded — visit the sender's website to opt out.")


# ── summarize ─────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--limit", default=50, show_default=True, help="Max items to process.")
def summarize(limit: int) -> None:
    """Run Claude summarization on stored newsletters that lack a summary."""
    if not config.ANTHROPIC_API_KEY:
        click.echo("ANTHROPIC_API_KEY is not set in .env.", err=True)
        sys.exit(1)

    db = _db()
    summarizer = NewsletterSummarizer(config.ANTHROPIC_API_KEY)
    items = db.get_unsummarized_items(limit=limit)

    if not items:
        click.echo("All newsletters are already summarized.")
        return

    click.echo(f"Summarizing {len(items)} newsletter(s)…")
    ok = err = 0
    with click.progressbar(items, label="Summarizing") as bar:
        for item in bar:
            try:
                summary, headlines = summarizer.summarize(
                    item["sender_name"] or item["sender_email"],
                    item["subject"] or "",
                    item["content"] or "",
                )
                db.update_item_summary(item["id"], summary, json.dumps(headlines))
                ok += 1
            except Exception as exc:
                logging.getLogger(__name__).debug("Summarize error: %s", exc)
                err += 1

    click.echo(f"Done — {ok} summarized, {err} error(s).")


# ── setup-gmail ───────────────────────────────────────────────────────────────


@cli.command("setup-gmail")
def setup_gmail() -> None:
    """Create Gmail label structure for newsletter management.

    Creates:
      Newsletters/               — parent label
      Newsletters/Unsubscribe    — apply this in Gmail to deactivate a subscription
    """
    gmail = _gmail()
    prefix = config.GMAIL_LABEL_PREFIX

    gmail.get_or_create_label(prefix)
    click.echo(f"  ✓  {prefix}")

    gmail.get_or_create_label(f"{prefix}/Unsubscribe")
    click.echo(f"  ✓  {prefix}/Unsubscribe")

    click.echo(
        f"\nSetup complete. In Gmail, apply '{prefix}/Unsubscribe' to any newsletter "
        "thread; the next `sync` will deactivate that subscription."
    )


# ── stats ─────────────────────────────────────────────────────────────────────


@cli.command()
def stats() -> None:
    """Show subscription and newsletter statistics."""
    s = _db().get_stats()
    sub = s["subscriptions"]
    items = s["items"]
    click.echo(
        f"\nSubscriptions : {sub['total']} total  "
        f"({sub['active']} active, {sub['inactive']} inactive)"
    )
    click.echo(
        f"Items stored  : {items['total_items']} across {items['days_with_items']} day(s)"
    )
    click.echo(f"Today         : {s['today']} newsletter(s) received")


# ── start (daemon) ────────────────────────────────────────────────────────────


@cli.command()
def start() -> None:
    """Start the background daemon: syncs every 2 h, sends digest at 7 AM."""
    if not config.DIGEST_RECIPIENT:
        click.echo("DIGEST_RECIPIENT is not set in .env.", err=True)
        sys.exit(1)

    gmail, db, summarizer, digest_gen = _all_clients()
    scheduler = NewsletterScheduler(config, gmail, db, summarizer, digest_gen)

    click.echo(
        f"Starting daemon…\n"
        f"  Daily digest : {config.DIGEST_TIME} {config.TIMEZONE} → {config.DIGEST_RECIPIENT}\n"
        f"  Sync         : every 2 hours\n"
        f"Press Ctrl-C to stop."
    )
    scheduler.start()


# ── entry point ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    cli()

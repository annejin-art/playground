import logging
from datetime import date, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class NewsletterScheduler:
    def __init__(self, config, gmail_client, database, summarizer, digest_generator):
        self.config = config
        self.gmail = gmail_client
        self.db = database
        self.summarizer = summarizer
        self.digest = digest_generator

    # ── Jobs ──────────────────────────────────────────────────────────────────

    def sync(self, lookback_days: int = 1) -> int:
        """Pull recent newsletters from Gmail into the database. Returns new item count."""
        logger.info("Starting newsletter sync (lookback=%d days)…", lookback_days)
        after = (date.today() - timedelta(days=lookback_days)).strftime("%Y/%m/%d")
        messages = self.gmail.get_recent_newsletters(
            self.config.SUBSCRIPTION_EMAIL, after_date=after
        )
        logger.info("Found %d newsletter messages in Gmail", len(messages))

        new_items = 0
        for msg_ref in messages:
            try:
                msg = self.gmail.get_message(msg_ref["id"])
                parsed = self.gmail.parse_message(msg)
                if not parsed["sender_email"]:
                    continue

                sub_id = self.db.upsert_subscription(
                    sender_email=parsed["sender_email"],
                    sender_name=parsed["sender_name"],
                    list_id=parsed["list_id"],
                    unsubscribe_link=parsed["unsubscribe"],
                )
                item_id = self.db.add_newsletter_item(
                    subscription_id=sub_id,
                    gmail_message_id=parsed["id"],
                    subject=parsed["subject"],
                    received_at=parsed["received_at"],
                    snippet=parsed["snippet"],
                    content=parsed["content"],
                )
                if item_id:
                    new_items += 1

                    # Apply Gmail label so the newsletter is visible under Newsletters/
                    try:
                        label_name = (
                            f"{self.config.GMAIL_LABEL_PREFIX}/"
                            f"{(parsed['sender_name'] or parsed['sender_email'])[:40]}"
                        )
                        label_id = self.gmail.get_or_create_label(label_name)
                        self.gmail.apply_labels(parsed["id"], [label_id])
                        self.db.set_label(parsed["sender_email"], label_id)
                    except Exception as exc:
                        logger.debug("Label apply failed for %s: %s", parsed["id"], exc)

            except Exception as exc:
                logger.warning("Skipped message %s: %s", msg_ref.get("id", "?"), exc)

        # Process any "Newsletters/Unsubscribe" labels the user applied in Gmail
        self._process_unsubscribe_labels()

        logger.info("Sync complete: %d new items", new_items)
        return new_items

    def _process_unsubscribe_labels(self) -> None:
        """Deactivate subscriptions where the user applied Newsletters/Unsubscribe in Gmail."""
        unsub_label = f"{self.config.GMAIL_LABEL_PREFIX}/Unsubscribe"
        try:
            label_id = self.gmail.get_or_create_label(unsub_label)
            messages = self.gmail.get_messages_with_label(label_id)
            for msg_ref in messages:
                try:
                    msg = self.gmail.get_message(msg_ref["id"], format="metadata")
                    parsed = self.gmail.parse_message(msg)
                    if parsed["sender_email"]:
                        self.db.deactivate_subscription(parsed["sender_email"])
                        logger.info(
                            "Unsubscribed from %s (via Gmail label)",
                            parsed["sender_email"],
                        )
                except Exception as exc:
                    logger.debug("Unsubscribe label processing error: %s", exc)
        except Exception as exc:
            logger.debug("Could not check unsubscribe labels: %s", exc)

    def run_daily_digest(self) -> None:
        logger.info("Running daily digest…")
        try:
            self.sync(lookback_days=1)
            result = self.digest.run_digest(self.config.DIGEST_RECIPIENT)
            logger.info("Digest result: %s", result)
        except Exception as exc:
            logger.error("Daily digest failed: %s", exc)

    # ── Daemon ────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the blocking scheduler (Ctrl-C to stop)."""
        scheduler = BlockingScheduler(timezone=self.config.TIMEZONE)

        hour, minute = self.config.DIGEST_TIME.split(":")
        scheduler.add_job(
            self.run_daily_digest,
            CronTrigger(hour=int(hour), minute=int(minute)),
            id="daily_digest",
            name="Daily Newsletter Digest",
            replace_existing=True,
        )
        scheduler.add_job(
            self.sync,
            IntervalTrigger(hours=2),
            id="sync_newsletters",
            name="Sync Newsletters",
            replace_existing=True,
        )

        logger.info(
            "Scheduler started — digest at %s %s, sync every 2 h",
            self.config.DIGEST_TIME,
            self.config.TIMEZONE,
        )
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped.")

import json
import re
from typing import List, Tuple

import anthropic

_SYSTEM_PROMPT = """\
You are a newsletter digest assistant. For each newsletter you receive:
1. Write a concise 2-3 sentence summary capturing the main theme and most important information.
2. Extract the top 3-5 headlines or key points as a JSON array of short strings.

Be factual, objective, and informative. Preserve proper nouns and key figures.\
"""


class NewsletterSummarizer:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def summarize(
        self, sender_name: str, subject: str, content: str
    ) -> Tuple[str, List[str]]:
        """Return (summary, headlines). Falls back to snippet on error or empty content."""
        if not content or len(content.strip()) < 80:
            return subject, []

        response = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            # Cache the static system prompt across repeated calls in the same session
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Newsletter from: {sender_name}\n"
                        f"Subject: {subject}\n\n"
                        f"{content[:4000]}\n\n"
                        "Reply with:\n"
                        "SUMMARY: <2-3 sentences>\n"
                        "HEADLINES: <json array of strings>"
                    ),
                }
            ],
        )

        text = response.content[0].text
        summary = self._field(text, "SUMMARY") or subject
        headlines = self._parse_headlines(self._field(text, "HEADLINES"))
        return summary, headlines

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _field(text: str, name: str) -> str:
        m = re.search(rf"{name}:\s*(.*?)(?=\n[A-Z]+:|$)", text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _parse_headlines(raw: str) -> List[str]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(h) for h in parsed[:5]]
        except json.JSONDecodeError:
            pass
        # Fallback: split on newlines / bullet markers
        lines = [
            re.sub(r"^[\-\*\•\d\.]+\s*", "", line).strip()
            for line in raw.splitlines()
            if line.strip() and not line.strip().startswith("[")
        ]
        return [l for l in lines if l][:5]

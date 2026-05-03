"""
Telegram Notifier - Sends push notifications to Telegram when leads are
found, qualified, or contacted. Gracefully does nothing if not configured.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}"


class TelegramNotifier:
    def __init__(self):
        self._token: Optional[str] = settings.TELEGRAM_BOT_TOKEN
        self._chat_id: Optional[str] = settings.TELEGRAM_CHAT_ID

    @property
    def enabled(self) -> bool:
        return bool(self._token and self._chat_id)

    async def send_message(self, text: str) -> bool:
        if not self.enabled:
            return False
        url = f"{API_BASE.format(token=self._token)}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                })
                if resp.status_code == 200:
                    return True
                logger.warning(f"Telegram API returned {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")
        return False

    # ── Agent-specific helpers ─────────────────────────────────

    async def notify_new_leads(
        self,
        count: int,
        services: dict[str, int],
        channels: dict[str, int],
    ):
        if count == 0:
            return
        svc_lines = ", ".join(f"{k} ({v})" for k, v in services.items())
        ch_lines = ", ".join(channels.keys())
        text = (
            f"<b>New Leads Found!</b>\n"
            f"{count} leads discovered\n"
            f"<b>Services:</b> {svc_lines}\n"
            f"<b>Channels:</b> {ch_lines}"
        )
        await self.send_message(text)

    async def notify_leads_qualified(
        self,
        qualified: list[dict],
    ):
        if not qualified:
            return
        if len(qualified) == 1:
            q = qualified[0]
            text = (
                f"<b>Lead Qualified!</b>\n"
                f"{q['name']} ({q['company']})\n"
                f"<b>Score:</b> {q['score']}% | <b>Service:</b> {q['service']}\n"
                f"<i>{q['summary']}</i>"
            )
        else:
            lines = "\n".join(
                f"  - {q['name']} ({q['company']}) — {q['score']}%"
                for q in qualified[:10]
            )
            text = (
                f"<b>{len(qualified)} Leads Qualified!</b>\n"
                f"{lines}"
            )
        await self.send_message(text)

    async def notify_outreach_sent(
        self,
        count: int,
        services: dict[str, int],
    ):
        if count == 0:
            return
        svc_lines = ", ".join(f"{k} ({v})" for k, v in services.items())
        text = (
            f"<b>Outreach Sent!</b>\n"
            f"{count} leads contacted\n"
            f"<b>Services:</b> {svc_lines}"
        )
        await self.send_message(text)


telegram = TelegramNotifier()

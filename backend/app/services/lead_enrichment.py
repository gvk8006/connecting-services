"""
Lead Enrichment Service - Enriches leads with LinkedIn URLs and phone numbers.
Uses DuckDuckGo search + page scraping to find contact details.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Lead

logger = logging.getLogger(__name__)

PHONE_REGEX = re.compile(
    r"(?:\+\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}"
)
LINKEDIN_REGEX = re.compile(
    r"https?://(?:www\.)?linkedin\.com/(?:in|company)/[\w-]+"
)
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

JUNK_PHONE_PATTERNS = [
    "000", "1234", "5678", "9999", "0000",
    "123456", "111111", "999999",
]


def _is_valid_phone(phone: str) -> bool:
    """Check if phone looks like a real number."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 8 or len(digits) > 15:
        return False
    if any(p in digits for p in JUNK_PHONE_PATTERNS):
        return False
    return True


def _clean_phone(phone: str) -> str:
    """Normalize phone format."""
    return phone.strip()


async def _search_ddg(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo for results."""
    import time
    from ddgs import DDGS

    def _do_search():
        for attempt in range(2):
            try:
                with DDGS() as ddgs:
                    return list(ddgs.text(query, region="wt-wt", max_results=max_results))
            except Exception:
                if attempt < 1:
                    time.sleep(3)
        return []

    return await asyncio.to_thread(_do_search)


async def _fetch_page(client: httpx.AsyncClient, url: str) -> str:
    """Fetch a page's HTML content."""
    try:
        resp = await client.get(url, follow_redirects=True, timeout=10.0)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return ""


async def _find_linkedin_for_company(company: str, website: str | None = None) -> str | None:
    """Try to find LinkedIn company page via DuckDuckGo."""
    if not company:
        return None

    query = f"{company} site:linkedin.com/company"
    try:
        results = await _search_ddg(query, 3)
        for r in results:
            href = r.get("href", "")
            if "linkedin.com/company/" in href or "linkedin.com/in/" in href:
                # Clean up tracking params
                parsed = urlparse(href)
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                return clean_url.rstrip("/")
    except Exception as e:
        logger.debug(f"LinkedIn search failed for {company}: {e}")

    return None


async def _find_phone_from_website(client: httpx.AsyncClient, website: str) -> str | None:
    """Try to find phone number from website or its contact page."""
    if not website:
        return None

    html = await _fetch_page(client, website)
    if not html:
        return None

    soup = BeautifulSoup(html[:80000], "html.parser")
    text = soup.get_text(" ", strip=True)

    # Look for phone numbers in page
    phones = PHONE_REGEX.findall(text)
    valid_phones = [_clean_phone(p) for p in phones if _is_valid_phone(p)]
    if valid_phones:
        return valid_phones[0]

    # Try contact page
    contact_url = None
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        link_text = a.get_text(strip=True).lower()
        if any(k in href or k in link_text for k in ["contact", "get-in-touch", "enquir"]):
            contact_href = a["href"]
            if contact_href.startswith("/"):
                parsed = urlparse(website)
                contact_url = f"{parsed.scheme}://{parsed.netloc}{contact_href}"
            elif contact_href.startswith("http"):
                contact_url = contact_href
            break

    if contact_url:
        contact_html = await _fetch_page(client, contact_url)
        if contact_html:
            contact_soup = BeautifulSoup(contact_html[:50000], "html.parser")
            contact_text = contact_soup.get_text(" ", strip=True)
            phones = PHONE_REGEX.findall(contact_text)
            valid_phones = [_clean_phone(p) for p in phones if _is_valid_phone(p)]
            if valid_phones:
                return valid_phones[0]

    # Check for tel: links
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("tel:"):
            phone = a["href"].replace("tel:", "").strip()
            if _is_valid_phone(phone):
                return _clean_phone(phone)

    return None


async def _find_email_from_website(client: httpx.AsyncClient, website: str) -> str | None:
    """Try to find email from website or contact page."""
    if not website:
        return None

    html = await _fetch_page(client, website)
    if not html:
        return None

    soup = BeautifulSoup(html[:80000], "html.parser")
    text = soup.get_text(" ", strip=True)

    # Check mailto: links first
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("mailto:"):
            email = a["href"].replace("mailto:", "").split("?")[0].strip()
            if "@" in email and not any(
                x in email.lower() for x in ["example", "noreply", "no-reply", "wordpress", "sentry"]
            ):
                return email

    # Regex from page text
    emails = EMAIL_REGEX.findall(text)
    junk_patterns = [
        "example.com", "email.com", "domain.com", "wixpress", "sentry",
        "noreply", "no-reply", "wordpress", "schema.org", "cloudflare",
    ]
    valid = [e for e in set(emails) if not any(j in e.lower() for j in junk_patterns)]
    if valid:
        return valid[0]

    return None


async def enrich_leads(session: AsyncSession, batch_size: int = 20) -> dict:
    """
    Enrich leads that are missing LinkedIn, phone, or email.
    Processes in batches to avoid rate limiting.
    """
    # Find leads missing data
    query = select(Lead).where(
        or_(
            Lead.linkedin_url.is_(None),
            Lead.phone.is_(None),
            Lead.email.is_(None),
        )
    ).order_by(Lead.score.desc()).limit(batch_size)

    result = await session.execute(query)
    leads = result.scalars().all()

    if not leads:
        return {"success": True, "enriched": 0, "message": "No leads need enrichment"}

    enriched_count = 0
    linkedin_found = 0
    phone_found = 0
    email_found = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    async with httpx.AsyncClient(timeout=12.0, headers=headers, follow_redirects=True) as client:
        for lead in leads:
            updated = False

            # Find LinkedIn if missing
            if not lead.linkedin_url and lead.company:
                linkedin = await _find_linkedin_for_company(lead.company, lead.website)
                if linkedin:
                    lead.linkedin_url = linkedin
                    linkedin_found += 1
                    updated = True
                await asyncio.sleep(3)  # Rate limit

            # Find phone if missing
            if not lead.phone and lead.website:
                phone = await _find_phone_from_website(client, lead.website)
                if phone:
                    lead.phone = phone
                    phone_found += 1
                    updated = True

            # Find email if missing
            if not lead.email and lead.website:
                email = await _find_email_from_website(client, lead.website)
                if email:
                    lead.email = email
                    email_found += 1
                    updated = True

            if updated:
                enriched_count += 1

            await asyncio.sleep(1)  # Small delay between leads

    await session.commit()

    return {
        "success": True,
        "enriched": enriched_count,
        "total_processed": len(leads),
        "linkedin_found": linkedin_found,
        "phone_found": phone_found,
        "email_found": email_found,
    }

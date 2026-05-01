"""
Prospector Tool - Autonomous multi-channel lead discovery agent.

STRATEGY: Finds people/businesses ACTIVELY SEEKING services (not providers).
Primary channels:
  1. Reddit search - people posting "need help with X", "looking for developer"
  2. DuckDuckGo forum-scoped search - Reddit, Quora, IndieHackers, Gumtree posts
  3. DuckDuckGo job/hiring search - job boards, freelancer platforms
  4. Google Custom Search API (if configured)
  5. Twitter/X API (if configured)

Each discovered lead is tagged with the service they need.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.models.models import Lead, LeadSource, LeadActivity
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"(?:\+44|0)\s?\d{3,4}\s?\d{3,4}\s?\d{3,4}")

# ---------------------------------------------------------------------------
# Provider detection: domains of companies that SELL services (not seeking)
# ---------------------------------------------------------------------------
PROVIDER_DOMAIN_KEYWORDS = [
    "agency", "studio", "digital", "creative", "design", "solutions",
    "technologies", "consulting", "software", "development", "developer",
    "devhouse", "webdev", "techno", "infotech", "codehouse", "labs",
    "media", "marketing", "seo", "hosting", "cloud",
]

KNOWN_PROVIDER_DOMAINS = {
    "wix.com", "squarespace.com", "godaddy.com", "wordpress.com",
    "shopify.com", "weebly.com", "webflow.com", "hubspot.com",
    "fiverr.com", "upwork.com", "toptal.com", "99designs.com",
    "clutch.co", "topdevelopers.co", "designrush.com", "goodfirms.co",
    "g2.com", "capterra.com", "trustpilot.com", "glassdoor.com",
    "orimon.ai", "intercom.com", "drift.com", "zendesk.com",
    "freshdesk.com", "tidio.com", "chatfuel.com", "manychat.com",
    "botpress.com", "landbot.io", "click4assistance.co.uk",
    "salesforce.com", "zoho.com", "pipedrive.com", "monday.com",
}

PROVIDER_TITLE_SIGNALS = [
    "top 10", "top 20", "best companies", "agency list",
    "development company", "development services", "our services",
    "hire us", "get a quote", "free consultation", "our portfolio",
    "we build", "we create", "we design", "we develop",
    "pricing plans", "our clients", "case studies",
    "web development company", "software development company",
    "digital agency", "design agency", "marketing agency",
]

# Seeker signals: phrases that indicate someone IS SEEKING a service
SEEKER_SIGNALS = [
    "looking for", "need someone to", "can anyone recommend",
    "hiring", "who can build", "help me find", "suggestions for",
    "need help with", "recommend me", "anyone know a good",
    "want to hire", "budget for", "how much does it cost",
    "where can I find", "need a developer", "need built",
    "my business needs", "our company needs", "looking to get",
    "i need", "we need", "seeking", "in search of",
]

JUNK_EMAIL_PATTERNS = [
    "example.com", "email.com", "domain.com", "wixpress", "sentry",
    "schema.org", "noreply", "no-reply", "unsubscribe", "wordpress",
    ".png", ".jpg", ".gif", "gravatar", "cloudflare", "google.com",
    "facebook.com", "twitter.com", "github.com",
]

# ---------------------------------------------------------------------------
# Seeker-focused search queries for each service category
# ---------------------------------------------------------------------------
# Queries now target community platforms where REAL PEOPLE ask for help.
# DuckDuckGo general queries are scoped to seeker platforms via site: filters.

SERVICE_CATEGORIES = {
    "website": {
        "label": "Website Development",
        "reddit_queries": [
            "need website built for my business",
            "looking for web developer recommendation",
            "who can build me a website",
            "recommend a web designer for small business",
            "need help getting a website made",
            "how much to hire someone to build a website",
        ],
        "forum_queries": [
            "site:reddit.com need website built for my business",
            "site:quora.com looking for web developer to build website",
            "site:gumtree.com web developer needed",
            "site:indiehackers.com need website built",
            "site:reddit.com recommend web designer small business",
            "site:community.shopify.com need custom website developer",
        ],
        "job_queries": [
            "site:indeed.co.uk web developer freelance",
            "site:reed.co.uk freelance website developer contract",
            "site:peopleperhour.com build website for business",
        ],
        "social_keywords": [
            "need a website built", "looking for web developer",
            "recommend a web designer", "website for my business",
            "need website help", "who builds websites",
        ],
        "reddit_subs": ["smallbusiness", "Entrepreneur", "freelance", "web_design", "webdev"],
    },
    "saas": {
        "label": "SaaS Tool Development",
        "reddit_queries": [
            "looking for developer to build my SaaS idea",
            "need technical cofounder for SaaS startup",
            "need MVP built for my SaaS",
            "who can build a SaaS product for me",
            "looking to hire developer for SaaS MVP",
            "recommend developer for SaaS platform",
        ],
        "forum_queries": [
            "site:reddit.com need SaaS MVP built",
            "site:indiehackers.com looking for developer to build SaaS",
            "site:quora.com need someone to build SaaS product",
            "site:reddit.com technical cofounder SaaS startup",
            "site:indiehackers.com need help building SaaS",
        ],
        "job_queries": [
            "site:indeed.co.uk SaaS developer freelance MVP",
            "site:angel.co looking for SaaS developer cofounder",
        ],
        "social_keywords": [
            "need SaaS built", "looking for SaaS developer",
            "SaaS MVP help", "build my SaaS idea",
        ],
        "reddit_subs": ["SaaS", "startups", "Entrepreneur", "microsaas", "indiehackers"],
    },
    "ai_agents": {
        "label": "AI Agents",
        "reddit_queries": [
            "need AI agent built for my business",
            "looking for someone to build AI automation",
            "need help automating with AI agents",
            "who can build custom AI assistant for my company",
            "looking for AI developer to automate workflows",
            "need AI chatbot agent for customer support",
        ],
        "forum_queries": [
            "site:reddit.com need AI agent built for business",
            "site:reddit.com looking for AI automation developer",
            "site:quora.com need custom AI agent for company",
            "site:indiehackers.com looking for AI developer",
            "site:reddit.com hire someone build AI automation",
        ],
        "job_queries": [
            "site:indeed.co.uk AI agent developer freelance",
            "site:reed.co.uk AI automation specialist contract",
        ],
        "social_keywords": [
            "need AI agent built", "looking for AI developer",
            "AI automation for business", "custom AI assistant",
        ],
        "reddit_subs": ["smallbusiness", "Entrepreneur", "ChatGPT", "artificial", "AutoGPT"],
    },
    "chatbot": {
        "label": "Chatbot Development",
        "reddit_queries": [
            "need chatbot for my website customer support",
            "looking for someone to build chatbot",
            "recommend chatbot developer for business",
            "need WhatsApp chatbot for my business",
            "want to add chatbot to my website",
            "looking for GPT chatbot developer",
        ],
        "forum_queries": [
            "site:reddit.com need chatbot built for website",
            "site:quora.com looking for chatbot developer",
            "site:reddit.com recommend chatbot for business",
            "site:indiehackers.com need chatbot for customer service",
            "site:reddit.com WhatsApp chatbot for business",
        ],
        "job_queries": [
            "site:indeed.co.uk chatbot developer freelance",
            "site:peopleperhour.com build chatbot for website",
        ],
        "social_keywords": [
            "need a chatbot built", "looking for chatbot developer",
            "chatbot for my website", "customer service chatbot help",
        ],
        "reddit_subs": ["smallbusiness", "Entrepreneur", "CustomerService", "chatbots"],
    },
    "web_app": {
        "label": "Web Application",
        "reddit_queries": [
            "need custom web application built",
            "looking for developer to build web app",
            "need help building a web platform",
            "recommend a full stack developer for web app",
            "need React or Next.js developer for project",
            "looking for team to build my web app idea",
        ],
        "forum_queries": [
            "site:reddit.com need web app built for business",
            "site:indiehackers.com looking for developer to build web app",
            "site:quora.com need custom web application developer",
            "site:reddit.com recommend full stack developer web app",
        ],
        "job_queries": [
            "site:indeed.co.uk full stack developer freelance web app",
            "site:reed.co.uk React developer contract web application",
        ],
        "social_keywords": [
            "need web app built", "looking for full stack developer",
            "custom web application help", "build my web platform",
        ],
        "reddit_subs": ["webdev", "reactjs", "startups", "Entrepreneur", "freelance"],
    },
    "crm": {
        "label": "CRM Development",
        "reddit_queries": [
            "need custom CRM built for my business",
            "looking for developer to build CRM system",
            "need alternative to Salesforce custom CRM",
            "recommend CRM developer for small business",
            "need bespoke CRM for real estate",
            "looking for someone to build CRM from scratch",
        ],
        "forum_queries": [
            "site:reddit.com need custom CRM built",
            "site:quora.com looking for CRM developer",
            "site:reddit.com custom CRM alternative Salesforce",
            "site:indiehackers.com need CRM built for business",
        ],
        "job_queries": [
            "site:indeed.co.uk CRM developer freelance custom",
            "site:reed.co.uk bespoke CRM development contract",
        ],
        "social_keywords": [
            "need custom CRM", "looking for CRM developer",
            "build CRM for business", "custom CRM system",
        ],
        "reddit_subs": ["CRM", "smallbusiness", "sales", "Entrepreneur"],
    },
    "qc_ai": {
        "label": "Quality Check AI Tool",
        "reddit_queries": [
            "need AI quality control tool for manufacturing",
            "looking for automated visual inspection system",
            "need AI for quality assurance process",
            "anyone recommend AI QC inspection tool",
            "looking for AI testing and quality tool",
            "need machine learning quality control system",
        ],
        "forum_queries": [
            "site:reddit.com need AI quality control tool",
            "site:quora.com AI quality assurance for manufacturing",
            "site:reddit.com automated quality inspection AI",
            "site:reddit.com need AI for QC process",
        ],
        "job_queries": [
            "site:indeed.co.uk AI quality control specialist",
            "site:reed.co.uk machine learning QC engineer",
        ],
        "social_keywords": [
            "need AI quality control", "looking for QC automation",
            "AI inspection system help", "quality assurance AI tool",
        ],
        "reddit_subs": ["MachineLearning", "manufacturing", "QualityAssurance", "smallbusiness"],
    },
}


class ProspectorTool(BaseAgent):
    """
    Seeker-focused prospecting tool that finds people/businesses ACTIVELY
    LOOKING FOR services - not service providers.

    Channels (ordered by quality for finding seekers):
    1. Reddit search - people posting in communities asking for help
    2. DDG forum-scoped search - Reddit, Quora, IndieHackers, Gumtree posts
    3. DDG job-board search - Indeed, Reed, PeoplePerHour postings
    4. Google Custom Search API (if configured)
    5. Twitter/X API (if configured)

    Provider detection filters ensure we skip company/agency websites.
    """

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_company_from_url(url: str) -> Optional[str]:
        """Extract a company name from a URL's domain."""
        try:
            domain = urlparse(url).netloc.replace("www.", "")
            name = domain.split(".")[0]
            if name and len(name) > 2 and name not in ("com", "org", "net", "co"):
                return name.replace("-", " ").replace("_", " ").title()
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_page_info(html: str, url: str) -> dict:
        """Extract useful lead info from a page's HTML."""
        info: dict = {"emails": [], "phones": [], "company": None, "contact_url": None}
        try:
            soup = BeautifulSoup(html[:80000], "html.parser")

            og_site = soup.find("meta", property="og:site_name")
            if og_site and og_site.get("content"):
                info["company"] = og_site["content"].strip()
            elif soup.title and soup.title.string:
                raw = soup.title.string.strip()
                for sep in [" | ", " - ", " :: ", " — ", " – "]:
                    if sep in raw:
                        raw = raw.split(sep)[0].strip()
                        break
                if len(raw) < 60:
                    info["company"] = raw

            text = soup.get_text(" ", strip=True)[:30000]
            emails = EMAIL_REGEX.findall(text)
            info["emails"] = [
                e for e in set(emails)
                if not any(j in e.lower() for j in JUNK_EMAIL_PATTERNS)
            ][:3]

            phones = PHONE_REGEX.findall(text)
            info["phones"] = list(set(phones))[:2]

            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                link_text = a.get_text(strip=True).lower()
                if any(k in href or k in link_text for k in ["contact", "get-in-touch", "enquir"]):
                    info["contact_url"] = a["href"]
                    break
        except Exception:
            pass
        return info

    @classmethod
    def _is_provider_url(cls, url: str, title: str = "", body: str = "") -> bool:
        """
        Detect if a URL/result belongs to a SERVICE PROVIDER rather than
        a service seeker. Returns True if it looks like a provider.
        """
        url_lower = url.lower()

        # 1. Check known provider domains
        domain = urlparse(url_lower).netloc.replace("www.", "")
        if domain in KNOWN_PROVIDER_DOMAINS:
            return True

        # 2. Check domain keywords that indicate an agency/provider
        domain_name = domain.split(".")[0] if domain else ""
        if any(kw in domain_name for kw in PROVIDER_DOMAIN_KEYWORDS):
            return True

        # 3. Check title/body for provider signals
        combined = f"{title} {body}".lower()
        provider_hits = sum(1 for sig in PROVIDER_TITLE_SIGNALS if sig in combined)
        if provider_hits >= 2:
            return True

        return False

    @classmethod
    def _has_seeker_signals(cls, text: str) -> bool:
        """Check if text contains signals that someone is SEEKING a service."""
        text_lower = text.lower()
        return any(sig in text_lower for sig in SEEKER_SIGNALS)

    @classmethod
    def _is_community_url(cls, url: str) -> bool:
        """Check if URL is from a community/forum platform (likely a seeker)."""
        community_domains = [
            "reddit.com", "quora.com", "indiehackers.com", "gumtree.com",
            "peopleperhour.com", "indeed.co.uk", "reed.co.uk", "angel.co",
            "community.shopify.com", "stackoverflow.com", "hackernews",
        ]
        url_lower = url.lower()
        return any(d in url_lower for d in community_domains)

    # ------------------------------------------------------------------
    # Main execute
    # ------------------------------------------------------------------

    async def execute(self, session: AsyncSession, params: dict = None) -> dict:
        params = params or {}
        target_services = params.get("services", list(SERVICE_CATEGORIES.keys()))
        channels = params.get("channels", self.config.get(
            "channels", ["reddit", "ddg_forums", "ddg_jobs", "google", "twitter"]
        ))
        max_per_service = params.get("max_per_service", self.config.get("max_per_service", 15))
        # Prospecting mode: "seekers_only" (default), "providers_only", "both"
        prospecting_mode = params.get("prospecting_mode", self.config.get("prospecting_mode", "seekers_only"))

        all_leads = []
        stats = {"reddit": 0, "ddg_forums": 0, "ddg_jobs": 0, "google": 0, "twitter": 0, "providers_found": 0}

        for service_key in target_services:
            if service_key not in SERVICE_CATEGORIES:
                continue
            service = SERVICE_CATEGORIES[service_key]
            service_leads = []

            # --- Seeker channels (when mode is seekers_only or both) ---
            if prospecting_mode in ("seekers_only", "both"):
                # Channel 1: Reddit (highest quality for finding seekers)
                if "reddit" in channels:
                    try:
                        reddit_leads = await self._search_reddit(service_key, service)
                        service_leads.extend(reddit_leads)
                        stats["reddit"] += len(reddit_leads)
                        logger.info(f"Reddit found {len(reddit_leads)} seeker leads for {service_key}")
                    except Exception as e:
                        logger.warning(f"Reddit search failed for {service_key}: {e}")

                # Channel 2: DDG forum-scoped search
                if "ddg_forums" in channels:
                    try:
                        forum_leads = await self._search_ddg_forums(service_key, service)
                        service_leads.extend(forum_leads)
                        stats["ddg_forums"] += len(forum_leads)
                        logger.info(f"DDG forums found {len(forum_leads)} seeker leads for {service_key}")
                    except Exception as e:
                        logger.warning(f"DDG forum search failed for {service_key}: {e}")

                # Channel 3: DDG job-board scoped search
                if "ddg_jobs" in channels:
                    try:
                        job_leads = await self._search_ddg_jobs(service_key, service)
                        service_leads.extend(job_leads)
                        stats["ddg_jobs"] += len(job_leads)
                        logger.info(f"DDG jobs found {len(job_leads)} seeker leads for {service_key}")
                    except Exception as e:
                        logger.warning(f"DDG job search failed for {service_key}: {e}")

                # Channel 4: Google Custom Search API (if configured)
                if "google" in channels:
                    try:
                        google_leads = await self._search_google(service_key, service)
                        service_leads.extend(google_leads)
                        stats["google"] += len(google_leads)
                    except Exception as e:
                        logger.warning(f"Google search failed for {service_key}: {e}")

                # Channel 5: Twitter/X API (if configured)
                if "twitter" in channels:
                    try:
                        twitter_leads = await self._search_twitter(service_key, service)
                        service_leads.extend(twitter_leads)
                        stats["twitter"] += len(twitter_leads)
                    except Exception as e:
                        logger.warning(f"Twitter search failed for {service_key}: {e}")

            # --- Provider channel (when mode is providers_only or both) ---
            if prospecting_mode in ("providers_only", "both"):
                try:
                    provider_leads = await self._search_providers(service_key, service)
                    service_leads.extend(provider_leads)
                    stats["providers_found"] += len(provider_leads)
                    logger.info(f"Found {len(provider_leads)} provider leads for {service_key}")
                except Exception as e:
                    logger.warning(f"Provider search failed for {service_key}: {e}")

            all_leads.extend(service_leads[:max_per_service])
            await asyncio.sleep(2)  # Rate limit between services

        # Deduplicate and save
        saved = 0
        seen = set()
        for lead_data in all_leads:
            identifier = lead_data.get("email") or lead_data.get("twitter_handle") or lead_data.get("source_url", "")
            if not identifier or identifier in seen:
                continue
            seen.add(identifier)

            # Check existing by email
            if lead_data.get("email"):
                existing = await session.execute(
                    select(Lead).where(Lead.email == lead_data["email"])
                )
                if existing.scalar_one_or_none():
                    continue

            # Check existing by source_url
            if lead_data.get("source_url"):
                existing = await session.execute(
                    select(Lead).where(Lead.source_url == lead_data["source_url"])
                )
                if existing.scalar_one_or_none():
                    continue

            lead = Lead(
                first_name=lead_data.get("first_name"),
                last_name=lead_data.get("last_name"),
                email=lead_data.get("email"),
                phone=lead_data.get("phone"),
                company=lead_data.get("company"),
                job_title=lead_data.get("job_title"),
                website=lead_data.get("website"),
                twitter_handle=lead_data.get("twitter_handle"),
                linkedin_url=lead_data.get("linkedin_url"),
                source=lead_data.get("source", LeadSource.WEB_SCRAPE),
                source_url=lead_data.get("source_url"),
                location=lead_data.get("location"),
                notes=lead_data.get("notes"),
                industry=lead_data.get("industry"),
                tags=lead_data.get("tags", []),
                lead_type=lead_data.get("lead_type", "seeker"),
                custom_fields={
                    "service_needed": lead_data.get("service_needed", "website"),
                    "lead_type": lead_data.get("lead_type", "seeker"),
                },
            )
            session.add(lead)
            await session.flush()

            lead_type_str = lead_data.get("lead_type", "seeker")
            lead_type_label = "SERVICE SEEKER" if lead_type_str == "seeker" else "SERVICE PROVIDER"
            activity = LeadActivity(
                lead_id=lead.id,
                activity_type="prospected",
                description=f"{lead_type_label} found via {lead_data.get('channel', 'search')} - {lead_data.get('service_needed', 'unknown')}",
                extra_data={
                    "service_needed": lead_data.get("service_needed"),
                    "channel": lead_data.get("channel"),
                    "lead_type": lead_type_str,
                    "original_post": lead_data.get("notes", "")[:500],
                },
            )
            session.add(activity)
            saved += 1

        await session.commit()

        return {
            "success": True,
            "leads_count": saved,
            "total_found": len(all_leads),
            "services_searched": target_services,
            "channels_used": channels,
            "channel_stats": stats,
            "prospecting_mode": prospecting_mode,
        }

    async def _search_google(self, service_key: str, service: dict) -> list[dict]:
        """Search Google Custom Search API - filtered for seeker content."""
        from app.core.config import settings
        leads = []

        if not settings.GOOGLE_API_KEY or not settings.GOOGLE_CSE_ID:
            logger.info("Google API not configured, skipping Google search")
            return leads

        async with httpx.AsyncClient(timeout=15.0) as client:
            for query in service.get("reddit_queries", [])[:3]:
                try:
                    resp = await client.get(
                        "https://www.googleapis.com/customsearch/v1",
                        params={
                            "key": settings.GOOGLE_API_KEY,
                            "cx": settings.GOOGLE_CSE_ID,
                            "q": f"{query} site:reddit.com OR site:quora.com",
                            "num": 5,
                        },
                    )
                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    for item in data.get("items", []):
                        url = item.get("link", "")
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")

                        # Skip provider results
                        if self._is_provider_url(url, title, snippet):
                            continue

                        try:
                            page_resp = await client.get(url, follow_redirects=True, timeout=10.0)
                            page_text = page_resp.text
                            emails = EMAIL_REGEX.findall(page_text)
                            emails = [
                                e for e in set(emails)
                                if not any(x in e for x in JUNK_EMAIL_PATTERNS)
                            ]

                            for email in emails[:2]:
                                name_parts = email.split("@")[0].replace(".", " ").replace("_", " ").split()
                                leads.append({
                                    "email": email,
                                    "first_name": name_parts[0].title() if name_parts else None,
                                    "last_name": name_parts[1].title() if len(name_parts) > 1 else None,
                                    "source_url": url,
                                    "notes": f"Google (seeker): {title} - {snippet[:200]}",
                                    "source": LeadSource.GOOGLE_SEARCH,
                                    "service_needed": service_key,
                                    "channel": "google",
                                    "tags": [service_key, "google", "seeker", "prospector"],
                                })
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f"Google search query failed: {e}")

        return leads

    # ------------------------------------------------------------------
    # Reddit search (BEST channel for finding service seekers)
    # ------------------------------------------------------------------

    async def _search_reddit(self, service_key: str, service: dict) -> list[dict]:
        """
        Search Reddit for people actively SEEKING services.
        Uses DuckDuckGo site:reddit.com queries since Reddit's JSON API
        blocks automated requests (403). DDG reliably indexes Reddit posts.
        """
        leads = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
            for query in service.get("reddit_queries", [])[:4]:
                try:
                    search_query = f"site:reddit.com {query}"
                    results = await asyncio.to_thread(
                        self._ddg_text_search, search_query, 10
                    )
                    await asyncio.sleep(8)  # Rate limit DDG

                    for r in results:
                        url = r.get("href", "")
                        title = r.get("title", "")
                        body = r.get("body", "")

                        if "reddit.com" not in url:
                            continue

                        # Only keep results with seeker signals
                        combined_text = f"{title} {body}"
                        if not self._has_seeker_signals(combined_text):
                            continue

                        # Try to extract author from page
                        author_name = None
                        post_emails = []
                        try:
                            page_resp = await client.get(url, timeout=10.0)
                            if page_resp.status_code == 200:
                                page_text = page_resp.text[:50000]
                                post_emails = [
                                    e for e in EMAIL_REGEX.findall(page_text)
                                    if not any(j in e.lower() for j in JUNK_EMAIL_PATTERNS)
                                ]
                                soup = BeautifulSoup(page_text, "html.parser")
                                author_el = (
                                    soup.select_one("a.author")
                                    or soup.select_one("[data-testid='post_author_link']")
                                    or soup.select_one("shreddit-post")
                                )
                                if author_el:
                                    author_name = (
                                        author_el.get("author")
                                        or author_el.get_text(strip=True).lstrip("u/")
                                    )
                        except Exception:
                            pass

                        # Extract subreddit from URL
                        sub_match = re.search(r"/r/(\w+)/", url)
                        sub_name = sub_match.group(1) if sub_match else "unknown"

                        lead_data = {
                            "first_name": author_name,
                            "twitter_handle": f"u/{author_name}" if author_name else None,
                            "source_url": url,
                            "notes": f"Reddit SEEKER r/{sub_name}: {title}\n{body[:400]}",
                            "source": LeadSource.WEB_SCRAPE,
                            "service_needed": service_key,
                            "channel": "reddit",
                            "tags": [service_key, "reddit", f"r/{sub_name}", "seeker", "prospector"],
                        }

                        if post_emails:
                            lead_data["email"] = post_emails[0]

                        leads.append(lead_data)

                except Exception as e:
                    logger.warning(f"Reddit DDG search failed for '{query}': {e}")

                await asyncio.sleep(1.5)

        return leads

    # ------------------------------------------------------------------
    # Twitter/X search
    # ------------------------------------------------------------------

    async def _search_twitter(self, service_key: str, service: dict) -> list[dict]:
        """Search Twitter/X API for people seeking services."""
        from app.core.config import settings
        leads = []

        if not settings.TWITTER_BEARER_TOKEN:
            logger.info("Twitter token not configured, skipping Twitter search")
            return leads

        headers = {"Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            for keyword in service.get("social_keywords", [])[:3]:
                try:
                    resp = await client.get(
                        "https://api.twitter.com/2/tweets/search/recent",
                        params={
                            "query": f"{keyword} -is:retweet lang:en",
                            "max_results": 10,
                            "tweet.fields": "author_id,created_at,text",
                            "expansions": "author_id",
                            "user.fields": "name,username,description,location,url",
                        },
                        headers=headers,
                    )

                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

                    for tweet in data.get("data", []):
                        tweet_text = tweet.get("text", "")

                        # Only keep tweets with seeker signals
                        if not self._has_seeker_signals(tweet_text):
                            continue

                        author = users.get(tweet.get("author_id"), {})
                        name_parts = author.get("name", "").split(" ", 1)

                        leads.append({
                            "first_name": name_parts[0] if name_parts else None,
                            "last_name": name_parts[1] if len(name_parts) > 1 else None,
                            "twitter_handle": f"@{author.get('username', '')}",
                            "location": author.get("location"),
                            "website": author.get("url"),
                            "notes": f"Tweet (seeker): {tweet_text[:500]}",
                            "source": LeadSource.TWITTER,
                            "service_needed": service_key,
                            "channel": "twitter",
                            "tags": [service_key, "twitter", "seeker", "prospector"],
                        })

                except Exception as e:
                    logger.warning(f"Twitter search failed for '{keyword}': {e}")

        return leads

    # ------------------------------------------------------------------
    # Provider search (finds agencies/freelancers OFFERING services)
    # ------------------------------------------------------------------

    async def _search_providers(self, service_key: str, service: dict) -> list[dict]:
        """
        Search for service PROVIDERS (agencies, freelancers) offering the given service.
        Uses DDG to find companies that provide these services, using the provider
        detection filters in REVERSE - here we WANT provider results.
        """
        leads = []
        label = service.get("label", service_key)

        provider_queries = [
            f"{label} agency services",
            f"freelance {label.lower()} developer for hire",
            f"{label.lower()} company portfolio",
        ]

        for query in provider_queries[:2]:
            try:
                results = await asyncio.to_thread(
                    self._ddg_text_search, query, 8
                )
                await asyncio.sleep(8)

                for r in results:
                    url = r.get("href", "")
                    title = r.get("title", "")
                    body = r.get("body", "")

                    # Skip community/forum URLs (those are seekers, not providers)
                    if self._is_community_url(url):
                        continue

                    # We WANT provider URLs here (inverted filter)
                    if not self._is_provider_url(url, title, body):
                        # If it doesn't look like a provider, skip
                        continue

                    company = self._extract_company_from_url(url)

                    lead_data = {
                        "company": company or title[:100],
                        "website": url,
                        "source_url": url,
                        "notes": f"Provider ({label}): {title}\n{body[:300]}",
                        "source": LeadSource.WEB_SCRAPE,
                        "service_needed": service_key,
                        "channel": "ddg_providers",
                        "lead_type": "provider",
                        "tags": [service_key, "provider", "prospector"],
                    }

                    # Try to get contact info
                    try:
                        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                            page_resp = await client.get(url, timeout=10.0)
                            if page_resp.status_code == 200:
                                page_info = self._extract_page_info(page_resp.text, url)
                                if page_info.get("emails"):
                                    lead_data["email"] = page_info["emails"][0]
                                if page_info.get("phones"):
                                    lead_data["phone"] = page_info["phones"][0]
                                if page_info.get("company"):
                                    lead_data["company"] = page_info["company"]
                    except Exception:
                        pass

                    leads.append(lead_data)

            except Exception as e:
                logger.warning(f"Provider search failed for '{query}': {e}")

            await asyncio.sleep(1.5)

        return leads

    # ------------------------------------------------------------------
    # DuckDuckGo helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ddg_text_search(query: str, max_results: int = 8) -> list[dict]:
        """
        Search DuckDuckGo HTML directly via httpx (no library dependency).
        Returns list of dicts with 'href', 'title', 'body' keys.
        Uses POST to html.duckduckgo.com which is more reliable than GET
        and handles 202 rate-limit responses with exponential backoff.
        """
        import time
        import httpx as _httpx
        from bs4 import BeautifulSoup as _BS

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Referer": "https://html.duckduckgo.com/",
        }

        results = []
        for attempt in range(4):
            try:
                with _httpx.Client(timeout=20.0, headers=headers, follow_redirects=True) as client:
                    # Use POST which DDG HTML form uses (more reliable)
                    resp = client.post(
                        "https://html.duckduckgo.com/html/",
                        data={"q": query, "b": "", "kl": "uk-en"},
                    )
                    # 202 = rate limited / bot check, back off and retry
                    if resp.status_code == 202:
                        wait = 5 * (attempt + 1)
                        logger.info(f"DDG returned 202, waiting {wait}s (attempt {attempt+1}/4)")
                        time.sleep(wait)
                        continue
                    if resp.status_code != 200:
                        time.sleep(3 * (attempt + 1))
                        continue

                    soup = _BS(resp.text, "html.parser")
                    for result_div in soup.select(".result"):
                        link_el = result_div.select_one(".result__a")
                        snippet_el = result_div.select_one(".result__snippet")
                        if not link_el:
                            continue

                        href = link_el.get("href", "")
                        # Skip DDG ad links
                        if "duckduckgo.com/y.js" in href or "ad_provider" in href:
                            continue
                        # DDG wraps URLs in redirect; extract actual URL
                        if "uddg=" in href:
                            from urllib.parse import unquote, parse_qs, urlparse as _urlparse
                            parsed = _urlparse(href)
                            qs = parse_qs(parsed.query)
                            href = unquote(qs.get("uddg", [href])[0])

                        title = link_el.get_text(strip=True)
                        body = snippet_el.get_text(strip=True) if snippet_el else ""

                        results.append({"href": href, "title": title, "body": body})
                        if len(results) >= max_results:
                            break

                    return results

            except Exception as e:
                if attempt < 3:
                    time.sleep(3 * (attempt + 1))
                else:
                    logger.warning(f"DDG search failed after 4 attempts: {e}")
                    raise e

        return results

    # ------------------------------------------------------------------
    # DDG forum-scoped search (finds seeker posts on community platforms)
    # ------------------------------------------------------------------

    async def _search_ddg_forums(self, service_key: str, service: dict) -> list[dict]:
        """
        Search DuckDuckGo with site: scoping to community platforms.
        This finds actual forum posts from people asking for services,
        NOT provider/agency websites.
        """
        leads = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        for query in service.get("forum_queries", [])[:4]:
            try:
                results = await asyncio.to_thread(
                    self._ddg_text_search, query, 10
                )

                await asyncio.sleep(8)  # Rate limit between DDG queries

                async with httpx.AsyncClient(
                    timeout=12.0, headers=headers, follow_redirects=True
                ) as client:
                    for r in results:
                        url = r.get("href", "")
                        title = r.get("title", "")
                        body = r.get("body", "")

                        # Skip social media noise, images, videos
                        if any(d in url for d in [
                            "facebook.com", "youtube.com", "instagram.com",
                            "tiktok.com", "wikipedia.org", "amazon.com",
                            "bing.com/aclick",
                        ]):
                            continue

                        # Skip if it's a provider website (not a community post)
                        if not self._is_community_url(url) and self._is_provider_url(url, title, body):
                            continue

                        # Determine source type
                        source_tag = "forum"
                        if "reddit.com" in url:
                            source_tag = "reddit"
                        elif "quora.com" in url:
                            source_tag = "quora"
                        elif "indiehackers.com" in url:
                            source_tag = "indiehackers"
                        elif "gumtree.com" in url:
                            source_tag = "gumtree"
                        elif "indeed" in url or "reed.co.uk" in url:
                            source_tag = "job_board"

                        # Try visiting the page for extra info
                        page_emails = []
                        author_name = None
                        try:
                            page_resp = await client.get(url, timeout=10.0)
                            if page_resp.status_code == 200:
                                page_text = page_resp.text[:50000]
                                page_emails = [
                                    e for e in EMAIL_REGEX.findall(page_text)
                                    if not any(x in e.lower() for x in JUNK_EMAIL_PATTERNS)
                                ]

                                if "reddit.com" in url:
                                    soup = BeautifulSoup(page_text, "html.parser")
                                    author_el = (
                                        soup.select_one("a.author")
                                        or soup.select_one("[data-testid='post_author_link']")
                                    )
                                    if author_el:
                                        author_name = author_el.get_text(strip=True).lstrip("u/")
                        except Exception:
                            pass

                        lead_data = {
                            "source_url": url,
                            "notes": f"Forum SEEKER ({source_tag}): {title}\n{body[:300]}",
                            "source": LeadSource.WEB_SCRAPE,
                            "service_needed": service_key,
                            "channel": "ddg_forums",
                            "tags": [service_key, source_tag, "seeker", "prospector"],
                        }

                        if page_emails:
                            lead_data["email"] = page_emails[0]
                            name_parts = (
                                page_emails[0].split("@")[0]
                                .replace(".", " ").replace("_", " ")
                                .split()
                            )
                            lead_data["first_name"] = name_parts[0].title() if name_parts else None
                            lead_data["last_name"] = name_parts[1].title() if len(name_parts) > 1 else None
                        elif author_name:
                            lead_data["first_name"] = author_name
                            lead_data["twitter_handle"] = f"u/{author_name}"

                        leads.append(lead_data)

            except Exception as e:
                logger.warning(f"DDG forum search failed for '{query}': {e}")

            await asyncio.sleep(1.5)

        return leads

    # ------------------------------------------------------------------
    # DDG job-board scoped search (finds hiring/project posts)
    # ------------------------------------------------------------------

    async def _search_ddg_jobs(self, service_key: str, service: dict) -> list[dict]:
        """
        Search DuckDuckGo scoped to job boards and freelancer platforms.
        These are people actively HIRING / posting projects.
        """
        leads = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        for query in service.get("job_queries", [])[:3]:
            try:
                results = await asyncio.to_thread(
                    self._ddg_text_search, query, 8
                )

                await asyncio.sleep(8)

                async with httpx.AsyncClient(
                    timeout=12.0, headers=headers, follow_redirects=True
                ) as client:
                    for r in results:
                        url = r.get("href", "")
                        title = r.get("title", "")
                        body = r.get("body", "")

                        # Skip non-job-board results and providers
                        if not self._is_community_url(url) and self._is_provider_url(url, title, body):
                            continue

                        # Try to extract info from the page
                        page_info = {"emails": [], "phones": [], "company": None}
                        try:
                            page_resp = await client.get(url, timeout=10.0)
                            if page_resp.status_code == 200:
                                page_info = self._extract_page_info(page_resp.text, url)
                        except Exception:
                            pass

                        company = page_info.get("company") or self._extract_company_from_url(url)

                        lead_data = {
                            "company": company,
                            "source_url": url,
                            "notes": f"Job posting (seeker): {title}\n{body[:300]}",
                            "source": LeadSource.WEB_SCRAPE,
                            "service_needed": service_key,
                            "channel": "ddg_jobs",
                            "tags": [service_key, "job_board", "seeker", "prospector"],
                        }

                        if page_info.get("emails"):
                            lead_data["email"] = page_info["emails"][0]
                        if page_info.get("phones"):
                            lead_data["phone"] = page_info["phones"][0]

                        leads.append(lead_data)

            except Exception as e:
                logger.warning(f"DDG job search failed for '{query}': {e}")

            await asyncio.sleep(1.5)

        return leads

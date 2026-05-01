"""
Matching Engine - Connects service seekers with best-fit providers.

Scoring algorithm (weighted 0-100):
  - Service alignment  (35%): provider offers the requested service category
  - Budget fit         (25%): request budget overlaps provider's range
  - Location match     (15%): text similarity between locations
  - Provider rating    (15%): average_rating normalised to 0-15
  - Success history    (10%): success_rate * 10
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ProviderProfile,
    ServiceRequest,
    Match,
    MatchStatus,
    Lead,
)

logger = logging.getLogger(__name__)

DEFAULT_TOP_N = 5

# Alias map: maps request categories to provider service labels that satisfy them
SERVICE_ALIASES: dict[str, set[str]] = {
    "website": {"website", "web_design", "web_development", "web_dev", "wordpress"},
    "web_design": {"website", "web_design", "web_development"},
    "web_development": {"website", "web_design", "web_development", "web_dev"},
    "seo": {"seo", "digital_marketing", "marketing"},
    "digital_marketing": {"digital_marketing", "seo", "marketing", "social_media"},
    "social_media": {"social_media", "digital_marketing", "marketing"},
    "marketing": {"marketing", "digital_marketing", "seo", "social_media"},
    "chatbot": {"chatbot", "ai", "automation", "web_development"},
    "crm": {"crm", "web_development", "web_app", "automation"},
    "web_app": {"web_app", "web_development", "web_design"},
    "ai": {"ai", "chatbot", "automation"},
    "automation": {"automation", "ai", "chatbot"},
    "branding": {"branding", "design", "digital_marketing"},
    "design": {"design", "branding", "web_design"},
}


def _service_matches(request_category: str, provider_services: list[str]) -> bool:
    """Check if a provider's services match a request category, using aliases."""
    if not request_category or not provider_services:
        return False
    cat = request_category.lower().strip()
    prov_set = {s.lower().strip() for s in provider_services}
    # Direct match
    if cat in prov_set:
        return True
    # Alias match
    aliases = SERVICE_ALIASES.get(cat, {cat})
    return bool(aliases & prov_set)


def _budget_overlap_score(
    req_min: float | None,
    req_max: float | None,
    prov_min: float | None,
    prov_max: float | None,
) -> float:
    """Return 0-1 representing how well budgets overlap."""
    # If either side has no budget info, give neutral score
    if (req_min is None and req_max is None) or (prov_min is None and prov_max is None):
        return 0.6

    r_lo = req_min or 0.0
    r_hi = req_max or float("inf")
    p_lo = prov_min or 0.0
    p_hi = prov_max or float("inf")

    overlap_lo = max(r_lo, p_lo)
    overlap_hi = min(r_hi, p_hi)

    if overlap_lo <= overlap_hi:
        return 1.0  # Ranges overlap
    # No overlap — how far apart?
    gap = overlap_lo - overlap_hi
    ref = max(r_hi if r_hi != float("inf") else r_lo, p_hi if p_hi != float("inf") else p_lo, 1.0)
    closeness = max(0.0, 1.0 - gap / ref)
    return closeness * 0.5  # partial credit


def _location_similarity(loc_a: str | None, loc_b: str | None) -> float:
    """Simple word-overlap similarity between two location strings."""
    if not loc_a or not loc_b:
        return 0.5  # neutral
    words_a = set(loc_a.lower().split())
    words_b = set(loc_b.lower().split())
    if not words_a or not words_b:
        return 0.5
    overlap = words_a & words_b
    return len(overlap) / max(len(words_a), len(words_b))


async def score_provider(
    provider: ProviderProfile,
    request: ServiceRequest,
    provider_lead: Lead,
) -> dict:
    """Score a single provider against a service request. Returns dict with score + breakdown."""
    breakdown = {}

    # 1. Service alignment (35 points)
    services = provider.services_offered or []
    if _service_matches(request.service_category, services):
        breakdown["service_alignment"] = 35.0
    else:
        breakdown["service_alignment"] = 0.0

    # 2. Budget fit (25 points)
    budget_ratio = _budget_overlap_score(
        request.budget_min, request.budget_max,
        provider.min_project_budget, provider.max_project_budget,
    )
    breakdown["budget_fit"] = round(budget_ratio * 25.0, 1)

    # 3. Location (15 points)
    loc_score = _location_similarity(
        request.location_preference,
        provider_lead.location if provider_lead else None,
    )
    breakdown["location"] = round(loc_score * 15.0, 1)

    # 4. Provider rating (15 points)
    rating = min(provider.average_rating or 0.0, 5.0)
    breakdown["rating"] = round((rating / 5.0) * 15.0, 1)

    # 5. Success history (10 points)
    breakdown["success_history"] = round((provider.success_rate or 0.0) * 10.0, 1)

    total = sum(breakdown.values())
    return {
        "provider_profile_id": provider.id,
        "score": round(total, 1),
        "breakdown": breakdown,
    }


async def find_matches(
    request_id: str,
    session: AsyncSession,
    top_n: int = DEFAULT_TOP_N,
) -> list[dict]:
    """Find and rank best-fit providers for a service request.

    Returns a list of dicts: [{provider_profile_id, score, breakdown}, ...]
    Does NOT create Match records — caller decides what to do.
    """
    # Load the request
    req_result = await session.execute(
        select(ServiceRequest).where(ServiceRequest.id == request_id)
    )
    request = req_result.scalar_one_or_none()
    if not request:
        raise ValueError(f"ServiceRequest {request_id} not found")

    # Get IDs of providers already matched to this request
    existing_result = await session.execute(
        select(Match.provider_profile_id).where(
            Match.service_request_id == request_id
        )
    )
    already_matched = {row[0] for row in existing_result.all()}

    # Fetch active providers that offer the requested service
    providers_result = await session.execute(
        select(ProviderProfile).where(
            and_(
                ProviderProfile.is_active == True,
            )
        )
    )
    all_providers = providers_result.scalars().all()

    # Filter to providers offering a matching service and not already matched
    candidates = [
        p for p in all_providers
        if p.id not in already_matched
        and _service_matches(request.service_category, p.services_offered or [])
    ]

    if not candidates:
        logger.info(f"No eligible providers found for request {request_id}")
        return []

    # Load lead records for location data
    lead_ids = [p.lead_id for p in candidates]
    leads_result = await session.execute(
        select(Lead).where(Lead.id.in_(lead_ids))
    )
    leads_map = {l.id: l for l in leads_result.scalars().all()}

    # Score each candidate
    scored = []
    for provider in candidates:
        provider_lead = leads_map.get(provider.lead_id)
        result = await score_provider(provider, request, provider_lead)
        scored.append(result)

    # Sort by score descending, take top N
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


async def auto_propose_matches(
    request_id: str,
    session: AsyncSession,
    top_n: int = DEFAULT_TOP_N,
) -> list[Match]:
    """Find best matches and create Match records with status=PROPOSED."""
    scored = await find_matches(request_id, session, top_n)

    if not scored:
        return []

    matches = []
    for item in scored:
        match = Match(
            service_request_id=request_id,
            provider_profile_id=item["provider_profile_id"],
            status=MatchStatus.PROPOSED,
            match_score=item["score"],
            match_reason=_format_match_reason(item["breakdown"]),
        )
        session.add(match)
        matches.append(match)

    # Update request status
    req_result = await session.execute(
        select(ServiceRequest).where(ServiceRequest.id == request_id)
    )
    request = req_result.scalar_one_or_none()
    if request:
        request.status = "matching"
        request.updated_at = datetime.utcnow()

    await session.flush()
    return matches


def _format_match_reason(breakdown: dict) -> str:
    """Generate a human-readable match reason from score breakdown."""
    parts = []
    if breakdown.get("service_alignment", 0) >= 30:
        parts.append("Offers the exact service needed")
    if breakdown.get("budget_fit", 0) >= 20:
        parts.append("budget fits well")
    elif breakdown.get("budget_fit", 0) >= 10:
        parts.append("budget partially aligns")
    if breakdown.get("location", 0) >= 12:
        parts.append("location match")
    if breakdown.get("rating", 0) >= 10:
        parts.append("highly rated")
    if breakdown.get("success_history", 0) >= 7:
        parts.append("strong track record")

    if not parts:
        return "Potential match based on available criteria"
    return ". ".join(parts).capitalize() + "."

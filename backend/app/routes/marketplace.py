"""
Marketplace Routes - Provider profiles, service requests, matches, commissions.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import (
    Lead,
    ProviderProfile,
    ServiceRequest,
    Match,
    MatchStatus,
    Commission,
    CommissionStatus,
    LeadActivity,
)
from app.models.schemas import (
    ProviderProfileCreate,
    ProviderProfileUpdate,
    ProviderProfileResponse,
    ServiceRequestCreate,
    ServiceRequestUpdate,
    ServiceRequestResponse,
    MatchResponse,
    MatchComplete,
    CommissionResponse,
    CommissionUpdate,
    MarketplaceStats,
)

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# ---------------------------------------------------------------------------
# Marketplace dashboard stats
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=MarketplaceStats)
async def get_marketplace_stats(db: AsyncSession = Depends(get_db)):
    """Aggregate KPIs for the marketplace."""
    total_providers = (await db.execute(select(func.count(ProviderProfile.id)))).scalar() or 0
    active_providers = (await db.execute(
        select(func.count(ProviderProfile.id)).where(ProviderProfile.is_active == True)
    )).scalar() or 0

    total_requests = (await db.execute(select(func.count(ServiceRequest.id)))).scalar() or 0
    open_requests = (await db.execute(
        select(func.count(ServiceRequest.id)).where(ServiceRequest.status == "open")
    )).scalar() or 0

    total_matches = (await db.execute(select(func.count(Match.id)))).scalar() or 0
    active_matches = (await db.execute(
        select(func.count(Match.id)).where(
            Match.status.in_([MatchStatus.PROPOSED, MatchStatus.APPROVED, MatchStatus.INTRO_SENT, MatchStatus.IN_PROGRESS])
        )
    )).scalar() or 0
    completed_matches = (await db.execute(
        select(func.count(Match.id)).where(Match.status == MatchStatus.COMPLETED)
    )).scalar() or 0

    match_success_rate = round((completed_matches / max(total_matches, 1)) * 100, 1)

    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(Commission.commission_amount), 0.0))
    )).scalar() or 0.0
    pending_revenue = (await db.execute(
        select(func.coalesce(func.sum(Commission.commission_amount), 0.0)).where(
            Commission.status == CommissionStatus.PENDING
        )
    )).scalar() or 0.0
    paid_revenue = (await db.execute(
        select(func.coalesce(func.sum(Commission.commission_amount), 0.0)).where(
            Commission.status == CommissionStatus.PAID
        )
    )).scalar() or 0.0

    return MarketplaceStats(
        total_providers=total_providers,
        active_providers=active_providers,
        total_requests=total_requests,
        open_requests=open_requests,
        total_matches=total_matches,
        active_matches=active_matches,
        completed_matches=completed_matches,
        match_success_rate=match_success_rate,
        total_revenue=round(total_revenue, 2),
        pending_revenue=round(pending_revenue, 2),
        paid_revenue=round(paid_revenue, 2),
    )


# ---------------------------------------------------------------------------
# Provider profiles
# ---------------------------------------------------------------------------


@router.get("/providers")
async def list_providers(
    service: Optional[str] = None,
    active_only: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ProviderProfile)
    if active_only:
        stmt = stmt.where(ProviderProfile.is_active == True)
    stmt = stmt.order_by(ProviderProfile.average_rating.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    providers = result.scalars().all()

    # Enrich with lead data
    lead_ids = [p.lead_id for p in providers]
    if lead_ids:
        leads_result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
        leads_map = {l.id: l for l in leads_result.scalars().all()}
    else:
        leads_map = {}

    items = []
    for p in providers:
        lead = leads_map.get(p.lead_id)
        # Filter by service if requested
        if service and service not in (p.services_offered or []):
            continue
        items.append(_provider_to_dict(p, lead))

    return items


@router.get("/providers/{provider_id}")
async def get_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProviderProfile).where(ProviderProfile.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "Provider not found")
    lead_result = await db.execute(select(Lead).where(Lead.id == provider.lead_id))
    lead = lead_result.scalar_one_or_none()
    return _provider_to_dict(provider, lead)


@router.post("/providers/convert/{lead_id}")
async def convert_lead_to_provider(
    lead_id: str,
    data: ProviderProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    """Convert an existing lead into a provider profile."""
    # Check lead exists
    lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")

    # Check if already converted
    existing = await db.execute(
        select(ProviderProfile).where(ProviderProfile.lead_id == lead_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Lead already has a provider profile")

    profile = ProviderProfile(
        lead_id=lead_id,
        services_offered=data.services_offered,
        description=data.description,
        portfolio_urls=data.portfolio_urls,
        hourly_rate=data.hourly_rate,
        min_project_budget=data.min_project_budget,
        max_project_budget=data.max_project_budget,
    )
    db.add(profile)

    # Update lead type
    lead.lead_type = "provider"
    lead.updated_at = datetime.utcnow()

    # Activity log
    activity = LeadActivity(
        lead_id=lead_id,
        activity_type="provider_converted",
        description="Lead converted to marketplace provider profile",
    )
    db.add(activity)

    await db.commit()
    await db.refresh(profile)
    return _provider_to_dict(profile, lead)


@router.put("/providers/{provider_id}")
async def update_provider(
    provider_id: str,
    data: ProviderProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProviderProfile).where(ProviderProfile.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "Provider not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)
    provider.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(provider)

    lead_result = await db.execute(select(Lead).where(Lead.id == provider.lead_id))
    lead = lead_result.scalar_one_or_none()
    return _provider_to_dict(provider, lead)


@router.delete("/providers/{provider_id}")
async def deactivate_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProviderProfile).where(ProviderProfile.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "Provider not found")
    provider.is_active = False
    provider.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "message": "Provider deactivated"}


def _provider_to_dict(p: ProviderProfile, lead: Lead | None) -> dict:
    return {
        "id": p.id,
        "lead_id": p.lead_id,
        "services_offered": p.services_offered or [],
        "description": p.description,
        "portfolio_urls": p.portfolio_urls or [],
        "hourly_rate": p.hourly_rate,
        "min_project_budget": p.min_project_budget,
        "max_project_budget": p.max_project_budget,
        "average_rating": p.average_rating,
        "total_reviews": p.total_reviews,
        "total_matches": p.total_matches,
        "success_rate": p.success_rate,
        "is_active": p.is_active,
        "verified": p.verified,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "lead_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.company if lead else None,
        "lead_company": lead.company if lead else None,
        "lead_email": lead.email if lead else None,
        "lead_location": lead.location if lead else None,
    }


# ---------------------------------------------------------------------------
# Service requests
# ---------------------------------------------------------------------------


@router.get("/requests")
async def list_requests(
    status: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ServiceRequest)
    if status:
        stmt = stmt.where(ServiceRequest.status == status)
    if category:
        stmt = stmt.where(ServiceRequest.service_category == category)
    stmt = stmt.order_by(ServiceRequest.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    requests = result.scalars().all()

    # Enrich with lead + match count data
    lead_ids = list({r.lead_id for r in requests})
    if lead_ids:
        leads_result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
        leads_map = {l.id: l for l in leads_result.scalars().all()}
    else:
        leads_map = {}

    req_ids = [r.id for r in requests]
    match_counts = {}
    if req_ids:
        mc_result = await db.execute(
            select(Match.service_request_id, func.count(Match.id))
            .where(Match.service_request_id.in_(req_ids))
            .group_by(Match.service_request_id)
        )
        match_counts = dict(mc_result.all())

    items = []
    for r in requests:
        lead = leads_map.get(r.lead_id)
        items.append(_request_to_dict(r, lead, match_counts.get(r.id, 0)))
    return items


@router.get("/requests/{request_id}")
async def get_request(request_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Service request not found")

    lead_result = await db.execute(select(Lead).where(Lead.id == req.lead_id))
    lead = lead_result.scalar_one_or_none()

    mc_result = await db.execute(
        select(func.count(Match.id)).where(Match.service_request_id == request_id)
    )
    match_count = mc_result.scalar() or 0

    data = _request_to_dict(req, lead, match_count)

    # Include matches
    matches_result = await db.execute(
        select(Match).where(Match.service_request_id == request_id).order_by(Match.match_score.desc())
    )
    matches = matches_result.scalars().all()
    data["matches"] = [await _match_to_dict(m, db) for m in matches]

    return data


@router.post("/requests")
async def create_request(
    data: ServiceRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    # Verify seeker lead exists
    lead_result = await db.execute(select(Lead).where(Lead.id == data.lead_id))
    lead = lead_result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")

    req = ServiceRequest(
        lead_id=data.lead_id,
        title=data.title,
        description=data.description,
        service_category=data.service_category,
        budget_min=data.budget_min,
        budget_max=data.budget_max,
        timeline=data.timeline,
        location_preference=data.location_preference,
    )
    db.add(req)

    # Update lead type if not already
    if lead.lead_type not in ("seeker", "both"):
        lead.lead_type = "seeker"
        lead.updated_at = datetime.utcnow()

    activity = LeadActivity(
        lead_id=data.lead_id,
        activity_type="service_request_created",
        description=f"Service request created: {data.title} ({data.service_category})",
    )
    db.add(activity)

    await db.commit()
    await db.refresh(req)
    return _request_to_dict(req, lead, 0)


@router.put("/requests/{request_id}")
async def update_request(
    request_id: str,
    data: ServiceRequestUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Service request not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(req, field, value)
    req.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(req)
    return {"success": True, "id": req.id}


@router.post("/requests/{request_id}/find-matches")
async def find_matches_for_request(
    request_id: str,
    top_n: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the matching engine for a service request."""
    from app.services.matching_engine import auto_propose_matches

    result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Service request not found")

    matches = await auto_propose_matches(request_id, db, top_n)
    await db.commit()

    return {
        "success": True,
        "matches_proposed": len(matches),
        "matches": [
            {"id": m.id, "provider_profile_id": m.provider_profile_id, "score": m.match_score}
            for m in matches
        ],
    }


def _request_to_dict(r: ServiceRequest, lead: Lead | None, match_count: int) -> dict:
    return {
        "id": r.id,
        "lead_id": r.lead_id,
        "title": r.title,
        "description": r.description,
        "service_category": r.service_category,
        "budget_min": r.budget_min,
        "budget_max": r.budget_max,
        "timeline": r.timeline,
        "location_preference": r.location_preference,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        "seeker_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.company if lead else None,
        "seeker_company": lead.company if lead else None,
        "match_count": match_count,
    }


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------


@router.get("/matches")
async def list_matches(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Match)
    if status:
        stmt = stmt.where(Match.status == status)
    stmt = stmt.order_by(Match.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    matches = result.scalars().all()
    return [await _match_to_dict(m, db) for m in matches]


@router.get("/matches/{match_id}")
async def get_match(match_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(404, "Match not found")
    return await _match_to_dict(match, db)


@router.post("/matches/{match_id}/approve")
async def approve_match(match_id: str, db: AsyncSession = Depends(get_db)):
    match = await _get_match_or_404(match_id, db)
    if match.status != MatchStatus.PROPOSED:
        raise HTTPException(400, f"Cannot approve match in '{match.status.value}' status")
    match.status = MatchStatus.APPROVED
    match.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "status": "approved"}


@router.post("/matches/{match_id}/reject")
async def reject_match(match_id: str, db: AsyncSession = Depends(get_db)):
    match = await _get_match_or_404(match_id, db)
    if match.status not in (MatchStatus.PROPOSED, MatchStatus.APPROVED):
        raise HTTPException(400, f"Cannot reject match in '{match.status.value}' status")
    match.status = MatchStatus.REJECTED
    match.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "status": "rejected"}


@router.post("/matches/{match_id}/send-intro")
async def send_introduction(match_id: str, db: AsyncSession = Depends(get_db)):
    match = await _get_match_or_404(match_id, db)
    if match.status != MatchStatus.APPROVED:
        raise HTTPException(400, f"Cannot send intro for match in '{match.status.value}' status")
    match.status = MatchStatus.INTRO_SENT
    match.intro_sent_at = datetime.utcnow()
    match.updated_at = datetime.utcnow()

    # Update request status
    req_result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.id == match.service_request_id)
    )
    req = req_result.scalar_one_or_none()
    if req:
        req.status = "matched"
        req.updated_at = datetime.utcnow()

    await db.commit()
    return {"success": True, "status": "intro_sent"}


@router.post("/matches/{match_id}/complete")
async def complete_match(
    match_id: str,
    data: MatchComplete,
    db: AsyncSession = Depends(get_db),
):
    """Mark a match as completed and create a commission record."""
    match = await _get_match_or_404(match_id, db)
    if match.status not in (MatchStatus.INTRO_SENT, MatchStatus.IN_PROGRESS):
        raise HTTPException(400, f"Cannot complete match in '{match.status.value}' status")

    match.status = MatchStatus.COMPLETED
    match.agreed_amount = data.agreed_amount
    match.completed_at = datetime.utcnow()
    match.updated_at = datetime.utcnow()
    if data.admin_notes:
        match.admin_notes = data.admin_notes

    # Create commission
    commission_amount = round(data.agreed_amount * data.commission_rate / 100, 2)
    commission = Commission(
        match_id=match_id,
        percentage_rate=data.commission_rate,
        base_amount=data.agreed_amount,
        commission_amount=commission_amount,
        status=CommissionStatus.PENDING,
    )
    db.add(commission)

    # Update provider stats
    provider_result = await db.execute(
        select(ProviderProfile).where(ProviderProfile.id == match.provider_profile_id)
    )
    provider = provider_result.scalar_one_or_none()
    if provider:
        provider.total_matches = (provider.total_matches or 0) + 1
        # Recalculate success rate
        total_for_provider = (await db.execute(
            select(func.count(Match.id)).where(
                and_(
                    Match.provider_profile_id == provider.id,
                    Match.status.in_([MatchStatus.COMPLETED, MatchStatus.FAILED]),
                )
            )
        )).scalar() or 0
        completed_for_provider = (await db.execute(
            select(func.count(Match.id)).where(
                and_(
                    Match.provider_profile_id == provider.id,
                    Match.status == MatchStatus.COMPLETED,
                )
            )
        )).scalar() or 0
        provider.success_rate = round(completed_for_provider / max(total_for_provider, 1), 2)

    # Update request status
    req_result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.id == match.service_request_id)
    )
    req = req_result.scalar_one_or_none()
    if req:
        req.status = "completed"
        req.updated_at = datetime.utcnow()

    await db.commit()
    return {
        "success": True,
        "status": "completed",
        "commission": {
            "amount": commission_amount,
            "rate": data.commission_rate,
            "base": data.agreed_amount,
        },
    }


@router.post("/matches/{match_id}/fail")
async def fail_match(match_id: str, db: AsyncSession = Depends(get_db)):
    match = await _get_match_or_404(match_id, db)
    match.status = MatchStatus.FAILED
    match.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "status": "failed"}


async def _get_match_or_404(match_id: str, db: AsyncSession) -> Match:
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(404, "Match not found")
    return match


async def _match_to_dict(m: Match, db: AsyncSession) -> dict:
    """Build match dict with joined provider/seeker names."""
    provider_name = None
    provider_services = None
    seeker_name = None
    request_title = None
    request_category = None

    # Provider info
    prov_result = await db.execute(
        select(ProviderProfile).where(ProviderProfile.id == m.provider_profile_id)
    )
    provider = prov_result.scalar_one_or_none()
    if provider:
        provider_services = provider.services_offered or []
        lead_result = await db.execute(select(Lead).where(Lead.id == provider.lead_id))
        lead = lead_result.scalar_one_or_none()
        if lead:
            provider_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.company

    # Request + seeker info
    req_result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.id == m.service_request_id)
    )
    req = req_result.scalar_one_or_none()
    if req:
        request_title = req.title
        request_category = req.service_category
        seeker_lead_result = await db.execute(select(Lead).where(Lead.id == req.lead_id))
        seeker = seeker_lead_result.scalar_one_or_none()
        if seeker:
            seeker_name = f"{seeker.first_name or ''} {seeker.last_name or ''}".strip() or seeker.company

    return {
        "id": m.id,
        "service_request_id": m.service_request_id,
        "provider_profile_id": m.provider_profile_id,
        "status": m.status.value if hasattr(m.status, "value") else str(m.status),
        "match_score": m.match_score,
        "match_reason": m.match_reason,
        "agreed_amount": m.agreed_amount,
        "admin_notes": m.admin_notes,
        "intro_sent_at": m.intro_sent_at.isoformat() if m.intro_sent_at else None,
        "completed_at": m.completed_at.isoformat() if m.completed_at else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        "provider_name": provider_name,
        "provider_services": provider_services,
        "seeker_name": seeker_name,
        "request_title": request_title,
        "request_category": request_category,
    }


# ---------------------------------------------------------------------------
# Commissions
# ---------------------------------------------------------------------------


@router.get("/commissions")
async def list_commissions(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Commission)
    if status:
        stmt = stmt.where(Commission.status == status)
    stmt = stmt.order_by(Commission.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    commissions = result.scalars().all()
    return [await _commission_to_dict(c, db) for c in commissions]


@router.get("/commissions/stats")
async def commission_stats(db: AsyncSession = Depends(get_db)):
    """Revenue statistics."""
    total = (await db.execute(
        select(func.coalesce(func.sum(Commission.commission_amount), 0.0))
    )).scalar() or 0.0
    pending = (await db.execute(
        select(func.coalesce(func.sum(Commission.commission_amount), 0.0)).where(
            Commission.status == CommissionStatus.PENDING
        )
    )).scalar() or 0.0
    paid = (await db.execute(
        select(func.coalesce(func.sum(Commission.commission_amount), 0.0)).where(
            Commission.status == CommissionStatus.PAID
        )
    )).scalar() or 0.0
    count = (await db.execute(select(func.count(Commission.id)))).scalar() or 0
    avg_deal = (await db.execute(
        select(func.coalesce(func.avg(Commission.base_amount), 0.0))
    )).scalar() or 0.0

    return {
        "total_revenue": round(total, 2),
        "pending_revenue": round(pending, 2),
        "paid_revenue": round(paid, 2),
        "commission_count": count,
        "average_deal_size": round(avg_deal, 2),
    }


@router.put("/commissions/{commission_id}")
async def update_commission(
    commission_id: str,
    data: CommissionUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Commission).where(Commission.id == commission_id)
    )
    commission = result.scalar_one_or_none()
    if not commission:
        raise HTTPException(404, "Commission not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "status" and value:
            commission.status = CommissionStatus(value)
        elif field == "paid_at" and value:
            commission.paid_at = value
        elif field == "notes":
            commission.notes = value
    commission.updated_at = datetime.utcnow()

    await db.commit()
    return {"success": True, "id": commission.id}


async def _commission_to_dict(c: Commission, db: AsyncSession) -> dict:
    provider_name = None
    seeker_name = None
    request_title = None

    # Get match -> request + provider info
    match_result = await db.execute(select(Match).where(Match.id == c.match_id))
    match = match_result.scalar_one_or_none()
    if match:
        prov_result = await db.execute(
            select(ProviderProfile).where(ProviderProfile.id == match.provider_profile_id)
        )
        provider = prov_result.scalar_one_or_none()
        if provider:
            lead_result = await db.execute(select(Lead).where(Lead.id == provider.lead_id))
            lead = lead_result.scalar_one_or_none()
            if lead:
                provider_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.company

        req_result = await db.execute(
            select(ServiceRequest).where(ServiceRequest.id == match.service_request_id)
        )
        req = req_result.scalar_one_or_none()
        if req:
            request_title = req.title
            seeker_result = await db.execute(select(Lead).where(Lead.id == req.lead_id))
            seeker = seeker_result.scalar_one_or_none()
            if seeker:
                seeker_name = f"{seeker.first_name or ''} {seeker.last_name or ''}".strip() or seeker.company

    return {
        "id": c.id,
        "match_id": c.match_id,
        "percentage_rate": c.percentage_rate,
        "base_amount": c.base_amount,
        "commission_amount": c.commission_amount,
        "status": c.status.value if hasattr(c.status, "value") else str(c.status),
        "due_date": c.due_date.isoformat() if c.due_date else None,
        "paid_at": c.paid_at.isoformat() if c.paid_at else None,
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "provider_name": provider_name,
        "seeker_name": seeker_name,
        "request_title": request_title,
    }

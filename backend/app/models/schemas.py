from __future__ import annotations

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── Lead Schemas ──

class LeadCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    source: str = "manual"
    source_url: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    tags: list[str] = []
    campaign_id: Optional[str] = None


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None
    score: Optional[float] = None


class LeadResponse(BaseModel):
    id: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    job_title: Optional[str]
    website: Optional[str]
    linkedin_url: Optional[str]
    twitter_handle: Optional[str]
    score: float
    score_breakdown: Optional[dict]
    status: str
    source: str
    source_url: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    location: Optional[str]
    notes: Optional[str]
    tags: list
    custom_fields: Optional[dict]
    ai_summary: Optional[str]
    ai_next_action: Optional[str]
    lead_type: Optional[str] = "unknown"
    created_at: datetime
    updated_at: datetime
    last_contacted_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Agent Schemas ──

class AgentCreate(BaseModel):
    name: str
    agent_type: str
    config: dict = {}
    is_enabled: bool = True


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    is_enabled: Optional[bool] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    agent_type: str
    status: str
    config: dict
    last_run_at: Optional[datetime]
    last_result: Optional[dict]
    leads_generated: int
    error_message: Optional[str]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentRunRequest(BaseModel):
    agent_id: str
    params: dict = {}


# ── Campaign Schemas ──

class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    campaign_type: str = "email"
    target_criteria: dict = {}
    email_template: Optional[str] = None
    schedule_config: dict = {}


class CampaignResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    campaign_type: str
    target_criteria: dict
    email_template: Optional[str]
    schedule_config: dict
    stats: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Dashboard Schemas ──

class DashboardStats(BaseModel):
    total_leads: int
    new_leads_today: int
    qualified_leads: int
    conversion_rate: float
    active_agents: int
    active_campaigns: int
    leads_by_source: dict
    leads_by_status: dict
    recent_leads: list[LeadResponse]
    agent_stats: list[AgentResponse]


# ── WebSocket Events ──

class WSEvent(BaseModel):
    event: str  # new_lead, agent_update, lead_scored, campaign_update
    data: dict
    timestamp: datetime = None

    def __init__(self, **kwargs):
        if kwargs.get("timestamp") is None:
            kwargs["timestamp"] = datetime.utcnow()
        super().__init__(**kwargs)


# ── Marketplace Schemas ──


class ProviderProfileCreate(BaseModel):
    services_offered: list[str] = []
    description: Optional[str] = None
    portfolio_urls: list[str] = []
    hourly_rate: Optional[float] = None
    min_project_budget: Optional[float] = None
    max_project_budget: Optional[float] = None


class ProviderProfileUpdate(BaseModel):
    services_offered: Optional[list[str]] = None
    description: Optional[str] = None
    portfolio_urls: Optional[list[str]] = None
    hourly_rate: Optional[float] = None
    min_project_budget: Optional[float] = None
    max_project_budget: Optional[float] = None
    is_active: Optional[bool] = None
    verified: Optional[bool] = None


class ProviderProfileResponse(BaseModel):
    id: str
    lead_id: str
    services_offered: list
    description: Optional[str]
    portfolio_urls: list
    hourly_rate: Optional[float]
    min_project_budget: Optional[float]
    max_project_budget: Optional[float]
    average_rating: float
    total_reviews: int
    total_matches: int
    success_rate: float
    is_active: bool
    verified: bool
    created_at: datetime
    updated_at: datetime
    # Joined lead fields
    lead_name: Optional[str] = None
    lead_company: Optional[str] = None
    lead_email: Optional[str] = None
    lead_location: Optional[str] = None

    class Config:
        from_attributes = True


class ServiceRequestCreate(BaseModel):
    lead_id: str
    title: str
    description: Optional[str] = None
    service_category: str
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    timeline: Optional[str] = None
    location_preference: Optional[str] = None


class ServiceRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    timeline: Optional[str] = None
    location_preference: Optional[str] = None
    status: Optional[str] = None


class ServiceRequestResponse(BaseModel):
    id: str
    lead_id: str
    title: str
    description: Optional[str]
    service_category: str
    budget_min: Optional[float]
    budget_max: Optional[float]
    timeline: Optional[str]
    location_preference: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    # Joined fields
    seeker_name: Optional[str] = None
    seeker_company: Optional[str] = None
    match_count: int = 0

    class Config:
        from_attributes = True


class MatchResponse(BaseModel):
    id: str
    service_request_id: str
    provider_profile_id: str
    status: str
    match_score: float
    match_reason: Optional[str]
    agreed_amount: Optional[float]
    admin_notes: Optional[str]
    intro_sent_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    # Joined fields
    provider_name: Optional[str] = None
    provider_services: Optional[list] = None
    seeker_name: Optional[str] = None
    request_title: Optional[str] = None
    request_category: Optional[str] = None

    class Config:
        from_attributes = True


class MatchComplete(BaseModel):
    agreed_amount: float
    commission_rate: float = 10.0
    admin_notes: Optional[str] = None


class CommissionResponse(BaseModel):
    id: str
    match_id: str
    percentage_rate: float
    base_amount: float
    commission_amount: float
    status: str
    due_date: Optional[datetime]
    paid_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    # Joined fields
    provider_name: Optional[str] = None
    seeker_name: Optional[str] = None
    request_title: Optional[str] = None

    class Config:
        from_attributes = True


class CommissionUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    paid_at: Optional[datetime] = None


class MarketplaceStats(BaseModel):
    total_providers: int
    active_providers: int
    total_requests: int
    open_requests: int
    total_matches: int
    active_matches: int
    completed_matches: int
    match_success_rate: float
    total_revenue: float
    pending_revenue: float
    paid_revenue: float

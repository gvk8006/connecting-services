import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Float, Text, DateTime, Boolean, Integer, Enum, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class LeadStatus(str, PyEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class LeadSource(str, PyEnum):
    WEB_SCRAPE = "web_scrape"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    GOOGLE_SEARCH = "google_search"
    FORM_CAPTURE = "form_capture"
    EMAIL_CAMPAIGN = "email_campaign"
    API_INTEGRATION = "api_integration"
    REFERRAL = "referral"
    MANUAL = "manual"


class AgentType(str, PyEnum):
    SCRAPER = "scraper"
    QUALIFIER = "qualifier"
    EMAIL_OUTREACH = "email_outreach"
    SOCIAL_MONITOR = "social_monitor"
    FORM_PROCESSOR = "form_processor"
    PROSPECTOR = "prospector"
    OUTREACH_CONNECTOR = "outreach_connector"


class AgentStatus(str, PyEnum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    PAUSED = "paused"


class CampaignStatus(str, PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class MatchStatus(str, PyEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    INTRO_SENT = "intro_sent"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class CommissionStatus(str, PyEnum):
    PENDING = "pending"
    INVOICED = "invoiced"
    PAID = "paid"
    WAIVED = "waived"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=generate_uuid)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(200), nullable=True)
    job_title = Column(String(200), nullable=True)
    website = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    twitter_handle = Column(String(100), nullable=True)

    # Lead scoring
    score = Column(Float, default=0.0)
    score_breakdown = Column(JSON, nullable=True)

    # Status & source
    status = Column(Enum(LeadStatus), default=LeadStatus.NEW, index=True)
    source = Column(Enum(LeadSource), default=LeadSource.MANUAL)
    source_url = Column(String(500), nullable=True)

    # Additional data
    industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    location = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    custom_fields = Column(JSON, default=dict)

    # AI-generated insights
    ai_summary = Column(Text, nullable=True)
    ai_next_action = Column(Text, nullable=True)

    # Marketplace classification
    lead_type = Column(String(20), default="unknown")  # "seeker", "provider", "both", "unknown"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_contacted_at = Column(DateTime, nullable=True)

    # Relationships
    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True)


class LeadActivity(Base):
    __tablename__ = "lead_activities"

    id = Column(String, primary_key=True, default=generate_uuid)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False)  # email_sent, call, note, status_change
    description = Column(Text, nullable=True)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="activities")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    agent_type = Column(Enum(AgentType), nullable=False)
    status = Column(Enum(AgentStatus), default=AgentStatus.IDLE)
    config = Column(JSON, default=dict)
    last_run_at = Column(DateTime, nullable=True)
    last_result = Column(JSON, nullable=True)
    leads_generated = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT)
    campaign_type = Column(String(50), nullable=False)  # email, social, multi_channel
    target_criteria = Column(JSON, default=dict)
    email_template = Column(Text, nullable=True)
    schedule_config = Column(JSON, default=dict)
    stats = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_type = Column(String(50), nullable=False, index=True)
    event_data = Column(JSON, default=dict)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# ---------------------------------------------------------------------------
# Marketplace models
# ---------------------------------------------------------------------------


class ProviderProfile(Base):
    __tablename__ = "provider_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    lead_id = Column(String, ForeignKey("leads.id"), unique=True, nullable=False)

    # Service capabilities
    services_offered = Column(JSON, default=list)   # ["website", "chatbot", "crm"]
    description = Column(Text, nullable=True)
    portfolio_urls = Column(JSON, default=list)
    hourly_rate = Column(Float, nullable=True)
    min_project_budget = Column(Float, nullable=True)
    max_project_budget = Column(Float, nullable=True)

    # Ratings (denormalized)
    average_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    total_matches = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    # Status
    is_active = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", backref="provider_profile")
    matches = relationship("Match", back_populates="provider")


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id = Column(String, primary_key=True, default=generate_uuid)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    service_category = Column(String(50), nullable=False)
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    timeline = Column(String(50), nullable=True)
    location_preference = Column(String(200), nullable=True)

    status = Column(String(20), default="open")  # open, matching, matched, completed, cancelled

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", backref="service_requests")
    matches = relationship("Match", back_populates="service_request")


class Match(Base):
    __tablename__ = "matches"

    id = Column(String, primary_key=True, default=generate_uuid)
    service_request_id = Column(String, ForeignKey("service_requests.id"), nullable=False)
    provider_profile_id = Column(String, ForeignKey("provider_profiles.id"), nullable=False)

    status = Column(Enum(MatchStatus), default=MatchStatus.PROPOSED)
    match_score = Column(Float, default=0.0)
    match_reason = Column(Text, nullable=True)

    agreed_amount = Column(Float, nullable=True)
    admin_notes = Column(Text, nullable=True)

    intro_sent_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    service_request = relationship("ServiceRequest", back_populates="matches")
    provider = relationship("ProviderProfile", back_populates="matches")
    commission = relationship("Commission", back_populates="match", uselist=False)


class Commission(Base):
    __tablename__ = "commissions"

    id = Column(String, primary_key=True, default=generate_uuid)
    match_id = Column(String, ForeignKey("matches.id"), unique=True, nullable=False)

    percentage_rate = Column(Float, default=10.0)
    base_amount = Column(Float, nullable=False)
    commission_amount = Column(Float, nullable=False)
    status = Column(Enum(CommissionStatus), default=CommissionStatus.PENDING)

    due_date = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    match = relationship("Match", back_populates="commission")

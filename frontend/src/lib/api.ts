const API_BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  // Dashboard
  getDashboardStats: () => request<DashboardStats>("/dashboard/stats"),

  // Leads
  getLeads: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<Lead[]>(`/leads${qs}`);
  },
  getLead: (id: string) => request<Lead>(`/leads/${id}`),
  getLeadActivities: (id: string) => request<LeadActivity[]>(`/leads/${id}/activities`),
  getLeadStats: () => request<LeadStats>("/leads/stats"),
  getLeadCount: () => request<{ total: number; today: number; qualified: number }>("/leads/count"),
  createLead: (data: Partial<Lead>) => request<Lead>("/leads", { method: "POST", body: JSON.stringify(data) }),
  updateLead: (id: string, data: Partial<Lead>) =>
    request<Lead>(`/leads/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteLead: (id: string) => request(`/leads/${id}`, { method: "DELETE" }),

  // Agents
  getAgents: () => request<Agent[]>("/agents"),
  getAgentStatuses: () => request<AgentStatusInfo[]>("/agents/status"),
  runAgent: (id: string, params?: Record<string, unknown>) =>
    request(`/agents/${id}/run`, { method: "POST", body: JSON.stringify(params || {}) }),
  runAllAgents: () => request("/agents/run-all", { method: "POST" }),
  toggleAgent: (id: string) => request(`/agents/${id}/toggle`, { method: "POST" }),

  // Campaigns
  getCampaigns: () => request<Campaign[]>("/campaigns"),
  createCampaign: (data: Partial<Campaign>) =>
    request<Campaign>("/campaigns", { method: "POST", body: JSON.stringify(data) }),
  activateCampaign: (id: string) => request(`/campaigns/${id}/activate`, { method: "POST" }),
  pauseCampaign: (id: string) => request(`/campaigns/${id}/pause`, { method: "POST" }),

  // Form Capture
  captureFormLead: (data: Record<string, string>) =>
    request("/capture/form", { method: "POST", body: JSON.stringify(data) }),

  // Marketplace
  getMarketplaceStats: () => request<MarketplaceStats>("/marketplace/stats"),

  // Providers
  getProviders: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<ProviderProfile[]>(`/marketplace/providers${qs}`);
  },
  getProvider: (id: string) => request<ProviderProfile>(`/marketplace/providers/${id}`),
  convertLeadToProvider: (leadId: string, data: Partial<ProviderProfile>) =>
    request<ProviderProfile>(`/marketplace/providers/convert/${leadId}`, {
      method: "POST", body: JSON.stringify(data),
    }),
  updateProvider: (id: string, data: Partial<ProviderProfile>) =>
    request<ProviderProfile>(`/marketplace/providers/${id}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  deactivateProvider: (id: string) =>
    request(`/marketplace/providers/${id}`, { method: "DELETE" }),

  // Service Requests
  getServiceRequests: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<ServiceRequestItem[]>(`/marketplace/requests${qs}`);
  },
  getServiceRequest: (id: string) => request<ServiceRequestItem>(`/marketplace/requests/${id}`),
  createServiceRequest: (data: Partial<ServiceRequestItem>) =>
    request<ServiceRequestItem>("/marketplace/requests", {
      method: "POST", body: JSON.stringify(data),
    }),
  updateServiceRequest: (id: string, data: Partial<ServiceRequestItem>) =>
    request(`/marketplace/requests/${id}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  findMatches: (requestId: string, topN?: number) =>
    request<{ success: boolean; matches_proposed: number; matches: { id: string; provider_profile_id: string; score: number }[] }>(
      `/marketplace/requests/${requestId}/find-matches${topN ? `?top_n=${topN}` : ""}`,
      { method: "POST" },
    ),

  // Matches
  getMatches: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<MatchItem[]>(`/marketplace/matches${qs}`);
  },
  getMatch: (id: string) => request<MatchItem>(`/marketplace/matches/${id}`),
  approveMatch: (id: string) =>
    request(`/marketplace/matches/${id}/approve`, { method: "POST" }),
  rejectMatch: (id: string) =>
    request(`/marketplace/matches/${id}/reject`, { method: "POST" }),
  sendIntro: (id: string) =>
    request(`/marketplace/matches/${id}/send-intro`, { method: "POST" }),
  completeMatch: (id: string, data: { agreed_amount: number; commission_rate?: number; admin_notes?: string }) =>
    request(`/marketplace/matches/${id}/complete`, {
      method: "POST", body: JSON.stringify(data),
    }),
  failMatch: (id: string) =>
    request(`/marketplace/matches/${id}/fail`, { method: "POST" }),

  // Commissions
  getCommissions: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<CommissionItem[]>(`/marketplace/commissions${qs}`);
  },
  getCommissionStats: () => request<CommissionStats>("/marketplace/commissions/stats"),
  updateCommission: (id: string, data: { status?: string; notes?: string }) =>
    request(`/marketplace/commissions/${id}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
};

// Types
export interface Lead {
  id: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  company: string | null;
  job_title: string | null;
  website: string | null;
  linkedin_url: string | null;
  twitter_handle: string | null;
  score: number;
  score_breakdown: Record<string, number> | null;
  status: string;
  source: string;
  source_url: string | null;
  industry: string | null;
  company_size: string | null;
  location: string | null;
  notes: string | null;
  tags: string[];
  custom_fields: Record<string, string> | null;
  ai_summary: string | null;
  ai_next_action: string | null;
  lead_type: string;
  created_at: string;
  updated_at: string;
  last_contacted_at: string | null;
}

export interface LeadActivity {
  id: string;
  activity_type: string;
  description: string;
  extra_data: Record<string, unknown> | null;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  agent_type: string;
  status: string;
  config: Record<string, unknown>;
  last_run_at: string | null;
  last_result: Record<string, unknown> | null;
  leads_generated: number;
  error_message: string | null;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentStatusInfo {
  id: string;
  name: string;
  type: string;
  status: string;
  is_enabled: boolean;
  leads_generated: number;
  last_run_at: string | null;
  error_message: string | null;
}

export interface Campaign {
  id: string;
  name: string;
  description: string | null;
  status: string;
  campaign_type: string;
  target_criteria: Record<string, unknown>;
  email_template: string | null;
  schedule_config: Record<string, unknown>;
  stats: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_leads: number;
  new_today: number;
  new_this_week: number;
  qualified_leads: number;
  conversion_rate: number;
  active_agents: number;
  active_campaigns: number;
  average_score: number;
  leads_by_source: Record<string, number>;
  leads_by_status: Record<string, number>;
  daily_trend: { date: string; count: number }[];
  recent_leads: RecentLead[];
  agent_total_leads: number;
}

export interface RecentLead {
  id: string;
  name: string;
  email: string | null;
  company: string | null;
  score: number;
  status: string;
  source: string;
  created_at: string;
}

export interface LeadStats {
  by_status: Record<string, number>;
  by_source: Record<string, number>;
  daily_leads: { date: string; count: number }[];
  average_score: number;
  conversion_rate: number;
  total: number;
}

// Marketplace Types

export interface ProviderProfile {
  id: string;
  lead_id: string;
  services_offered: string[];
  description: string | null;
  portfolio_urls: string[];
  hourly_rate: number | null;
  min_project_budget: number | null;
  max_project_budget: number | null;
  average_rating: number;
  total_reviews: number;
  total_matches: number;
  success_rate: number;
  is_active: boolean;
  verified: boolean;
  created_at: string;
  updated_at: string;
  lead_name: string | null;
  lead_company: string | null;
  lead_email: string | null;
  lead_location: string | null;
}

export interface ServiceRequestItem {
  id: string;
  lead_id: string;
  title: string;
  description: string | null;
  service_category: string;
  budget_min: number | null;
  budget_max: number | null;
  timeline: string | null;
  location_preference: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  seeker_name: string | null;
  seeker_company: string | null;
  match_count: number;
  matches?: MatchItem[];
}

export interface MatchItem {
  id: string;
  service_request_id: string;
  provider_profile_id: string;
  status: string;
  match_score: number;
  match_reason: string | null;
  agreed_amount: number | null;
  admin_notes: string | null;
  intro_sent_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  provider_name: string | null;
  provider_services: string[] | null;
  seeker_name: string | null;
  request_title: string | null;
  request_category: string | null;
}

export interface CommissionItem {
  id: string;
  match_id: string;
  percentage_rate: number;
  base_amount: number;
  commission_amount: number;
  status: string;
  due_date: string | null;
  paid_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  provider_name: string | null;
  seeker_name: string | null;
  request_title: string | null;
}

export interface CommissionStats {
  total_revenue: number;
  pending_revenue: number;
  paid_revenue: number;
  commission_count: number;
  average_deal_size: number;
}

export interface MarketplaceStats {
  total_providers: number;
  active_providers: number;
  total_requests: number;
  open_requests: number;
  total_matches: number;
  active_matches: number;
  completed_matches: number;
  match_success_rate: number;
  total_revenue: number;
  pending_revenue: number;
  paid_revenue: number;
}
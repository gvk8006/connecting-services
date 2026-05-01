import { useEffect, useState, useMemo, useCallback } from "react"
import { useSearchParams } from "react-router-dom"
import {
  Search, Filter, UserPlus, ExternalLink, Mail, Phone, Globe, Code, Cpu,
  MessageSquare, Layout, Database, ShieldCheck, X, Clock, Send, Star,
  FileText, ChevronRight, ArrowUpRight, Users, UserCheck, BarChart3,
  Sparkles, Activity, Download,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScoreBar } from "@/components/ui/score-bar"
import { cn } from "@/lib/utils"
import type { Lead, LeadActivity } from "@/lib/api"

const SERVICE_LABELS: Record<string, { label: string; icon: typeof Globe; color: string }> = {
  website: { label: "Website", icon: Globe, color: "bg-primary/15 text-primary border-primary/25" },
  saas: { label: "SaaS Tool", icon: Code, color: "bg-[hsl(280_70%_55%/0.15)] text-[hsl(280_70%_55%)] border-[hsl(280_70%_55%/0.25)]" },
  ai_agents: { label: "AI Agents", icon: Cpu, color: "bg-success/15 text-success border-success/25" },
  chatbot: { label: "Chatbot", icon: MessageSquare, color: "bg-warning/15 text-warning border-warning/25" },
  web_app: { label: "Web App", icon: Layout, color: "bg-[hsl(200_90%_50%/0.15)] text-[hsl(200_90%_50%)] border-[hsl(200_90%_50%/0.25)]" },
  crm: { label: "CRM", icon: Database, color: "bg-[hsl(210_80%_55%/0.15)] text-[hsl(210_80%_55%)] border-[hsl(210_80%_55%/0.25)]" },
  qc_ai: { label: "QC AI Tool", icon: ShieldCheck, color: "bg-[hsl(160_70%_45%/0.15)] text-[hsl(160_70%_45%)] border-[hsl(160_70%_45%/0.25)]" },
}

const statusOptions = ["all", "new", "contacted", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"]

const statusBadgeVariant: Record<string, "default" | "success" | "warning" | "destructive" | "outline"> = {
  new: "default",
  contacted: "warning",
  qualified: "success",
  proposal: "default",
  negotiation: "warning",
  closed_won: "success",
  closed_lost: "destructive",
}

const SCORE_BREAKDOWN_LABELS: Record<string, string> = {
  contact_completeness: "Contact Info",
  company_info: "Company Data",
  title_relevance: "Title Match",
  location_data: "Location",
  source_quality: "Source Quality",
  service_intent: "Service Intent",
  url_quality: "URL Quality",
}

const ACTIVITY_ICONS: Record<string, typeof Send> = {
  prospected: Search,
  outreach_sent: Send,
  lead_scored: Star,
  email_sent: Mail,
  form_submitted: FileText,
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d ago`
  return `${Math.floor(days / 30)}mo ago`
}

function getLeadDisplayName(lead: Lead): string {
  if (lead.first_name && lead.first_name !== "Unknown") {
    return [lead.first_name, lead.last_name].filter(Boolean).join(" ")
  }
  if (lead.company) return lead.company
  if (lead.email) return lead.email.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, c => c.toUpperCase())
  return "Unknown Lead"
}

function getLeadInitials(lead: Lead): string {
  const name = getLeadDisplayName(lead)
  return name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase()
}

function getServiceFromTags(lead: Lead): string | null {
  return lead.custom_fields?.service_needed || lead.tags?.find(t => t in SERVICE_LABELS) || null
}

export function LeadsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [leads, setLeads] = useState<Lead[]>([])
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [serviceFilter, setServiceFilter] = useState("all")
  const [sortBy, setSortBy] = useState<"score" | "created_at">("created_at")
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [activities, setActivities] = useState<LeadActivity[]>([])
  const [loadingActivities, setLoadingActivities] = useState(false)
  const [loading, setLoading] = useState(true)
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    fetch("/api/leads?limit=200")
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((data) => {
        setLeads(data)
        // Check if URL has a lead ID to pre-select
        const leadId = searchParams.get("id")
        if (leadId) {
          const found = data.find((l: Lead) => l.id === leadId)
          if (found) {
            setSelectedLead(found)
            setDrawerOpen(true)
          }
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const openLeadDrawer = useCallback((lead: Lead) => {
    setSelectedLead(lead)
    setDrawerOpen(true)
    setLoadingActivities(true)
    setActivities([])
    fetch(`/api/leads/${lead.id}/activities`)
      .then((r) => r.ok ? r.json() : [])
      .then(setActivities)
      .catch(() => {})
      .finally(() => setLoadingActivities(false))
  }, [])

  const closeDrawer = useCallback(() => {
    setDrawerOpen(false)
    setTimeout(() => setSelectedLead(null), 300)
    setSearchParams({})
  }, [setSearchParams])

  const filtered = useMemo(() => {
    let result = [...leads]
    if (search) {
      const q = search.toLowerCase()
      result = result.filter(
        (l) =>
          (l.first_name?.toLowerCase().includes(q)) ||
          (l.last_name?.toLowerCase().includes(q)) ||
          (l.email?.toLowerCase().includes(q)) ||
          (l.company?.toLowerCase().includes(q)) ||
          (l.notes?.toLowerCase().includes(q))
      )
    }
    if (statusFilter !== "all") result = result.filter((l) => l.status === statusFilter)
    if (serviceFilter !== "all") result = result.filter((l) => l.tags?.includes(serviceFilter))
    result.sort((a, b) => sortBy === "score" ? b.score - a.score : new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    return result
  }, [leads, search, statusFilter, serviceFilter, sortBy])

  // Stats
  const totalLeads = leads.length
  const qualifiedLeads = leads.filter(l => l.status === "qualified").length
  const contactedLeads = leads.filter(l => l.status === "contacted").length
  const avgScore = leads.length > 0 ? Math.round((leads.reduce((s, l) => s + l.score, 0) / leads.length) * 100) : 0

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Leads</h1>
          <p className="text-sm text-muted-foreground mt-1">{totalLeads} total leads &middot; {filtered.length} shown</p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => {
            const a = document.createElement("a")
            a.href = "/api/leads/export/excel"
            a.download = "leads_report.xlsx"
            a.click()
          }}>
            <Download className="w-4 h-4 mr-2" />Export Excel
          </Button>
          <Button size="sm">
            <UserPlus className="w-4 h-4 mr-2" />Add Lead
          </Button>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Leads", value: totalLeads, icon: Users, color: "text-primary" },
          { label: "Qualified", value: qualifiedLeads, icon: UserCheck, color: "text-success" },
          { label: "Contacted", value: contactedLeads, icon: Send, color: "text-warning" },
          { label: "Avg Score", value: `${avgScore}%`, icon: BarChart3, color: "text-primary" },
        ].map((stat) => (
          <Card key={stat.label} className="hover:shadow-card-hover transition-shadow">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">{stat.label}</span>
                <stat.icon className={cn("w-4 h-4", stat.color)} />
              </div>
              <div className="text-2xl font-bold text-foreground">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Service Filter Pills */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setServiceFilter("all")}
          className={cn(
            "px-3 py-1.5 rounded-full text-xs font-medium border transition-all",
            serviceFilter === "all"
              ? "gradient-primary text-primary-foreground border-transparent shadow-glow-primary"
              : "bg-card text-muted-foreground border-border hover:text-foreground hover:border-primary/30"
          )}
        >
          All Services
        </button>
        {Object.entries(SERVICE_LABELS).map(([key, svc]) => {
          const Icon = svc.icon
          const count = leads.filter(l => l.tags?.includes(key)).length
          return (
            <button
              key={key}
              onClick={() => setServiceFilter(serviceFilter === key ? "all" : key)}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all",
                serviceFilter === key
                  ? svc.color + " border-current/25"
                  : "bg-card text-muted-foreground border-border hover:text-foreground hover:border-primary/30"
              )}
            >
              <Icon className="w-3 h-3" />
              {svc.label}
              {count > 0 && <span className="ml-0.5 opacity-60">{count}</span>}
            </button>
          )
        })}
      </div>

      {/* Filters Row */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search leads by name, email, company..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-9 pl-9 pr-4 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 px-3 rounded-lg border border-border bg-card text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {statusOptions.map((s) => (
              <option key={s} value={s}>{s === "all" ? "All Statuses" : s.replace("_", " ")}</option>
            ))}
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as "score" | "created_at")}
            className="h-9 px-3 rounded-lg border border-border bg-card text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="created_at">Newest first</option>
            <option value="score">Highest score</option>
          </select>
        </div>
      </div>

      {/* Lead Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">Loading leads...</div>
          ) : filtered.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left text-xs font-medium text-muted-foreground px-4 py-3">Lead</th>
                    <th className="text-left text-xs font-medium text-muted-foreground px-4 py-3">Service</th>
                    <th className="text-left text-xs font-medium text-muted-foreground px-4 py-3 w-32">Score</th>
                    <th className="text-left text-xs font-medium text-muted-foreground px-4 py-3">Status</th>
                    <th className="text-left text-xs font-medium text-muted-foreground px-4 py-3">Contact</th>
                    <th className="text-left text-xs font-medium text-muted-foreground px-4 py-3">Added</th>
                    <th className="text-left text-xs font-medium text-muted-foreground px-2 py-3 w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((lead, i) => {
                    const service = getServiceFromTags(lead)
                    const svcMeta = service ? SERVICE_LABELS[service] : null
                    const SvcIcon = svcMeta?.icon || Globe
                    const displayName = getLeadDisplayName(lead)
                    const initials = getLeadInitials(lead)
                    return (
                      <tr
                        key={lead.id}
                        className={cn(
                          "border-b border-border/50 hover:bg-accent/40 cursor-pointer transition-all duration-150 group",
                          selectedLead?.id === lead.id && drawerOpen && "bg-primary/5 border-l-2 border-l-primary"
                        )}
                        onClick={() => openLeadDrawer(lead)}
                        style={{ animationDelay: `${Math.min(i, 20) * 20}ms` }}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-full gradient-primary flex items-center justify-center text-xs font-bold text-primary-foreground shrink-0">
                              {initials}
                            </div>
                            <div className="min-w-0">
                              <div className="text-sm font-medium text-foreground truncate max-w-[180px]">{displayName}</div>
                              <div className="text-xs text-muted-foreground truncate max-w-[180px]">{lead.company || lead.email || ""}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {svcMeta ? (
                            <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium", svcMeta.color)}>
                              <SvcIcon className="w-3 h-3" />
                              {svcMeta.label}
                            </span>
                          ) : (
                            <span className="text-xs text-muted-foreground capitalize">{lead.source.replace("_", " ")}</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <ScoreBar score={lead.score} />
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={statusBadgeVariant[lead.status] || "outline"}>
                            {lead.status.replace("_", " ")}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            {lead.email && <Mail className="w-3.5 h-3.5 text-muted-foreground" aria-label={lead.email} />}
                            {lead.phone && <Phone className="w-3.5 h-3.5 text-muted-foreground" aria-label={lead.phone} />}
                            {lead.website && <Globe className="w-3.5 h-3.5 text-muted-foreground" aria-label={lead.website} />}
                            {!lead.email && !lead.phone && !lead.website && (
                              <span className="text-xs text-muted-foreground/50">--</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs text-muted-foreground">{timeAgo(lead.created_at)}</span>
                        </td>
                        <td className="px-2 py-3">
                          <ChevronRight className="w-4 h-4 text-muted-foreground/40 group-hover:text-primary transition-colors" />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <Users className="w-10 h-10 mb-3 opacity-20" />
              <p className="text-sm">{leads.length === 0 ? "No leads yet" : "No leads match your filters"}</p>
              {leads.length === 0 && <p className="text-xs mt-1">Run the Prospector agent to start finding leads</p>}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Slide-over Drawer */}
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-black/40 z-40 transition-opacity duration-300",
          drawerOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={closeDrawer}
      />
      {/* Drawer Panel */}
      <div
        className={cn(
          "fixed right-0 top-0 h-full w-full max-w-lg bg-card border-l border-border z-50 shadow-elevated overflow-y-auto transition-transform duration-300 ease-out",
          drawerOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        {selectedLead && (
          <div className="flex flex-col h-full">
            {/* Drawer Header */}
            <div className="flex items-center justify-between p-5 border-b border-border sticky top-0 bg-card z-10">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-11 h-11 rounded-full gradient-primary flex items-center justify-center text-sm font-bold text-primary-foreground shrink-0">
                  {getLeadInitials(selectedLead)}
                </div>
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-foreground truncate">{getLeadDisplayName(selectedLead)}</h2>
                  <p className="text-sm text-muted-foreground truncate">
                    {selectedLead.job_title ? `${selectedLead.job_title} at ` : ""}{selectedLead.company || ""}
                  </p>
                </div>
              </div>
              <Button variant="ghost" size="icon" className="shrink-0" onClick={closeDrawer}>
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* Drawer Body */}
            <div className="flex-1 p-5 space-y-6 overflow-y-auto">
              {/* Score + Status Row */}
              <div className="flex items-center gap-3">
                <Badge variant={statusBadgeVariant[selectedLead.status] || "outline"} className="text-xs">
                  {selectedLead.status.replace("_", " ")}
                </Badge>
                {(() => {
                  const service = getServiceFromTags(selectedLead)
                  const svcMeta = service ? SERVICE_LABELS[service] : null
                  if (!svcMeta) return null
                  const SvcIcon = svcMeta.icon
                  return (
                    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium", svcMeta.color)}>
                      <SvcIcon className="w-3 h-3" />
                      {svcMeta.label}
                    </span>
                  )
                })()}
                {selectedLead.last_contacted_at && (
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Clock className="w-3 h-3" />Contacted {timeAgo(selectedLead.last_contacted_at)}
                  </span>
                )}
              </div>

              {/* Lead Score */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Lead Score</span>
                  <span className="text-lg font-bold text-foreground">{Math.round(selectedLead.score * 100)}%</span>
                </div>
                <ScoreBar score={selectedLead.score} showLabel={false} className="h-2" />

                {/* Score Breakdown */}
                {selectedLead.score_breakdown && Object.keys(selectedLead.score_breakdown).length > 0 && (
                  <div className="grid grid-cols-2 gap-x-4 gap-y-2 mt-2">
                    {Object.entries(selectedLead.score_breakdown).map(([key, value]) => (
                      <div key={key} className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-muted-foreground">{SCORE_BREAKDOWN_LABELS[key] || key}</span>
                          <span className="text-[10px] font-mono text-foreground">{Math.round(value * 100)}%</span>
                        </div>
                        <div className="h-1 rounded-full bg-secondary overflow-hidden">
                          <div
                            className={cn(
                              "h-full rounded-full transition-all duration-500",
                              value >= 0.7 ? "bg-success" : value >= 0.4 ? "bg-warning" : "bg-destructive/60"
                            )}
                            style={{ width: `${value * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Contact Info */}
              <div className="space-y-2">
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Contact</div>
                <div className="space-y-2">
                  {selectedLead.email && (
                    <a href={`mailto:${selectedLead.email}`} className="flex items-center gap-2 text-sm text-foreground hover:text-primary transition-colors group/link">
                      <Mail className="w-4 h-4 text-muted-foreground group-hover/link:text-primary" />
                      <span className="truncate">{selectedLead.email}</span>
                      <ArrowUpRight className="w-3 h-3 opacity-0 group-hover/link:opacity-100 transition-opacity" />
                    </a>
                  )}
                  {selectedLead.phone && (
                    <a href={`tel:${selectedLead.phone}`} className="flex items-center gap-2 text-sm text-foreground hover:text-primary transition-colors group/link">
                      <Phone className="w-4 h-4 text-muted-foreground group-hover/link:text-primary" />
                      <span>{selectedLead.phone}</span>
                    </a>
                  )}
                  {selectedLead.website && (
                    <a href={selectedLead.website.startsWith("http") ? selectedLead.website : `https://${selectedLead.website}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-primary hover:underline group/link">
                      <Globe className="w-4 h-4" />
                      <span className="truncate">{selectedLead.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}</span>
                      <ExternalLink className="w-3 h-3 opacity-50" />
                    </a>
                  )}
                  {selectedLead.source_url && selectedLead.source_url !== selectedLead.website && (
                    <a href={selectedLead.source_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors group/link">
                      <ExternalLink className="w-4 h-4" />
                      <span className="truncate text-xs">Source: {selectedLead.source_url.replace(/^https?:\/\//, "").slice(0, 50)}</span>
                    </a>
                  )}
                  {!selectedLead.email && !selectedLead.phone && !selectedLead.website && (
                    <p className="text-sm text-muted-foreground/60 italic">No contact info available</p>
                  )}
                </div>
              </div>

              {/* Details Grid */}
              <div className="space-y-2">
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Details</div>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: "Company", value: selectedLead.company },
                    { label: "Industry", value: selectedLead.industry },
                    { label: "Location", value: selectedLead.location },
                    { label: "Source", value: selectedLead.source?.replace("_", " ") },
                    { label: "Company Size", value: selectedLead.company_size },
                    { label: "Created", value: new Date(selectedLead.created_at).toLocaleDateString() },
                  ].map(({ label, value }) => (
                    <div key={label} className="p-2.5 rounded-lg bg-surface border border-border/50">
                      <div className="text-[10px] text-muted-foreground mb-0.5">{label}</div>
                      <div className="text-sm text-foreground capitalize truncate">{value || "N/A"}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* AI Insights */}
              {(selectedLead.ai_summary || selectedLead.ai_next_action) && (
                <div className="space-y-2 p-4 rounded-lg border border-primary/20 bg-primary/5">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-primary uppercase tracking-wider">
                    <Sparkles className="w-3.5 h-3.5" /> AI Insights
                  </div>
                  {selectedLead.ai_summary && <p className="text-sm text-foreground leading-relaxed">{selectedLead.ai_summary}</p>}
                  {selectedLead.ai_next_action && (
                    <p className="text-sm text-muted-foreground"><strong className="text-foreground">Next Action:</strong> {selectedLead.ai_next_action}</p>
                  )}
                </div>
              )}

              {/* Notes / Context */}
              {selectedLead.notes && (
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Prospect Context</div>
                  <div className="p-3 rounded-lg bg-surface border border-border/50 text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap max-h-32 overflow-y-auto scrollbar-thin">
                    {selectedLead.notes}
                  </div>
                </div>
              )}

              {/* Tags */}
              {selectedLead.tags && selectedLead.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {selectedLead.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-[10px]">
                      {SERVICE_LABELS[tag]?.label || tag}
                    </Badge>
                  ))}
                </div>
              )}

              {/* Activity Timeline */}
              <div className="space-y-3">
                <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  <Activity className="w-3.5 h-3.5" /> Activity Timeline
                </div>
                {loadingActivities ? (
                  <div className="text-xs text-muted-foreground py-4 text-center">Loading activities...</div>
                ) : activities.length > 0 ? (
                  <div className="space-y-0">
                    {activities.map((act, i) => {
                      const ActIcon = ACTIVITY_ICONS[act.activity_type] || Clock
                      return (
                        <div key={act.id} className="flex gap-3 relative">
                          {/* Timeline line */}
                          {i < activities.length - 1 && (
                            <div className="absolute left-[11px] top-7 bottom-0 w-px bg-border" />
                          )}
                          <div className="w-6 h-6 rounded-full bg-surface border border-border flex items-center justify-center shrink-0 z-10">
                            <ActIcon className="w-3 h-3 text-muted-foreground" />
                          </div>
                          <div className="flex-1 pb-4 min-w-0">
                            <div className="text-sm text-foreground leading-snug">{act.description}</div>
                            <div className="text-[10px] text-muted-foreground mt-0.5">{timeAgo(act.created_at)}</div>
                            {act.extra_data && !!(act.extra_data as Record<string, unknown>).message_preview && (
                              <div className="mt-1 p-2 rounded bg-surface text-xs text-muted-foreground line-clamp-2">
                                {String((act.extra_data as Record<string, unknown>).message_preview)}
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="text-xs text-muted-foreground/60 italic py-2">No activity recorded yet</div>
                )}
              </div>
            </div>

            {/* Drawer Footer */}
            <div className="p-4 border-t border-border bg-card sticky bottom-0 flex gap-2">
              {selectedLead.email && (
                <Button size="sm" className="flex-1" onClick={() => window.open(`mailto:${selectedLead.email}`)}>
                  <Mail className="w-4 h-4 mr-2" />Send Email
                </Button>
              )}
              {selectedLead.source_url && (
                <Button size="sm" variant="outline" className="flex-1" onClick={() => window.open(selectedLead.source_url!, "_blank")}>
                  <ExternalLink className="w-4 h-4 mr-2" />View Source
                </Button>
              )}
              {!selectedLead.email && !selectedLead.source_url && (
                <Button size="sm" variant="outline" className="flex-1" disabled>No actions available</Button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

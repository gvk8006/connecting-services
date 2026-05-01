import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import {
  Users,
  UserPlus,
  UserCheck,
  TrendingUp,
  Bot,
  Megaphone,
  ArrowUpRight,
  Play,
  Loader2,
  Globe,
  Code,
  Cpu,
  MessageSquare,
  Layout,
  Database,
  ShieldCheck,
  RefreshCw,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScoreBar } from "@/components/ui/score-bar"
import { StatusDot } from "@/components/ui/status-dot"
import { cn } from "@/lib/utils"
import type { DashboardStats, AgentStatusInfo } from "@/lib/api"

const SERVICE_LABELS: Record<string, { label: string; icon: typeof Globe; color: string }> = {
  website: { label: "Website", icon: Globe, color: "bg-primary/20 text-primary" },
  saas: { label: "SaaS Tool", icon: Code, color: "bg-[hsl(280_70%_55%/0.15)] text-[hsl(280_70%_55%)]" },
  ai_agents: { label: "AI Agents", icon: Cpu, color: "bg-success/15 text-success" },
  chatbot: { label: "Chatbot", icon: MessageSquare, color: "bg-warning/15 text-warning" },
  web_app: { label: "Web App", icon: Layout, color: "bg-[hsl(200_90%_50%/0.15)] text-[hsl(200_90%_50%)]" },
  crm: { label: "CRM", icon: Database, color: "bg-[hsl(210_80%_55%/0.15)] text-[hsl(210_80%_55%)]" },
  qc_ai: { label: "QC AI Tool", icon: ShieldCheck, color: "bg-[hsl(160_70%_45%/0.15)] text-[hsl(160_70%_45%)]" },
}

const EMPTY_STATS: DashboardStats = {
  total_leads: 0,
  new_today: 0,
  new_this_week: 0,
  qualified_leads: 0,
  conversion_rate: 0,
  active_agents: 0,
  active_campaigns: 0,
  average_score: 0,
  leads_by_source: {},
  leads_by_status: {},
  daily_trend: [],
  recent_leads: [],
  agent_total_leads: 0,
}

const sourceColors: Record<string, string> = {
  google: "bg-primary/20 text-primary",
  reddit: "bg-warning/15 text-warning",
  twitter: "bg-[hsl(200_90%_50%/0.15)] text-[hsl(200_90%_50%)]",
  form_capture: "bg-success/15 text-success",
  web_scrape: "bg-primary/20 text-primary",
  linkedin: "bg-[hsl(210_80%_55%/0.15)] text-[hsl(210_80%_55%)]",
  email_campaign: "bg-[hsl(280_70%_55%/0.15)] text-[hsl(280_70%_55%)]",
}

const statusBadgeVariant: Record<string, "default" | "success" | "warning" | "outline"> = {
  new: "default",
  contacted: "warning",
  qualified: "success",
  proposal: "default",
  negotiation: "warning",
  closed_won: "success",
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function DashboardPage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats>(EMPTY_STATS)
  const [agents, setAgents] = useState<AgentStatusInfo[]>([])
  const [runningAll, setRunningAll] = useState(false)
  const [runningAgentId, setRunningAgentId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(() => {
    fetch("/api/dashboard/stats")
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then(setStats)
      .catch(() => {})

    fetch("/api/agents/status")
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then(setAgents)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [fetchData])

  const handleRunAgent = async (agentId: string) => {
    setRunningAgentId(agentId)
    setAgents((prev) => prev.map((a) => a.id === agentId ? { ...a, status: "running" } : a))
    try {
      await fetch(`/api/agents/${agentId}/run`, { method: "POST" })
      setTimeout(fetchData, 2000)
    } catch { /* offline */ }
    setTimeout(() => setRunningAgentId(null), 3000)
  }

  const handleRunAll = async () => {
    setRunningAll(true)
    try {
      await fetch("/api/agents/run-all", { method: "POST" })
      setTimeout(fetchData, 5000)
    } catch { /* offline */ }
    setTimeout(() => { setRunningAll(false); fetchData() }, 8000)
  }

  const kpis = [
    { label: "Total Leads", value: stats.total_leads.toLocaleString(), icon: Users, color: "text-primary" },
    { label: "New Today", value: stats.new_today.toString(), icon: UserPlus, color: "text-success" },
    { label: "Qualified", value: stats.qualified_leads.toLocaleString(), icon: UserCheck, color: "text-primary" },
    { label: "Conversion Rate", value: `${stats.conversion_rate}%`, icon: TrendingUp, color: "text-success" },
    { label: "Active Agents", value: stats.active_agents.toString(), icon: Bot, color: "text-primary" },
    { label: "Campaigns", value: stats.active_campaigns.toString(), icon: Megaphone, color: "text-warning" },
  ]

  const maxDaily = Math.max(...(stats.daily_trend.map((d) => d.count)), 1)

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">Real-time lead generation overview</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchData}>
            <RefreshCw className="w-4 h-4 mr-2" />Refresh
          </Button>
          <Button onClick={handleRunAll} disabled={runningAll || agents.length === 0} size="sm">
            {runningAll ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Running Agents...</>
            ) : (
              <><Play className="w-4 h-4 mr-2" />Run All Agents</>
            )}
          </Button>
        </div>
      </div>

      {/* Service Categories */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold text-foreground">Services We Find Prospects For</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {Object.entries(SERVICE_LABELS).map(([key, svc]) => {
              const Icon = svc.icon
              return (
                <span key={key} className={cn("inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium", svc.color)}>
                  <Icon className="w-3.5 h-3.5" />{svc.label}
                </span>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {kpis.map((kpi) => (
          <Card key={kpi.label} className="hover:shadow-card-hover transition-shadow duration-300">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle>{kpi.label}</CardTitle>
                <kpi.icon className={cn("w-4 h-4", kpi.color)} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">{kpi.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* Lead Trend Chart */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold text-foreground">Lead Acquisition Trend</CardTitle>
              <span className="text-xs text-muted-foreground">Last 14 days</span>
            </div>
          </CardHeader>
          <CardContent>
            {stats.daily_trend.length > 0 ? (
              <>
                <div className="flex items-end gap-1 h-40">
                  {stats.daily_trend.map((d, i) => (
                    <div key={d.date} className="flex-1 group relative" style={{ animationDelay: `${i * 50}ms` }}>
                      <div className="absolute -top-6 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-popover border border-border rounded px-2 py-1 text-xs text-foreground whitespace-nowrap z-10 shadow-elevated">
                        {d.count} leads
                      </div>
                      <div
                        className="w-full rounded-t gradient-primary opacity-70 hover:opacity-100 transition-all duration-200 min-h-[4px]"
                        style={{ height: `${(d.count / maxDaily) * 100}%` }}
                      />
                    </div>
                  ))}
                </div>
                <div className="flex justify-between mt-2">
                  <span className="text-[10px] text-muted-foreground">{stats.daily_trend[0]?.date.slice(5)}</span>
                  <span className="text-[10px] text-muted-foreground">{stats.daily_trend[stats.daily_trend.length - 1]?.date.slice(5)}</span>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
                No trend data yet. Run the Prospector agent to start finding leads.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Leads by Source */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-foreground">Leads by Source</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(stats.leads_by_source).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(stats.leads_by_source)
                  .sort(([, a], [, b]) => b - a)
                  .map(([source, count]) => {
                    const total = Object.values(stats.leads_by_source).reduce((a, b) => a + b, 0)
                    const pct = Math.round((count / Math.max(total, 1)) * 100)
                    return (
                      <div key={source} className="space-y-1.5">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-foreground capitalize">{source.replace("_", " ")}</span>
                          <span className="text-muted-foreground font-mono text-xs">{count}</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                          <div className="h-full rounded-full gradient-primary transition-all duration-700" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    )
                  })}
              </div>
            ) : (
              <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
                No source data yet
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* Real-time Lead Feed */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CardTitle className="text-base font-semibold text-foreground">Recent Leads</CardTitle>
                <StatusDot status="running" />
                <span className="text-xs text-success font-medium">Live</span>
              </div>
              <span className="text-xs text-muted-foreground">{stats.recent_leads.length} latest</span>
            </div>
          </CardHeader>
          <CardContent>
            {stats.recent_leads.length > 0 ? (
              <div className="space-y-1">
                {stats.recent_leads.map((lead, i) => {
                  const displayName = lead.name === "Unknown" ? (lead.company || lead.email?.split("@")[0] || "Unknown Lead") : lead.name
                  const initials = displayName.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()
                  return (
                    <div
                      key={lead.id}
                      className="flex items-center gap-4 p-3 rounded-lg hover:bg-accent/50 cursor-pointer transition-colors animate-slide-up group"
                      style={{ animationDelay: `${i * 60}ms` }}
                      onClick={() => navigate(`/leads?id=${lead.id}`)}
                    >
                      <div className="w-9 h-9 rounded-full gradient-primary flex items-center justify-center text-xs font-bold text-primary-foreground shrink-0">
                        {initials}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-foreground truncate">{displayName}</span>
                          <Badge variant={statusBadgeVariant[lead.status] || "outline"}>{lead.status}</Badge>
                        </div>
                        <div className="text-xs text-muted-foreground truncate">
                          {lead.company && lead.company !== displayName ? lead.company : ""}{lead.company && lead.email ? " \u00b7 " : ""}{lead.email || ""}
                        </div>
                      </div>
                      <div className="w-24 shrink-0">
                        <ScoreBar score={lead.score} />
                      </div>
                      <div className="text-right shrink-0">
                        <span className={cn("inline-block rounded-full px-2 py-0.5 text-[10px] font-medium", sourceColors[lead.source] || "bg-secondary text-muted-foreground")}>
                          {lead.source.replace("_", " ")}
                        </span>
                        <div className="text-[10px] text-muted-foreground mt-1">{timeAgo(lead.created_at)}</div>
                      </div>
                      <ArrowUpRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-primary transition-colors shrink-0" />
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Users className="w-10 h-10 mb-3 opacity-30" />
                <p className="text-sm">No leads yet</p>
                <p className="text-xs mt-1">Run the Prospector agent to start finding leads</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Agent Control Panel */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold text-foreground">AI Agents</CardTitle>
              <Badge variant="success">{agents.filter((a) => a.is_enabled).length} Active</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : agents.length > 0 ? (
              <div className="space-y-3">
                {agents.map((agent) => (
                  <div key={agent.id} className="p-3 rounded-lg border border-border bg-surface hover:bg-surface-raised transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <StatusDot status={agent.status} />
                        <span className="text-sm font-medium text-foreground">{agent.name}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRunAgent(agent.id)}
                        disabled={agent.status === "running" || runningAgentId === agent.id}
                        className="h-7 px-2"
                      >
                        {agent.status === "running" || runningAgentId === agent.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Play className="w-3.5 h-3.5" />
                        )}
                      </Button>
                    </div>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{agent.leads_generated} leads generated</span>
                      <span>{agent.last_run_at ? timeAgo(agent.last_run_at) : "Never run"}</span>
                    </div>
                    {agent.status === "error" && agent.error_message && (
                      <p className="text-xs text-destructive mt-1 truncate">{agent.error_message}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Bot className="w-10 h-10 mb-3 opacity-30" />
                <p className="text-sm">No agents registered</p>
                <p className="text-xs mt-1">Start the backend server to register agents</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

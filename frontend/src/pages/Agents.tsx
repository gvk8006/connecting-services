import { useState, useEffect } from "react"
import {
  Bot,
  Play,
  Pause,
  RotateCcw,
  Settings,
  Loader2,
  Globe,
  Star,
  Mail,
  MessageCircle,
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  Search as SearchIcon,
  Send,
  Cpu,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { StatusDot } from "@/components/ui/status-dot"
import { cn } from "@/lib/utils"
import type { Agent } from "@/lib/api"

const AGENT_ICONS: Record<string, typeof Bot> = {
  scraper: Globe,
  qualifier: Star,
  email_outreach: Mail,
  social_monitor: MessageCircle,
  form_processor: FileText,
  prospector: SearchIcon,
  outreach_connector: Send,
}

const AGENT_DESCRIPTIONS: Record<string, string> = {
  prospector: "Multi-channel prospector that searches Google, Reddit, and Twitter for people actively looking for Website, SaaS, AI Agents, Chatbot, Web App, CRM, and QC AI tools.",
  qualifier: "AI-powered lead scoring engine. Analyzes contact completeness, company fit, job title relevance, and source quality to generate lead scores.",
  outreach_connector: "Sends personalized, service-specific outreach to qualified leads. Generates contextual pitches for each of the 7 service categories.",
  form_processor: "Handles inbound leads from web forms, landing pages, and API integrations. Validates, deduplicates, and enriches incoming leads.",
  scraper: "Scrapes websites and search results to discover potential leads. Extracts contact information, company details, and engagement signals.",
  email_outreach: "Sends AI-personalized outreach emails to qualified leads. Generates contextual, personalized content for each prospect.",
  social_monitor: "Monitors Twitter/X and LinkedIn for lead generation signals. Tracks keywords, hashtags, and engagement patterns in real-time.",
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "Never"
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "Just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("/api/agents")
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((data) => {
        setAgents(data)
        if (data.length > 0) setSelectedAgent(data[0])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleRunAgent = (agentId: string) => {
    setAgents((prev) =>
      prev.map((a) => a.id === agentId ? { ...a, status: "running" } : a)
    )
    if (selectedAgent?.id === agentId) {
      setSelectedAgent((prev) => prev ? { ...prev, status: "running" } : prev)
    }

    fetch(`/api/agents/${agentId}/run`, { method: "POST" })
      .then(() => {
        setTimeout(() => {
          fetch("/api/agents")
            .then((r) => r.ok ? r.json() : Promise.reject())
            .then((data) => {
              setAgents(data)
              const updated = data.find((a: Agent) => a.id === agentId)
              if (updated && selectedAgent?.id === agentId) setSelectedAgent(updated)
            })
            .catch(() => {})
        }, 3000)
      })
      .catch(() => {
        setAgents((prev) =>
          prev.map((a) => a.id === agentId ? { ...a, status: "error", error_message: "Failed to connect" } : a)
        )
      })
  }

  const handleToggle = (agentId: string) => {
    fetch(`/api/agents/${agentId}/toggle`, { method: "POST" })
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then(() => {
        setAgents((prev) =>
          prev.map((a) => a.id === agentId ? { ...a, is_enabled: !a.is_enabled } : a)
        )
        if (selectedAgent?.id === agentId) {
          setSelectedAgent((prev) => prev ? { ...prev, is_enabled: !prev.is_enabled } : prev)
        }
      })
      .catch(() => {})
  }

  const totalLeads = agents.reduce((sum, a) => sum + a.leads_generated, 0)
  const activeCount = agents.filter((a) => a.is_enabled).length
  const runningCount = agents.filter((a) => a.status === "running").length

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32 text-muted-foreground">
        <Loader2 className="w-6 h-6 animate-spin mr-2" />Loading agents...
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">AI Agents</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage your autonomous lead generation agents</p>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>{activeCount} active</span>
          <span>{runningCount} running</span>
          <span>{totalLeads.toLocaleString()} leads total</span>
        </div>
      </div>

      {agents.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <Bot className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm">No agents registered</p>
            <p className="text-xs mt-1">Start the backend server to register agents</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid lg:grid-cols-5 gap-6">
          {/* Agent List */}
          <div className="lg:col-span-3 space-y-3">
            {agents.map((agent) => {
              const Icon = AGENT_ICONS[agent.agent_type] || Bot
              return (
                <Card
                  key={agent.id}
                  className={cn(
                    "cursor-pointer transition-all duration-200 hover:shadow-card-hover",
                    selectedAgent?.id === agent.id && "ring-1 ring-primary/50 shadow-glow-primary",
                    !agent.is_enabled && "opacity-60"
                  )}
                  onClick={() => setSelectedAgent(agent)}
                >
                  <CardContent className="p-5">
                    <div className="flex items-start gap-4">
                      <div className={cn(
                        "w-11 h-11 rounded-xl flex items-center justify-center shrink-0",
                        agent.status === "running" ? "gradient-primary shadow-glow-primary" : "bg-secondary"
                      )}>
                        <Icon className={cn("w-5 h-5", agent.status === "running" ? "text-primary-foreground" : "text-muted-foreground")} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-semibold text-foreground">{agent.name}</h3>
                          <StatusDot status={agent.status} />
                          <Badge variant={agent.is_enabled ? "success" : "outline"}>
                            {agent.is_enabled ? "Enabled" : "Disabled"}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {AGENT_DESCRIPTIONS[agent.agent_type] || `${agent.agent_type} agent`}
                        </p>
                        <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <CheckCircle className="w-3 h-3 text-success" />
                            <span>{agent.leads_generated} leads</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>Last run: {timeAgo(agent.last_run_at)}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRunAgent(agent.id)}
                          disabled={agent.status === "running" || !agent.is_enabled}
                          className="h-8 w-8"
                        >
                          {agent.status === "running" ? (
                            <Loader2 className="w-4 h-4 animate-spin text-primary" />
                          ) : (
                            <Play className="w-4 h-4" />
                          )}
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleToggle(agent.id)}>
                          {agent.is_enabled ? <Pause className="w-4 h-4" /> : <RotateCcw className="w-4 h-4" />}
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Agent Detail */}
          <Card className="lg:col-span-2 h-fit sticky top-8">
            <CardHeader>
              <CardTitle className="text-base font-semibold text-foreground">
                {selectedAgent ? selectedAgent.name : "Select an Agent"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedAgent ? (
                <div className="space-y-5 animate-fade-in">
                  <div className="flex items-center gap-2">
                    <StatusDot status={selectedAgent.status} />
                    <span className="text-sm text-foreground capitalize">{selectedAgent.status}</span>
                    {selectedAgent.status === "running" && (
                      <span className="text-xs text-primary animate-pulse-glow">Processing...</span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {AGENT_DESCRIPTIONS[selectedAgent.agent_type] || `${selectedAgent.agent_type} agent`}
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg bg-surface border border-border">
                      <div className="text-xs text-muted-foreground">Leads Generated</div>
                      <div className="text-xl font-bold text-foreground mt-1">{selectedAgent.leads_generated}</div>
                    </div>
                    <div className="p-3 rounded-lg bg-surface border border-border">
                      <div className="text-xs text-muted-foreground">Last Run</div>
                      <div className="text-sm font-medium text-foreground mt-2">{timeAgo(selectedAgent.last_run_at)}</div>
                    </div>
                  </div>
                  {selectedAgent.config && Object.keys(selectedAgent.config).length > 0 && (
                    <div>
                      <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Configuration</div>
                      <div className="space-y-1.5">
                        {Object.entries(selectedAgent.config).map(([key, value]) => (
                          <div key={key} className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">{key.replace("_", " ")}</span>
                            <span className="text-foreground font-mono text-xs">
                              {Array.isArray(value) ? value.length + " items" : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {selectedAgent.error_message && (
                    <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                      <div className="flex items-center gap-2 text-xs font-medium text-destructive mb-1">
                        <XCircle className="w-3.5 h-3.5" /> Error
                      </div>
                      <p className="text-xs text-destructive/80">{selectedAgent.error_message}</p>
                    </div>
                  )}
                  <div className="flex gap-2 pt-2">
                    <Button
                      size="sm"
                      className="flex-1"
                      onClick={() => handleRunAgent(selectedAgent.id)}
                      disabled={selectedAgent.status === "running" || !selectedAgent.is_enabled}
                    >
                      {selectedAgent.status === "running" ? (
                        <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Running...</>
                      ) : (
                        <><Play className="w-4 h-4 mr-2" />Run Now</>
                      )}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleToggle(selectedAgent.id)}>
                      <Settings className="w-4 h-4 mr-2" />
                      {selectedAgent.is_enabled ? "Disable" : "Enable"}
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground text-sm">
                  Select an agent to view details
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

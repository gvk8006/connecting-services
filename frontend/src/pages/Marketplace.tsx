import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import {
  Building2,
  FileSearch,
  GitBranch,
  DollarSign,
  TrendingUp,
  Users,
  ArrowRight,
  Loader2,
  RefreshCw,
  CheckCircle2,
  Clock,
  XCircle,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import type { MarketplaceStats, MatchItem } from "@/lib/api"

const EMPTY_STATS: MarketplaceStats = {
  total_providers: 0,
  active_providers: 0,
  total_requests: 0,
  open_requests: 0,
  total_matches: 0,
  active_matches: 0,
  completed_matches: 0,
  match_success_rate: 0,
  total_revenue: 0,
  pending_revenue: 0,
  paid_revenue: 0,
}

const matchStatusConfig: Record<string, { label: string; variant: "default" | "success" | "warning" | "outline"; icon: typeof CheckCircle2 }> = {
  proposed: { label: "Proposed", variant: "outline", icon: Clock },
  approved: { label: "Approved", variant: "default", icon: CheckCircle2 },
  intro_sent: { label: "Intro Sent", variant: "warning", icon: ArrowRight },
  in_progress: { label: "In Progress", variant: "warning", icon: Clock },
  completed: { label: "Completed", variant: "success", icon: CheckCircle2 },
  failed: { label: "Failed", variant: "outline", icon: XCircle },
  rejected: { label: "Rejected", variant: "outline", icon: XCircle },
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

export function MarketplacePage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<MarketplaceStats>(EMPTY_STATS)
  const [recentMatches, setRecentMatches] = useState<MatchItem[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const [s, m] = await Promise.all([
        api.getMarketplaceStats(),
        api.getMatches({ limit: "8" }),
      ])
      setStats(s)
      setRecentMatches(m)
    } catch {
      /* offline */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const kpis = [
    { label: "Active Providers", value: stats.active_providers, icon: Building2, color: "text-primary" },
    { label: "Open Requests", value: stats.open_requests, icon: FileSearch, color: "text-warning" },
    { label: "Active Matches", value: stats.active_matches, icon: GitBranch, color: "text-success" },
    { label: "Completed", value: stats.completed_matches, icon: CheckCircle2, color: "text-primary" },
    { label: "Success Rate", value: `${stats.match_success_rate}%`, icon: TrendingUp, color: "text-success" },
    { label: "Total Revenue", value: `$${stats.total_revenue.toLocaleString()}`, icon: DollarSign, color: "text-warning" },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Marketplace</h1>
          <p className="text-sm text-muted-foreground mt-1">Connect service seekers with providers</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />Refresh
        </Button>
      </div>

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

      {/* Quick Actions + Revenue */}
      <div className="grid lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold text-foreground">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button variant="outline" className="w-full justify-start" onClick={() => navigate("/providers")}>
              <Building2 className="w-4 h-4 mr-2" />Manage Providers
            </Button>
            <Button variant="outline" className="w-full justify-start" onClick={() => navigate("/requests")}>
              <FileSearch className="w-4 h-4 mr-2" />View Service Requests
            </Button>
            <Button variant="outline" className="w-full justify-start" onClick={() => navigate("/matches")}>
              <GitBranch className="w-4 h-4 mr-2" />Pending Matches
            </Button>
            <Button variant="outline" className="w-full justify-start" onClick={() => navigate("/revenue")}>
              <DollarSign className="w-4 h-4 mr-2" />Revenue Dashboard
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold text-foreground">Revenue Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Total Earned</span>
              <span className="text-lg font-bold text-foreground">${stats.total_revenue.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Pending</span>
              <span className="text-sm font-medium text-warning">${stats.pending_revenue.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Paid</span>
              <span className="text-sm font-medium text-success">${stats.paid_revenue.toLocaleString()}</span>
            </div>
            <div className="h-2 rounded-full bg-secondary overflow-hidden">
              <div
                className="h-full rounded-full gradient-primary"
                style={{ width: `${stats.total_revenue > 0 ? (stats.paid_revenue / stats.total_revenue) * 100 : 0}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold text-foreground">Platform Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-primary" />
                <span className="text-muted-foreground">Total Providers</span>
              </div>
              <span className="font-medium text-foreground">{stats.total_providers}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <FileSearch className="w-4 h-4 text-warning" />
                <span className="text-muted-foreground">Total Requests</span>
              </div>
              <span className="font-medium text-foreground">{stats.total_requests}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-success" />
                <span className="text-muted-foreground">Total Matches</span>
              </div>
              <span className="font-medium text-foreground">{stats.total_matches}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Matches */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold text-foreground">Recent Matches</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => navigate("/matches")}>
              View All <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {recentMatches.length > 0 ? (
            <div className="space-y-2">
              {recentMatches.map((match) => {
                const cfg = matchStatusConfig[match.status] || matchStatusConfig.proposed
                return (
                  <div
                    key={match.id}
                    className="flex items-center justify-between p-3 rounded-lg hover:bg-accent/50 transition-colors cursor-pointer"
                    onClick={() => navigate("/matches")}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground truncate">
                          {match.request_title || "Untitled Request"}
                        </span>
                        <Badge variant={cfg.variant}>{cfg.label}</Badge>
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {match.seeker_name || "Unknown Seeker"} → {match.provider_name || "Unknown Provider"}
                      </div>
                    </div>
                    <div className="text-right shrink-0 ml-4">
                      <div className="text-sm font-mono text-foreground">{match.match_score}%</div>
                      <div className="text-[10px] text-muted-foreground">{timeAgo(match.created_at)}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <GitBranch className="w-10 h-10 mb-3 opacity-30" />
              <p className="text-sm">No matches yet</p>
              <p className="text-xs mt-1">Convert providers and create service requests to start matching</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

import { useState, useEffect } from "react"
import {
  BarChart3,
  TrendingUp,
  Users,
  Target,
  ArrowUpRight,
  Loader2,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { LeadStats } from "@/lib/api"

const statusColors: Record<string, string> = {
  new: "bg-primary",
  contacted: "bg-warning",
  qualified: "bg-success",
  proposal: "bg-[hsl(280_70%_55%)]",
  negotiation: "bg-[hsl(200_90%_50%)]",
  closed_won: "bg-success",
}

export function AnalyticsPage() {
  const [stats, setStats] = useState<LeadStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("/api/leads/stats")
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32 text-muted-foreground">
        <Loader2 className="w-6 h-6 animate-spin mr-2" />Loading analytics...
      </div>
    )
  }

  if (!stats || stats.total === 0) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">Lead generation performance insights</p>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <BarChart3 className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm">No analytics data yet</p>
            <p className="text-xs mt-1">Run the Prospector agent to generate leads and populate analytics</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const totalBySource = Object.values(stats.by_source).reduce((a, b) => a + b, 0)
  const totalByStatus = Object.values(stats.by_status).reduce((a, b) => a + b, 0)
  const maxDaily = Math.max(...(stats.daily_leads?.map((d) => d.count) || [1]), 1)
  const topSource = Object.entries(stats.by_source).sort(([, a], [, b]) => b - a)[0]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground mt-1">Lead generation performance insights</p>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Leads", value: stats.total.toLocaleString(), icon: Users, color: "text-primary" },
          { label: "Conversion Rate", value: `${stats.conversion_rate}%`, icon: Target, color: "text-success" },
          { label: "Avg Lead Score", value: `${Math.round(stats.average_score * 100)}%`, icon: TrendingUp, color: "text-primary" },
          { label: "Top Source", value: topSource ? topSource[0] : "N/A", icon: BarChart3, color: "text-warning" },
        ].map((stat) => (
          <Card key={stat.label} className="hover:shadow-card-hover transition-shadow">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">{stat.label}</span>
                <stat.icon className={cn("w-4 h-4", stat.color)} />
              </div>
              <div className="text-2xl font-bold text-foreground">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Daily Trend */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold text-foreground">Daily Lead Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {stats.daily_leads && stats.daily_leads.length > 0 ? (
              <div className="space-y-3">
                {stats.daily_leads.map((day) => (
                  <div key={day.date} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground w-20">{day.date.slice(5)}</span>
                      <span className="text-foreground">{day.count} leads</span>
                    </div>
                    <div className="h-2 rounded-full bg-secondary overflow-hidden">
                      <div
                        className="h-full rounded-full gradient-primary transition-all duration-700"
                        style={{ width: `${(day.count / maxDaily) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground text-center py-8">No daily trend data</div>
            )}
          </CardContent>
        </Card>

        {/* Source Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold text-foreground">Lead Sources</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(stats.by_source).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(stats.by_source)
                  .sort(([, a], [, b]) => b - a)
                  .map(([source, count]) => {
                    const pct = Math.round((count / totalBySource) * 100)
                    return (
                      <div key={source} className="flex items-center gap-3">
                        <span className="text-sm text-foreground w-28 shrink-0 capitalize">{source.replace("_", " ")}</span>
                        <div className="flex-1 h-2 rounded-full bg-secondary overflow-hidden">
                          <div className="h-full rounded-full gradient-primary transition-all duration-700" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="text-xs font-mono text-muted-foreground w-16 text-right">{count} ({pct}%)</span>
                      </div>
                    )
                  })}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground text-center py-8">No source data</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Pipeline / Status Breakdown */}
      {Object.keys(stats.by_status).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold text-foreground">Lead Pipeline</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2 h-48">
              {Object.entries(stats.by_status).map(([status, count]) => {
                const pct = Math.round((count / totalByStatus) * 100)
                const barColor = statusColors[status] || "bg-muted"
                return (
                  <div key={status} className="flex-1 flex flex-col items-center group">
                    <div className="text-xs font-mono text-foreground opacity-0 group-hover:opacity-100 transition-opacity mb-1">
                      {count}
                    </div>
                    <div className="w-full relative rounded-t-md overflow-hidden" style={{ height: `${Math.max(pct * 1.8, 8)}px` }}>
                      <div className={cn("absolute inset-0 opacity-80 hover:opacity-100 transition-opacity", barColor)} />
                    </div>
                    <div className="mt-2 text-[10px] text-muted-foreground text-center leading-tight capitalize">{status.replace("_", " ")}</div>
                    <div className="text-[10px] text-muted-foreground">{pct}%</div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

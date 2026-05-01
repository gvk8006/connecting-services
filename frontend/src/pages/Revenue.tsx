import { useEffect, useState, useCallback } from "react"
import {
  DollarSign,
  TrendingUp,
  Clock,
  CheckCircle2,
  Loader2,
  RefreshCw,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import type { CommissionItem, CommissionStats } from "@/lib/api"

const EMPTY_STATS: CommissionStats = {
  total_revenue: 0,
  pending_revenue: 0,
  paid_revenue: 0,
  commission_count: 0,
  average_deal_size: 0,
}

const statusVariant: Record<string, "default" | "success" | "warning" | "outline"> = {
  pending: "warning",
  invoiced: "default",
  paid: "success",
  waived: "outline",
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

export function RevenuePage() {
  const [stats, setStats] = useState<CommissionStats>(EMPTY_STATS)
  const [commissions, setCommissions] = useState<CommissionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [updatingId, setUpdatingId] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([
        api.getCommissionStats(),
        api.getCommissions(),
      ])
      setStats(s)
      setCommissions(c)
    } catch { /* */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleMarkPaid = async (id: string) => {
    setUpdatingId(id)
    try {
      await api.updateCommission(id, { status: "paid" })
      await fetchData()
    } catch { /* */ }
    finally { setUpdatingId(null) }
  }

  const handleWaive = async (id: string) => {
    setUpdatingId(id)
    try {
      await api.updateCommission(id, { status: "waived" })
      await fetchData()
    } catch { /* */ }
    finally { setUpdatingId(null) }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const kpis = [
    { label: "Total Revenue", value: `$${stats.total_revenue.toLocaleString()}`, icon: DollarSign, color: "text-primary" },
    { label: "Pending", value: `$${stats.pending_revenue.toLocaleString()}`, icon: Clock, color: "text-warning" },
    { label: "Paid", value: `$${stats.paid_revenue.toLocaleString()}`, icon: CheckCircle2, color: "text-success" },
    { label: "Avg Deal Size", value: `$${stats.average_deal_size.toLocaleString()}`, icon: TrendingUp, color: "text-primary" },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Revenue</h1>
          <p className="text-sm text-muted-foreground mt-1">{stats.commission_count} commissions tracked</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />Refresh
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
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

      {/* Revenue Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold text-foreground">Revenue Collection Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Paid</span>
              <span className="font-medium text-success">${stats.paid_revenue.toLocaleString()}</span>
            </div>
            <div className="h-3 rounded-full bg-secondary overflow-hidden">
              <div
                className="h-full rounded-full bg-success transition-all duration-700"
                style={{ width: `${stats.total_revenue > 0 ? (stats.paid_revenue / stats.total_revenue) * 100 : 0}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Pending collection</span>
              <span className="font-medium text-warning">${stats.pending_revenue.toLocaleString()}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Commission List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold text-foreground">Commission History</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Request</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Provider</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Deal Value</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Rate</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Commission</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {commissions.length > 0 ? commissions.map((c) => (
                  <tr key={c.id} className="border-b border-border/50 hover:bg-accent/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-foreground truncate max-w-[160px]">{c.request_title || "Match"}</div>
                      <div className="text-[10px] text-muted-foreground">{c.seeker_name || ""} | {timeAgo(c.created_at)}</div>
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground">{c.provider_name || "Unknown"}</td>
                    <td className="px-4 py-3 text-sm font-medium text-foreground">${c.base_amount.toLocaleString()}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{c.percentage_rate}%</td>
                    <td className="px-4 py-3 text-sm font-bold text-foreground">${c.commission_amount.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <Badge variant={statusVariant[c.status] || "outline"}>{c.status}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      {c.status === "pending" && (
                        <div className="flex items-center gap-1">
                          <Button size="sm" variant="outline" disabled={updatingId === c.id} onClick={() => handleMarkPaid(c.id)}>
                            {updatingId === c.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3 mr-1" />}
                            Paid
                          </Button>
                          <Button size="sm" variant="ghost" disabled={updatingId === c.id} onClick={() => handleWaive(c.id)}>
                            Waive
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center">
                      <DollarSign className="w-10 h-10 mx-auto mb-3 opacity-30 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">No commissions yet</p>
                      <p className="text-xs text-muted-foreground mt-1">Complete matches to generate commissions</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

import { useEffect, useState, useCallback } from "react"
import {
  GitBranch,
  CheckCircle2,
  XCircle,
  Send,
  DollarSign,
  Loader2,
  RefreshCw,
  X,
  Clock,
  ArrowRight,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import type { MatchItem } from "@/lib/api"

const statusConfig: Record<string, { label: string; variant: "default" | "success" | "warning" | "outline"; icon: typeof CheckCircle2 }> = {
  proposed: { label: "Proposed", variant: "outline", icon: Clock },
  approved: { label: "Approved", variant: "default", icon: CheckCircle2 },
  intro_sent: { label: "Intro Sent", variant: "warning", icon: Send },
  in_progress: { label: "In Progress", variant: "warning", icon: ArrowRight },
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

export function MatchesPage() {
  const [matches, setMatches] = useState<MatchItem[]>([])
  const [loading, setLoading] = useState(true)
  const [actionId, setActionId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState("")
  const [completeModal, setCompleteModal] = useState<string | null>(null)
  const [agreedAmount, setAgreedAmount] = useState("")
  const [commissionRate, setCommissionRate] = useState("10")

  const fetchMatches = useCallback(async () => {
    try {
      const params: Record<string, string> = {}
      if (statusFilter) params.status = statusFilter
      const data = await api.getMatches(params)
      setMatches(data)
    } catch { /* */ }
    finally { setLoading(false) }
  }, [statusFilter])

  useEffect(() => { fetchMatches() }, [fetchMatches])

  const handleAction = async (matchId: string, action: "approve" | "reject" | "send-intro" | "fail") => {
    setActionId(matchId)
    try {
      if (action === "approve") await api.approveMatch(matchId)
      else if (action === "reject") await api.rejectMatch(matchId)
      else if (action === "send-intro") await api.sendIntro(matchId)
      else if (action === "fail") await api.failMatch(matchId)
      await fetchMatches()
    } catch { /* */ }
    finally { setActionId(null) }
  }

  const handleComplete = async () => {
    if (!completeModal || !agreedAmount) return
    setActionId(completeModal)
    try {
      await api.completeMatch(completeModal, {
        agreed_amount: parseFloat(agreedAmount),
        commission_rate: parseFloat(commissionRate) || 10,
      })
      setCompleteModal(null)
      setAgreedAmount("")
      setCommissionRate("10")
      await fetchMatches()
    } catch { /* */ }
    finally { setActionId(null) }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Matches</h1>
          <p className="text-sm text-muted-foreground mt-1">{matches.length} total matches</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-border bg-surface text-sm text-foreground"
          >
            <option value="">All Statuses</option>
            <option value="proposed">Proposed</option>
            <option value="approved">Approved</option>
            <option value="intro_sent">Intro Sent</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="rejected">Rejected</option>
          </select>
          <Button variant="outline" size="sm" onClick={fetchMatches}>
            <RefreshCw className="w-4 h-4 mr-2" />Refresh
          </Button>
        </div>
      </div>

      {/* Matches Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Request</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Seeker</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Provider</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Score</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {matches.length > 0 ? matches.map((m) => {
                  const cfg = statusConfig[m.status] || statusConfig.proposed
                  const isActioning = actionId === m.id
                  return (
                    <tr key={m.id} className="border-b border-border/50 hover:bg-accent/30 transition-colors">
                      <td className="px-4 py-3">
                        <div className="text-sm font-medium text-foreground truncate max-w-[180px]">{m.request_title || "Untitled"}</div>
                        <div className="text-[10px] text-muted-foreground">{m.request_category} | {timeAgo(m.created_at)}</div>
                      </td>
                      <td className="px-4 py-3 text-sm text-foreground">{m.seeker_name || "Unknown"}</td>
                      <td className="px-4 py-3 text-sm text-foreground">{m.provider_name || "Unknown"}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 rounded-full bg-secondary overflow-hidden">
                            <div className="h-full rounded-full gradient-primary" style={{ width: `${m.match_score}%` }} />
                          </div>
                          <span className="text-xs font-mono text-foreground">{m.match_score}</span>
                        </div>
                        {m.match_reason && (
                          <div className="text-[10px] text-muted-foreground mt-0.5 truncate max-w-[160px]">{m.match_reason}</div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={cfg.variant}>{cfg.label}</Badge>
                        {m.agreed_amount && (
                          <div className="text-[10px] text-success mt-0.5">${m.agreed_amount.toLocaleString()}</div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          {m.status === "proposed" && (
                            <>
                              <Button size="sm" variant="outline" disabled={isActioning} onClick={() => handleAction(m.id, "approve")}>
                                {isActioning ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                              </Button>
                              <Button size="sm" variant="outline" disabled={isActioning} onClick={() => handleAction(m.id, "reject")}>
                                <XCircle className="w-3 h-3" />
                              </Button>
                            </>
                          )}
                          {m.status === "approved" && (
                            <Button size="sm" variant="outline" disabled={isActioning} onClick={() => handleAction(m.id, "send-intro")}>
                              {isActioning ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3 mr-1" />}
                              Intro
                            </Button>
                          )}
                          {(m.status === "intro_sent" || m.status === "in_progress") && (
                            <>
                              <Button size="sm" onClick={() => { setCompleteModal(m.id); setAgreedAmount(""); setCommissionRate("10") }}>
                                <DollarSign className="w-3 h-3 mr-1" />Complete
                              </Button>
                              <Button size="sm" variant="outline" disabled={isActioning} onClick={() => handleAction(m.id, "fail")}>
                                <XCircle className="w-3 h-3" />
                              </Button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                }) : (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center">
                      <GitBranch className="w-10 h-10 mx-auto mb-3 opacity-30 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">No matches found</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Complete Match Modal */}
      {completeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card border border-border rounded-xl shadow-elevated w-full max-w-sm overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-lg font-semibold text-foreground">Complete Match</h2>
              <button onClick={() => setCompleteModal(null)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Agreed Deal Amount ($)</label>
                <input
                  type="number"
                  value={agreedAmount}
                  onChange={(e) => setAgreedAmount(e.target.value)}
                  placeholder="e.g. 5000"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-sm text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Commission Rate (%)</label>
                <input
                  type="number"
                  value={commissionRate}
                  onChange={(e) => setCommissionRate(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-sm text-foreground"
                />
              </div>
              {agreedAmount && (
                <div className="p-3 rounded-lg bg-success/10 text-sm">
                  <span className="text-muted-foreground">Commission: </span>
                  <span className="font-bold text-success">
                    ${(parseFloat(agreedAmount) * (parseFloat(commissionRate) || 10) / 100).toFixed(2)}
                  </span>
                </div>
              )}
              <Button className="w-full" disabled={!agreedAmount || actionId === completeModal} onClick={handleComplete}>
                {actionId === completeModal ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
                Complete & Create Commission
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

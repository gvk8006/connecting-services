import { useEffect, useState, useCallback } from "react"
import {
  FileSearch,
  Plus,
  Search,
  Loader2,
  RefreshCw,
  Zap,
  X,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import type { ServiceRequestItem, Lead } from "@/lib/api"

const SERVICE_LABELS: Record<string, string> = {
  website: "Website",
  saas: "SaaS Tool",
  ai_agents: "AI Agents",
  chatbot: "Chatbot",
  web_app: "Web App",
  crm: "CRM",
  qc_ai: "QC AI Tool",
}

const statusConfig: Record<string, "default" | "success" | "warning" | "outline"> = {
  open: "default",
  matching: "warning",
  matched: "success",
  completed: "success",
  cancelled: "outline",
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

export function ServiceRequestsPage() {
  const [requests, setRequests] = useState<ServiceRequestItem[]>([])
  const [loading, setLoading] = useState(true)
  const [findingMatches, setFindingMatches] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [searchTerm, setSearchTerm] = useState("")
  const [showCreate, setShowCreate] = useState(false)
  const [seekerLeads, setSeekerLeads] = useState<Lead[]>([])
  const [newReq, setNewReq] = useState({ lead_id: "", title: "", description: "", service_category: "website", budget_min: "", budget_max: "", timeline: "flexible" })
  const [creating, setCreating] = useState(false)

  const fetchRequests = useCallback(async () => {
    try {
      const params: Record<string, string> = {}
      if (statusFilter) params.status = statusFilter
      const data = await api.getServiceRequests(params)
      setRequests(data)
    } catch { /* */ }
    finally { setLoading(false) }
  }, [statusFilter])

  useEffect(() => { fetchRequests() }, [fetchRequests])

  const handleFindMatches = async (requestId: string) => {
    setFindingMatches(requestId)
    try {
      await api.findMatches(requestId, 5)
      await fetchRequests()
    } catch { /* */ }
    finally { setFindingMatches(null) }
  }

  const handleOpenCreate = async () => {
    setShowCreate(true)
    try {
      const allLeads = await api.getLeads({ limit: "200" })
      setSeekerLeads(allLeads.filter((l) => l.lead_type === "seeker" || l.lead_type === "both" || l.lead_type === "unknown"))
    } catch { /* */ }
  }

  const handleCreate = async () => {
    if (!newReq.lead_id || !newReq.title) return
    setCreating(true)
    try {
      await api.createServiceRequest({
        lead_id: newReq.lead_id,
        title: newReq.title,
        description: newReq.description || null,
        service_category: newReq.service_category,
        budget_min: newReq.budget_min ? parseFloat(newReq.budget_min) : null,
        budget_max: newReq.budget_max ? parseFloat(newReq.budget_max) : null,
        timeline: newReq.timeline,
      } as Partial<ServiceRequestItem>)
      setShowCreate(false)
      setNewReq({ lead_id: "", title: "", description: "", service_category: "website", budget_min: "", budget_max: "", timeline: "flexible" })
      await fetchRequests()
    } catch { /* */ }
    finally { setCreating(false) }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const filtered = requests.filter((r) => {
    if (searchTerm) {
      const s = searchTerm.toLowerCase()
      return r.title.toLowerCase().includes(s) || (r.seeker_name || "").toLowerCase().includes(s)
    }
    return true
  })

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Service Requests</h1>
          <p className="text-sm text-muted-foreground mt-1">{requests.length} requests from seekers</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchRequests}>
            <RefreshCw className="w-4 h-4 mr-2" />Refresh
          </Button>
          <Button size="sm" onClick={handleOpenCreate}>
            <Plus className="w-4 h-4 mr-2" />Create Request
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search requests..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-surface text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border border-border bg-surface text-sm text-foreground"
        >
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="matching">Matching</option>
          <option value="matched">Matched</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Requests Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Request</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Seeker</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Service</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Budget</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Matches</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length > 0 ? filtered.map((r) => (
                  <tr key={r.id} className="border-b border-border/50 hover:bg-accent/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-foreground truncate max-w-[200px]">{r.title}</div>
                      <div className="text-[10px] text-muted-foreground">{timeAgo(r.created_at)}</div>
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground">{r.seeker_name || "Unknown"}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium bg-primary/10 text-primary">
                        {SERVICE_LABELS[r.service_category] || r.service_category}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground">
                      {r.budget_min || r.budget_max
                        ? `$${r.budget_min || 0} - $${r.budget_max || "?"}`
                        : "Not specified"}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-foreground">{r.match_count}</td>
                    <td className="px-4 py-3">
                      <Badge variant={statusConfig[r.status] || "outline"}>{r.status}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      {r.status === "open" && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={findingMatches === r.id}
                          onClick={() => handleFindMatches(r.id)}
                        >
                          {findingMatches === r.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                          ) : (
                            <Zap className="w-3.5 h-3.5 mr-1" />
                          )}
                          Find Matches
                        </Button>
                      )}
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center">
                      <FileSearch className="w-10 h-10 mx-auto mb-3 opacity-30 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">No service requests</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Create Request Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card border border-border rounded-xl shadow-elevated w-full max-w-lg overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-lg font-semibold text-foreground">Create Service Request</h2>
              <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Seeker Lead</label>
                <select
                  value={newReq.lead_id}
                  onChange={(e) => setNewReq({ ...newReq, lead_id: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-sm text-foreground"
                >
                  <option value="">Select a seeker...</option>
                  {seekerLeads.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.company || `${l.first_name || ""} ${l.last_name || ""}`.trim() || l.email || "Unknown"}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Title</label>
                <input
                  type="text"
                  value={newReq.title}
                  onChange={(e) => setNewReq({ ...newReq, title: e.target.value })}
                  placeholder="e.g. Need a website for my restaurant"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-sm text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Service Category</label>
                <select
                  value={newReq.service_category}
                  onChange={(e) => setNewReq({ ...newReq, service_category: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-sm text-foreground"
                >
                  {Object.entries(SERVICE_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Budget Min ($)</label>
                  <input type="number" value={newReq.budget_min} onChange={(e) => setNewReq({ ...newReq, budget_min: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-sm text-foreground" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Budget Max ($)</label>
                  <input type="number" value={newReq.budget_max} onChange={(e) => setNewReq({ ...newReq, budget_max: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-sm text-foreground" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Timeline</label>
                <select value={newReq.timeline} onChange={(e) => setNewReq({ ...newReq, timeline: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-sm text-foreground">
                  <option value="urgent">Urgent</option>
                  <option value="1_week">1 Week</option>
                  <option value="2_weeks">2 Weeks</option>
                  <option value="1_month">1 Month</option>
                  <option value="flexible">Flexible</option>
                </select>
              </div>
              <Button className="w-full" disabled={!newReq.lead_id || !newReq.title || creating} onClick={handleCreate}>
                {creating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Create Request
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

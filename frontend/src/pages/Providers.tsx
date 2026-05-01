import { useEffect, useState, useCallback } from "react"
import {
  Building2,
  Plus,
  Search,
  Star,
  GitBranch,
  CheckCircle2,
  Loader2,
  RefreshCw,
  X,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import type { ProviderProfile, Lead } from "@/lib/api"

const SERVICE_LABELS: Record<string, string> = {
  website: "Website",
  saas: "SaaS Tool",
  ai_agents: "AI Agents",
  chatbot: "Chatbot",
  web_app: "Web App",
  crm: "CRM",
  qc_ai: "QC AI Tool",
}

export function ProvidersPage() {
  const [providers, setProviders] = useState<ProviderProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [showConvert, setShowConvert] = useState(false)
  const [leads, setLeads] = useState<Lead[]>([])
  const [convertingId, setConvertingId] = useState<string | null>(null)
  const [selectedServices, setSelectedServices] = useState<string[]>([])
  const [searchTerm, setSearchTerm] = useState("")

  const fetchProviders = useCallback(async () => {
    try {
      const data = await api.getProviders({ active_only: "false" })
      setProviders(data)
    } catch { /* offline */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchProviders() }, [fetchProviders])

  const handleOpenConvert = async () => {
    setShowConvert(true)
    try {
      const allLeads = await api.getLeads({ limit: "200" })
      // Filter to leads that are providers (or unknown) and don't already have profiles
      const providerLeadIds = new Set(providers.map((p) => p.lead_id))
      setLeads(allLeads.filter((l) => !providerLeadIds.has(l.id) && l.lead_type !== "seeker"))
    } catch { /* */ }
  }

  const handleConvert = async (leadId: string) => {
    setConvertingId(leadId)
    try {
      const lead = leads.find((l) => l.id === leadId)
      const service = lead?.custom_fields?.service_needed
      await api.convertLeadToProvider(leadId, {
        services_offered: service ? [service] : [],
        description: lead?.ai_summary || lead?.notes || null,
      } as Partial<ProviderProfile>)
      await fetchProviders()
      setLeads((prev) => prev.filter((l) => l.id !== leadId))
    } catch { /* */ }
    finally { setConvertingId(null) }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const filtered = providers.filter((p) => {
    if (searchTerm) {
      const s = searchTerm.toLowerCase()
      const match = (p.lead_name || "").toLowerCase().includes(s) ||
        (p.lead_company || "").toLowerCase().includes(s) ||
        (p.lead_email || "").toLowerCase().includes(s)
      if (!match) return false
    }
    return true
  })

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Providers</h1>
          <p className="text-sm text-muted-foreground mt-1">{providers.length} provider profiles</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchProviders}>
            <RefreshCw className="w-4 h-4 mr-2" />Refresh
          </Button>
          <Button size="sm" onClick={handleOpenConvert}>
            <Plus className="w-4 h-4 mr-2" />Convert Lead
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search providers..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-surface text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
        />
      </div>

      {/* Provider Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Provider</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Services</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Rating</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Matches</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length > 0 ? filtered.map((p) => (
                  <tr key={p.id} className="border-b border-border/50 hover:bg-accent/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full gradient-primary flex items-center justify-center text-xs font-bold text-primary-foreground">
                          {(p.lead_name || p.lead_company || "?")[0].toUpperCase()}
                        </div>
                        <div>
                          <div className="text-sm font-medium text-foreground">{p.lead_name || p.lead_company || "Unknown"}</div>
                          <div className="text-xs text-muted-foreground">{p.lead_email || p.lead_location || ""}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(p.services_offered || []).map((s) => (
                          <span key={s} className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium bg-primary/10 text-primary">
                            {SERVICE_LABELS[s] || s}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <Star className="w-3.5 h-3.5 text-warning" />
                        <span className="text-sm text-foreground">{p.average_rating.toFixed(1)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <GitBranch className="w-3.5 h-3.5 text-muted-foreground" />
                        <span className="text-sm text-foreground">{p.total_matches}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={p.is_active ? "success" : "outline"}>
                        {p.is_active ? "Active" : "Inactive"}
                      </Badge>
                      {p.verified && (
                        <CheckCircle2 className="w-3.5 h-3.5 text-success inline ml-1" />
                      )}
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5} className="px-4 py-12 text-center">
                      <Building2 className="w-10 h-10 mx-auto mb-3 opacity-30 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">No providers yet</p>
                      <p className="text-xs text-muted-foreground mt-1">Convert leads to create provider profiles</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Convert Lead Modal */}
      {showConvert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card border border-border rounded-xl shadow-elevated w-full max-w-lg max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-lg font-semibold text-foreground">Convert Lead to Provider</h2>
              <button onClick={() => setShowConvert(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh] space-y-2">
              {leads.length > 0 ? leads.map((lead) => (
                <div key={lead.id} className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-accent/30 transition-colors">
                  <div>
                    <div className="text-sm font-medium text-foreground">
                      {lead.company || `${lead.first_name || ""} ${lead.last_name || ""}`.trim() || lead.email || "Unknown"}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {lead.custom_fields?.service_needed ? SERVICE_LABELS[lead.custom_fields.service_needed] || lead.custom_fields.service_needed : "No service"}{" "}
                      {lead.location ? `| ${lead.location}` : ""}
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={convertingId === lead.id}
                    onClick={() => handleConvert(lead.id)}
                  >
                    {convertingId === lead.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Convert"}
                  </Button>
                </div>
              )) : (
                <p className="text-sm text-muted-foreground text-center py-8">No eligible leads to convert</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

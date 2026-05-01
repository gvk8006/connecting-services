import { useState, useEffect } from "react"
import { Plus, Megaphone, Play, Pause, Mail, Share2, Layers, Loader2, Send, Target, BarChart3 } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { Campaign } from "@/lib/api"

interface CampaignDisplay {
  id: string
  name: string
  description: string
  status: string
  type: string
  leads_targeted: number
  emails_sent: number
  open_rate: number
  reply_rate: number
  created_at: string
}

const statusBadge: Record<string, "default" | "success" | "warning" | "outline"> = {
  draft: "outline",
  active: "success",
  paused: "warning",
  completed: "default",
}

const typeIcons: Record<string, typeof Mail> = {
  email: Mail,
  social: Share2,
  multi_channel: Layers,
}

function toCampaignDisplay(c: Campaign): CampaignDisplay {
  const stats = (c.stats || {}) as Record<string, number>
  return {
    id: c.id,
    name: c.name,
    description: c.description || "",
    status: c.status,
    type: c.campaign_type,
    leads_targeted: stats.leads_targeted || 0,
    emails_sent: stats.emails_sent || 0,
    open_rate: stats.open_rate || 0,
    reply_rate: stats.reply_rate || 0,
    created_at: c.created_at,
  }
}

export function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<CampaignDisplay[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newCampaign, setNewCampaign] = useState({ name: "", description: "", type: "email" })

  useEffect(() => {
    fetch("/api/campaigns")
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((data: Campaign[]) => setCampaigns(data.map(toCampaignDisplay)))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleToggleStatus = (id: string) => {
    const campaign = campaigns.find((c) => c.id === id)
    if (!campaign) return
    const action = campaign.status === "active" ? "pause" : "activate"
    fetch(`/api/campaigns/${id}/${action}`, { method: "POST" })
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then(() => {
        setCampaigns((prev) =>
          prev.map((c) =>
            c.id === id ? { ...c, status: c.status === "active" ? "paused" : "active" } : c
          )
        )
      })
      .catch(() => {})
  }

  const handleCreate = () => {
    if (!newCampaign.name) return
    fetch("/api/campaigns", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: newCampaign.name,
        description: newCampaign.description,
        campaign_type: newCampaign.type,
      }),
    })
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((data: Campaign) => {
        setCampaigns((prev) => [toCampaignDisplay(data), ...prev])
        setNewCampaign({ name: "", description: "", type: "email" })
        setShowCreateForm(false)
      })
      .catch(() => {})
  }

  const activeCampaigns = campaigns.filter((c) => c.status === "active").length
  const totalSent = campaigns.reduce((sum, c) => sum + c.emails_sent, 0)
  const avgOpenRate = campaigns.length > 0 ? Math.round(campaigns.reduce((sum, c) => sum + c.open_rate, 0) / campaigns.length) : 0

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Campaigns</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {campaigns.length} campaigns &middot; {activeCampaigns} active
          </p>
        </div>
        <Button size="sm" onClick={() => setShowCreateForm(!showCreateForm)}>
          <Plus className="w-4 h-4 mr-2" />New Campaign
        </Button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Campaigns", value: campaigns.length, icon: Megaphone, color: "text-primary" },
          { label: "Active", value: activeCampaigns, icon: Play, color: "text-success" },
          { label: "Emails Sent", value: totalSent, icon: Send, color: "text-warning" },
          { label: "Avg Open Rate", value: `${avgOpenRate}%`, icon: BarChart3, color: "text-primary" },
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

      {/* Create Form */}
      {showCreateForm && (
        <Card className="animate-slide-up">
          <CardContent className="p-5">
            <h3 className="text-sm font-semibold text-foreground mb-4">Create New Campaign</h3>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Campaign name"
                value={newCampaign.name}
                onChange={(e) => setNewCampaign((prev) => ({ ...prev, name: e.target.value }))}
                className="w-full h-9 px-3 rounded-lg border border-border bg-surface text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <textarea
                placeholder="Description"
                value={newCampaign.description}
                onChange={(e) => setNewCampaign((prev) => ({ ...prev, description: e.target.value }))}
                className="w-full h-20 px-3 py-2 rounded-lg border border-border bg-surface text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              />
              <div className="flex items-center gap-3">
                <select
                  value={newCampaign.type}
                  onChange={(e) => setNewCampaign((prev) => ({ ...prev, type: e.target.value }))}
                  className="h-9 px-3 rounded-lg border border-border bg-surface text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="email">Email Campaign</option>
                  <option value="social">Social Campaign</option>
                  <option value="multi_channel">Multi-Channel</option>
                </select>
                <Button size="sm" onClick={handleCreate}>Create</Button>
                <Button size="sm" variant="ghost" onClick={() => setShowCreateForm(false)}>Cancel</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Campaign Cards */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-muted-foreground">
          <Loader2 className="w-6 h-6 animate-spin mr-2" />Loading campaigns...
        </div>
      ) : campaigns.length > 0 ? (
        <div className="grid md:grid-cols-2 gap-4">
          {campaigns.map((campaign) => {
            const TypeIcon = typeIcons[campaign.type] || Megaphone
            return (
              <Card key={campaign.id} className="hover:shadow-card-hover transition-shadow duration-300">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-10 h-10 rounded-xl flex items-center justify-center",
                        campaign.status === "active" ? "gradient-primary" : "bg-secondary"
                      )}>
                        <TypeIcon className={cn("w-5 h-5", campaign.status === "active" ? "text-primary-foreground" : "text-muted-foreground")} />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-foreground">{campaign.name}</h3>
                        <Badge variant={statusBadge[campaign.status] || "outline"}>{campaign.status}</Badge>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleToggleStatus(campaign.id)}>
                        {campaign.status === "active" ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                      </Button>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground mb-4 line-clamp-2">{campaign.description}</p>
                  <div className="grid grid-cols-4 gap-2">
                    <div className="text-center p-2 rounded-lg bg-surface">
                      <div className="text-lg font-bold text-foreground">{campaign.leads_targeted}</div>
                      <div className="text-[10px] text-muted-foreground">Targeted</div>
                    </div>
                    <div className="text-center p-2 rounded-lg bg-surface">
                      <div className="text-lg font-bold text-foreground">{campaign.emails_sent}</div>
                      <div className="text-[10px] text-muted-foreground">Sent</div>
                    </div>
                    <div className="text-center p-2 rounded-lg bg-surface">
                      <div className="text-lg font-bold text-success">{campaign.open_rate}%</div>
                      <div className="text-[10px] text-muted-foreground">Open Rate</div>
                    </div>
                    <div className="text-center p-2 rounded-lg bg-surface">
                      <div className="text-lg font-bold text-primary">{campaign.reply_rate}%</div>
                      <div className="text-[10px] text-muted-foreground">Reply Rate</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <Megaphone className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm">No campaigns yet</p>
            <p className="text-xs mt-1">Create a campaign to start outreach</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

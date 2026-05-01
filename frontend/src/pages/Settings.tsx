import { useState } from "react"
import { Save, Key, Mail, Bot, Globe, Bell } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

interface SettingsSection {
  id: string
  label: string
  icon: typeof Key
  fields: { key: string; label: string; type: "text" | "password" | "number" | "toggle"; value: string | number | boolean; placeholder?: string }[]
}

export function SettingsPage() {
  const [saved, setSaved] = useState(false)

  const sections: SettingsSection[] = [
    {
      id: "api_keys", label: "API Keys", icon: Key,
      fields: [
        { key: "openai_key", label: "OpenAI API Key", type: "password", value: "", placeholder: "sk-..." },
        { key: "twitter_token", label: "Twitter Bearer Token", type: "password", value: "", placeholder: "AAA..." },
        { key: "google_api_key", label: "Google API Key", type: "password", value: "", placeholder: "AIza..." },
        { key: "google_cse_id", label: "Google CSE ID", type: "text", value: "", placeholder: "Custom Search Engine ID" },
      ],
    },
    {
      id: "email", label: "Email Configuration", icon: Mail,
      fields: [
        { key: "smtp_host", label: "SMTP Host", type: "text", value: "smtp.gmail.com", placeholder: "smtp.gmail.com" },
        { key: "smtp_port", label: "SMTP Port", type: "number", value: 587, placeholder: "587" },
        { key: "smtp_user", label: "SMTP Username", type: "text", value: "", placeholder: "your@email.com" },
        { key: "smtp_pass", label: "SMTP Password", type: "password", value: "", placeholder: "App password" },
      ],
    },
    {
      id: "agents", label: "Agent Settings", icon: Bot,
      fields: [
        { key: "scraper_interval", label: "Scraper Interval (min)", type: "number", value: 30 },
        { key: "max_leads_batch", label: "Max Leads per Batch", type: "number", value: 50 },
        { key: "score_threshold", label: "Score Threshold", type: "number", value: 0.6 },
        { key: "llm_model", label: "LLM Model", type: "text", value: "gpt-4o-mini", placeholder: "gpt-4o-mini" },
      ],
    },
  ]

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">Configure API keys, email, and agent behavior</p>
        </div>
        <Button size="sm" onClick={handleSave}>
          <Save className="w-4 h-4 mr-2" />
          {saved ? "Saved!" : "Save Changes"}
        </Button>
      </div>

      {/* Settings Sections */}
      {sections.map((section) => {
        const Icon = section.icon
        return (
          <Card key={section.id}>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Icon className="w-4 h-4 text-primary" />
                <CardTitle className="text-base font-semibold text-foreground">{section.label}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {section.fields.map((field) => (
                  <div key={field.key} className="flex items-center gap-4">
                    <label className="text-sm text-muted-foreground w-44 shrink-0">{field.label}</label>
                    <input
                      type={field.type === "password" ? "password" : field.type === "number" ? "number" : "text"}
                      defaultValue={String(field.value)}
                      placeholder={field.placeholder}
                      className="flex-1 h-9 px-3 rounded-lg border border-border bg-surface text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )
      })}

      {/* Danger Zone */}
      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-base font-semibold text-destructive">Danger Zone</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-foreground">Reset All Data</p>
              <p className="text-xs text-muted-foreground">This will permanently delete all leads, campaigns, and analytics.</p>
            </div>
            <Button variant="destructive" size="sm">Reset</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
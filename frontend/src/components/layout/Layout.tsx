import { Outlet } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { useWebSocket } from "@/hooks/useWebSocket"
import { cn } from "@/lib/utils"
import { useState, useCallback } from "react"

export function Layout() {
  const [notifications, setNotifications] = useState<string[]>([])
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const handleWSMessage = useCallback((msg: { event: string; data: Record<string, unknown> }) => {
    if (msg.event === "new_lead") {
      setNotifications((prev) => [`New lead captured: ${msg.data.email || "Unknown"}`, ...prev.slice(0, 9)])
    } else if (msg.event === "agent_completed") {
      setNotifications((prev) => [`Agent completed task`, ...prev.slice(0, 9)])
    }
  }, [])

  const { connected } = useWebSocket(handleWSMessage)

  return (
    <div className="min-h-screen bg-background">
      <Sidebar wsConnected={connected} collapsed={sidebarCollapsed} onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)} />

      {/* Main content area */}
      <main className={cn("min-h-screen transition-all duration-300", sidebarCollapsed ? "pl-16" : "pl-60")}>
        <div className="p-6 lg:p-8 max-w-[1600px] mx-auto">
          <Outlet />
        </div>
      </main>

      {/* Toast-style notifications */}
      {notifications.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 space-y-2 max-w-sm">
          {notifications.slice(0, 3).map((n, i) => (
            <div
              key={`${n}-${i}`}
              className="animate-slide-up bg-card border border-border rounded-lg px-4 py-3 shadow-elevated text-sm text-foreground"
              onClick={() => setNotifications((prev) => prev.filter((_, idx) => idx !== i))}
            >
              {n}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
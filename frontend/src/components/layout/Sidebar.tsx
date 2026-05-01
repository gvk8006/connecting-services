import { NavLink, useLocation } from "react-router-dom"
import {
  LayoutDashboard,
  Users,
  Bot,
  Megaphone,
  BarChart3,
  Settings,
  Zap,
  ChevronLeft,
  Handshake,
  Building2,
  FileSearch,
  GitBranch,
  DollarSign,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { StatusDot } from "@/components/ui/status-dot"

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/leads", icon: Users, label: "Leads" },
  { to: "/agents", icon: Bot, label: "Agents" },
  { to: "/campaigns", icon: Megaphone, label: "Campaigns" },
  { to: "/analytics", icon: BarChart3, label: "Analytics" },
  { to: "/settings", icon: Settings, label: "Settings" },
]

const marketplaceItems = [
  { to: "/marketplace", icon: Handshake, label: "Marketplace" },
  { to: "/providers", icon: Building2, label: "Providers" },
  { to: "/requests", icon: FileSearch, label: "Requests" },
  { to: "/matches", icon: GitBranch, label: "Matches" },
  { to: "/revenue", icon: DollarSign, label: "Revenue" },
]

interface SidebarProps {
  wsConnected: boolean
  collapsed: boolean
  onToggleCollapse: () => void
}

export function Sidebar({ wsConnected, collapsed, onToggleCollapse }: SidebarProps) {
  const location = useLocation()

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen border-r border-border bg-card flex flex-col transition-all duration-300",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-border shrink-0">
        <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center shadow-glow-primary shrink-0">
          <Zap className="w-4 h-4 text-primary-foreground" />
        </div>
        {!collapsed && (
          <div className="animate-fade-in">
            <h1 className="text-sm font-bold text-foreground tracking-tight">AgentForge</h1>
            <p className="text-[10px] text-muted-foreground font-medium tracking-widest uppercase">AI</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto scrollbar-thin">
        {navItems.map(({ to, icon: Icon, label }) => {
          const isActive = location.pathname === to || (to !== "/" && location.pathname.startsWith(to))
          return (
            <NavLink
              key={to}
              to={to}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-primary/10 text-primary shadow-glow-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
            >
              <Icon className={cn("w-[18px] h-[18px] shrink-0", isActive && "text-primary")} />
              {!collapsed && <span className="animate-fade-in">{label}</span>}
            </NavLink>
          )
        })}

        {/* Marketplace section divider */}
        <div className="pt-3 pb-1">
          {!collapsed && (
            <span className="px-3 text-[10px] font-semibold text-muted-foreground uppercase tracking-widest animate-fade-in">Marketplace</span>
          )}
          {collapsed && <div className="h-px bg-border mx-2" />}
        </div>

        {marketplaceItems.map(({ to, icon: Icon, label }) => {
          const isActive = location.pathname === to
          return (
            <NavLink
              key={to}
              to={to}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-primary/10 text-primary shadow-glow-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
            >
              <Icon className={cn("w-[18px] h-[18px] shrink-0", isActive && "text-primary")} />
              {!collapsed && <span className="animate-fade-in">{label}</span>}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-border space-y-2">
        {!collapsed && (
          <div className="flex items-center gap-2 px-2 py-1.5 animate-fade-in">
            <StatusDot status={wsConnected ? "running" : "error"} />
            <span className="text-xs text-muted-foreground">
              {wsConnected ? "Live connected" : "Reconnecting..."}
            </span>
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="flex items-center justify-center w-full py-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        >
          <ChevronLeft className={cn("w-4 h-4 transition-transform duration-300", collapsed && "rotate-180")} />
        </button>
      </div>
    </aside>
  )
}
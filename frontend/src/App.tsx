import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Layout } from "@/components/layout/Layout"
import { DashboardPage } from "@/pages/Dashboard"
import { LeadsPage } from "@/pages/Leads"
import { AgentsPage } from "@/pages/Agents"
import { CampaignsPage } from "@/pages/Campaigns"
import { AnalyticsPage } from "@/pages/Analytics"
import { SettingsPage } from "@/pages/Settings"
import { MarketplacePage } from "@/pages/Marketplace"
import { ProvidersPage } from "@/pages/Providers"
import { ServiceRequestsPage } from "@/pages/ServiceRequests"
import { MatchesPage } from "@/pages/Matches"
import { RevenuePage } from "@/pages/Revenue"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/leads" element={<LeadsPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/campaigns" element={<CampaignsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/marketplace" element={<MarketplacePage />} />
          <Route path="/providers" element={<ProvidersPage />} />
          <Route path="/requests" element={<ServiceRequestsPage />} />
          <Route path="/matches" element={<MatchesPage />} />
          <Route path="/revenue" element={<RevenuePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
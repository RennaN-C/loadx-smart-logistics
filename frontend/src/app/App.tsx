import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AuthProvider } from "../features/auth/components/AuthProvider";
import { RequireAuth } from "../features/auth/components/RequireAuth";
import { LoginPage } from "../features/auth/pages/LoginPage";
import { AuditPage } from "../features/audit/pages/AuditPage";
import { ContactsPage } from "../features/customers/pages/ContactsPage";
import { DashboardPage } from "../features/dashboard/pages/DashboardPage";
import { TripPage } from "../features/deliveries/pages/TripPage";
import { PlanningPage } from "../features/load-planning/pages/PlanningPage";
import { LoadingPage } from "../features/loading-operation/pages/LoadingPage";
import { OperationsDashboardPage } from "../features/operations/pages/OperationsDashboardPage";
import { OrderListPage } from "../features/orders/pages/OrderListPage";
import { ProductListPage } from "../features/products/pages/ProductListPage";
import { ReportsPage } from "../features/reports/pages/ReportsPage";
import { FleetStatusPage } from "../features/trucks/pages/FleetStatusPage";
import { TruckListPage } from "../features/trucks/pages/TruckListPage";
import { RequireSettingsAdmin } from "../features/settings/components/RequireSettingsAdmin";
import { SettingsPage } from "../features/settings/pages/SettingsPage";
import { AppLayout } from "./AppLayout";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route element={<RequireSettingsAdmin />}>
                <Route path="settings" element={<SettingsPage />} />
              </Route>
              <Route path="trucks" element={<TruckListPage />} />
              <Route path="fleet" element={<FleetStatusPage />} />
              <Route path="products" element={<ProductListPage />} />
              <Route path="contacts" element={<ContactsPage />} />
              <Route path="orders" element={<OrderListPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route path="operations" element={<OperationsDashboardPage />} />
              <Route path="audit" element={<AuditPage />} />
              <Route path="planning" element={<PlanningPage />} />
              <Route path="planning/:planId" element={<PlanningPage />} />
              <Route path="trips/:tripId" element={<TripPage />} />
              <Route path="loading/:sessionId" element={<LoadingPage />} />
              <Route
                path="*"
                element={
                  <div className="shell">
                    <h1>Página não encontrada</h1>
                    <p>Verifique o endereço digitado.</p>
                  </div>
                }
              />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

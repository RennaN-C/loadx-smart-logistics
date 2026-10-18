import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "../features/auth/components/AuthProvider";
import { RequireAuth } from "../features/auth/components/RequireAuth";
import { PasswordRecoveryPage } from "../features/auth/pages/PasswordRecoveryPage";
import { LoginPage } from "../features/auth/pages/LoginPage";
import { AuditPage } from "../features/audit/pages/AuditPage";
import { ContactsPage } from "../features/customers/pages/ContactsPage";
import { DashboardPage } from "../features/dashboard/pages/DashboardPage";
import { TripPage } from "../features/deliveries/pages/TripPage";
import { PlanningPage } from "../features/load-planning/pages/PlanningPage";
import { LoadingPage } from "../features/loading-operation/pages/LoadingPage";
import { OrderListPage } from "../features/orders/pages/OrderListPage";
import { ProductListPage } from "../features/products/pages/ProductListPage";
import { ReportsPage } from "../features/reports/pages/ReportsPage";
import { TruckWorkspacePage } from "../features/trucks/pages/TruckWorkspacePage";
import { OperationalAccess } from "./OperationalAccess";
import { RequireSettingsAdmin } from "../features/settings/components/RequireSettingsAdmin";
import { SettingsPage } from "../features/settings/pages/SettingsPage";
import { AccountPage } from "../features/auth/pages/AccountPage";
import { AppLayout } from "./AppLayout";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/password-recovery" element={<PasswordRecoveryPage />} />
          <Route path="/password-reset" element={<PasswordRecoveryPage reset />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="account" element={<AccountPage />} />
              <Route element={<RequireSettingsAdmin />}>
                <Route path="settings" element={<SettingsPage />} />
              </Route>
              <Route path="trucks" element={<OperationalAccess><TruckWorkspacePage /></OperationalAccess>} />
              <Route path="fleet" element={<OperationalAccess><Navigate to="/trucks?tab=availability" replace /></OperationalAccess>} />
              <Route path="products" element={<OperationalAccess permission="loadx.products.read"><ProductListPage /></OperationalAccess>} />
              <Route path="contacts" element={<ContactsPage />} />
              <Route path="orders" element={<OperationalAccess permission="loadx.orders.read"><OrderListPage /></OperationalAccess>} />
              <Route path="reports" element={<OperationalAccess permissions={["loadx.reports.read", "loadx.orders.read"]}><ReportsPage /></OperationalAccess>} />
              <Route path="operations" element={<OperationalAccess overview><Navigate to="/" replace /></OperationalAccess>} />
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

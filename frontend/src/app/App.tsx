import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AuthProvider } from "../features/auth/components/AuthProvider";
import { RequireAuth } from "../features/auth/components/RequireAuth";
import { LoginPage } from "../features/auth/pages/LoginPage";
import { ContactsPage } from "../features/customers/pages/ContactsPage";
import { PlanningPage } from "../features/load-planning/pages/PlanningPage";
import { OrderListPage } from "../features/orders/pages/OrderListPage";
import { ProductListPage } from "../features/products/pages/ProductListPage";
import { TruckListPage } from "../features/trucks/pages/TruckListPage";
import { AppLayout } from "./AppLayout";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppLayout />}>
              <Route
                index
                element={
                  <div className="shell">
                    <h1>Base inicial pronta</h1>
                    <p>
                      Consulte os READMEs e a documentação antes de iniciar as ocorrências do MVP.
                    </p>
                  </div>
                }
              />
              <Route path="trucks" element={<TruckListPage />} />
              <Route path="products" element={<ProductListPage />} />
              <Route path="contacts" element={<ContactsPage />} />
              <Route path="orders" element={<OrderListPage />} />
              <Route path="planning" element={<PlanningPage />} />
              <Route path="planning/:planId" element={<PlanningPage />} />
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

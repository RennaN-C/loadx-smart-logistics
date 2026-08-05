import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AppLayout } from "./AppLayout";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
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
      </Routes>
    </BrowserRouter>
  );
}

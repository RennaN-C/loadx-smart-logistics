import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Link, MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { expect, it } from "vitest";
import { useUrlSearch } from "./useUrlSearch";
function Harness() {
  const [search, setSearch] = useUrlSearch(); const location = useLocation(); const navigate = useNavigate();
  return <><label>Filtro<input value={search} onChange={(event) => setSearch(event.target.value)} /></label><p>{location.search}</p><Link to="?tab=drivers&search=outro">Outro filtro</Link><button onClick={() => navigate(-1)}>Voltar</button></>;
}
it("restaura filtro da URL, preserva aba e acompanha navegação anterior", async () => {
  render(<MemoryRouter initialEntries={["/contacts?tab=drivers&search=alvo"]}><Harness /></MemoryRouter>);
  expect(screen.getByLabelText("Filtro")).toHaveValue("alvo");
  fireEvent.change(screen.getByLabelText("Filtro"), { target: { value: "novo" } });
  expect(screen.getByText("?tab=drivers&search=novo")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("link", { name: "Outro filtro" })); expect(screen.getByLabelText("Filtro")).toHaveValue("outro");
  fireEvent.click(screen.getByRole("button", { name: "Voltar" })); await waitFor(() => expect(screen.getByLabelText("Filtro")).toHaveValue("novo"));
  fireEvent.change(screen.getByLabelText("Filtro"), { target: { value: "" } }); expect(screen.getByText("?tab=drivers")).toBeInTheDocument();
});
